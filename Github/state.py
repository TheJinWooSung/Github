import asyncio
import json
import secrets
import time
from dataclasses import dataclass, asdict
from redis.asyncio import Redis

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
        token = secrets.token_urlsafe(9)
        session.expires_at = time.time() + self.ttl
        await self.set(token, session)
        return token

    async def set(self, token: str, session) -> None:
        key = self._key(token)
        if self.redis:
            await self.redis.setex(key, self.ttl, json.dumps(asdict(session)))
            if isinstance(session, EditSession):
                await self.redis.setex(f"github:active:{session.user_id}", self.ttl, token)
            return
        async with self.lock:
            self.memory[token] = session

    async def get(self, token: str):
        if self.redis:
            value = await self.redis.get(self._key(token))
            if not value:
                return None
            payload = json.loads(value)
            return BrowserSession(**payload) if "parent_token" in payload else EditSession(**payload)
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
            if isinstance(session, EditSession):
                active_key = f"github:active:{session.user_id}"
                if await self.redis.get(active_key) == token:
                    await self.redis.delete(active_key)
            return
        async with self.lock:
            self.memory.pop(token, None)

    async def close(self) -> None:
        if self.redis:
            await self.redis.aclose()

    @staticmethod
    def _key(token: str) -> str:
        return f"github:session:{token}"
