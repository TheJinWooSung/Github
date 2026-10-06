import asyncio
import json
import secrets
import time
from dataclasses import dataclass, asdict
from redis.asyncio import Redis

@dataclass
class OAuthState:
    telegram_id: int
    verifier: str
    expires_at: float = 0.0

@dataclass
class EditSession:
    user_id: int
    chat_id: int
    repository_id: int
    owner: str
    name: str
    branch: str
    path: str
    original: str
    content: str | None = None
    message: str | None = None
    base_head: str | None = None
    browser_token: str | None = None
    status: str = "editing"
    expires_at: float = 0.0

@dataclass
class StagedChange:
    path: str
    status: str
    content: str | None = None
    additions: int = 0
    deletions: int = 0

@dataclass
class CommitStageSession:
    user_id: int
    chat_id: int
    repository_id: int
    owner: str
    name: str
    branch: str
    changes: list[StagedChange]
    base_head: str | None = None
    status: str = "ready"
    expires_at: float = 0.0

@dataclass
class ReviewSession:
    user_id: int
    chat_id: int
    repository_id: int
    owner: str
    name: str
    number: int
    event: str
    expires_at: float = 0.0

@dataclass
class BrowserSession:
    user_id: int
    chat_id: int
    repository_id: int
    owner: str
    name: str
    branch: str
    path: str
    parent_token: str | None = None
    expires_at: float = 0.0

class SessionStore:
    def __init__(self, redis_url: str | None = None, ttl: int = 1800):
        self.ttl = ttl
        self.redis = Redis.from_url(redis_url, decode_responses=True) if redis_url else None
        self.memory: dict[str, object] = {}
        self.lock = asyncio.Lock()

    async def create(self, session):
        token = secrets.token_urlsafe(18)
        session.expires_at = time.time() + self.ttl
        await self.set(token, session)
        return token

    async def set(self, token: str, session) -> None:
        if self.redis:
            await self.redis.setex(self._key(token), self.ttl, json.dumps(asdict(session)))
            if isinstance(session, EditSession):
                await self.redis.setex(f"github:active:{session.user_id}", self.ttl, token)
            if isinstance(session, ReviewSession):
                await self.redis.setex(f"github:review:{session.user_id}", self.ttl, token)
            if isinstance(session, CommitStageSession):
                await self.redis.setex(f"github:stage:{session.user_id}", self.ttl, token)
            return
        async with self.lock:
            self.memory[token] = session

    async def get(self, token: str):
        if self.redis:
            value = await self.redis.get(self._key(token))
            if not value:
                return None
            payload = json.loads(value)
            if "verifier" in payload:
                return OAuthState(**payload)
            if "event" in payload and "number" in payload and "owner" in payload:
                return ReviewSession(**payload)
            if "changes" in payload and "branch" in payload:
                payload["changes"] = [StagedChange(**item) for item in payload["changes"]]
                return CommitStageSession(**payload)
            if "parent_token" in payload:
                return BrowserSession(**payload)
            return EditSession(**payload)
        async with self.lock:
            session = self.memory.get(token)
            if not session:
                return None
            if session.expires_at <= time.time():
                self.memory.pop(token, None)
                return None
            return session

    async def active(self, user_id: int) -> str | None:
        if self.redis:
            token = await self.redis.get(f"github:active:{user_id}")
            if not token:
                return None
            if await self.get(token):
                return token
            await self.redis.delete(f"github:active:{user_id}")
            return None
        async with self.lock:
            for token, session in self.memory.items():
                if isinstance(session, EditSession) and session.user_id == user_id and session.expires_at > time.time():
                    return token
            return None

    async def delete(self, token: str) -> None:
        session = await self.get(token)
        if self.redis:
            await self.redis.delete(self._key(token))
            if isinstance(session, (EditSession, ReviewSession, CommitStageSession)):
                if isinstance(session, EditSession):
                    key = f"github:active:{session.user_id}"
                elif isinstance(session, ReviewSession):
                    key = f"github:review:{session.user_id}"
                else:
                    key = f"github:stage:{session.user_id}"
                if await self.redis.get(key) == token:
                    await self.redis.delete(key)
            return
        async with self.lock:
            self.memory.pop(token, None)

    async def stage(self, user_id: int) -> str | None:
        if self.redis:
            token = await self.redis.get(f"github:stage:{user_id}")
            if token and await self.get(token):
                return token
            if token:
                await self.redis.delete(f"github:stage:{user_id}")
            return None
        async with self.lock:
            for token, session in self.memory.items():
                if isinstance(session, CommitStageSession) and session.user_id == user_id and session.expires_at > time.time():
                    return token
            return None

    async def create_stage(self, session: CommitStageSession):
        token = secrets.token_urlsafe(18)
        session.expires_at = time.time() + self.ttl
        await self.set(token, session)
        return token

    async def review(self, user_id: int) -> str | None:
        if self.redis:
            token = await self.redis.get(f"github:review:{user_id}")
            if token and await self.get(token):
                return token
            if token:
                await self.redis.delete(f"github:review:{user_id}")
            return None
        async with self.lock:
            for token, session in self.memory.items():
                if isinstance(session, ReviewSession) and session.user_id == user_id and session.expires_at > time.time():
                    return token
            return None

    async def create_review(self, session: ReviewSession):
        token = secrets.token_urlsafe(18)
        session.expires_at = time.time() + self.ttl
        await self.set(token, session)
        return token

    async def close(self) -> None:
        if self.redis:
            await self.redis.aclose()

    @staticmethod
    def _key(token: str) -> str:
        return f"github:session:{token}"
