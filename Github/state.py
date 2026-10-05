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
    status: str = "editing"
    expires_at: float = 0.0

class SessionStore:
    def __init__(self, redis_url: str | None = None, ttl: int = 1800):
        self.ttl = ttl
        self.redis = Redis.from_url(redis_url, decode_responses=True) if redis_url else None
        self.memory: dict[str, EditSession] = {}
        self.lock = asyncio.Lock()

    async def create(self, session: EditSession) -> str:
        token = secrets.token_urlsafe(9)
        session.expires_at = time.time() + self.ttl
        await self.set(token, session)
        return token

    async def set(self, token: str, session: EditSession) -> None:
        if self.redis:
            payload = json.dumps(asdict(session))
            await self.redis.setex(f"github:session:{token}", self.ttl, payload)
            await self.redis.setex(f"github:active:{session.user_id}", self.ttl, token)
            return
        async with self.lock:
            self.memory[token] = session

    async def get(self, token: str) -> EditSession | None:
        if self.redis:
            value = await self.redis.get(f"github:session:{token}")
            if not value:
                return None
            return EditSession(**json.loads(value))
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
            return await self.redis.get(f"github:active:{user_id}")
        async with self.lock:
            for token, session in self.memory.items():
                if session.user_id == user_id and session.expires_at > time.time():
                    return token
            return None

    async def delete(self, token: str) -> None:
        if self.redis:
            await self.redis.delete(f"github:session:{token}")
            return
        async with self.lock:
            self.memory.pop(token, None)

    async def close(self) -> None:
        if self.redis:
            await self.redis.aclose()
