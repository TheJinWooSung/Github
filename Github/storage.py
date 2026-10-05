from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet

class GitHubStore:
    def __init__(self, mongo_uri: str, encryption_key: str):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client.get_default_database()
        self.users = self.db["github_users"]
        self.integrations = self.db["github_integrations"]
        self.cipher = Fernet(encryption_key.encode())

    async def setup(self):
        await self.users.create_index("telegram_id", unique=True)
        await self.integrations.create_index([("telegram_id", 1), ("repository_id", 1)], unique=True)

    async def save_user(self, telegram_id: int, profile: dict, grant) -> None:
        now = datetime.now(timezone.utc)
        update = {"telegram_id": telegram_id, "github_id": profile["id"], "login": profile["login"], "avatar_url": profile.get("avatar_url"), "access_token": self.cipher.encrypt(grant.access_token.encode()).decode(), "refresh_token": self.cipher.encrypt(grant.refresh_token.encode()).decode() if grant.refresh_token else None, "expires_in": grant.expires_in, "refresh_token_expires_in": grant.refresh_token_expires_in, "access_expires_at": now + timedelta(seconds=grant.expires_in or 0), "refresh_token_expires_at": now + timedelta(seconds=grant.refresh_token_expires_in or 0) if grant.refresh_token_expires_in else None, "scope": grant.scope, "updated_at": now}
        await self.users.update_one({"telegram_id": telegram_id}, {"$set": update, "$setOnInsert": {"created_at": now}}, upsert=True)

    async def get_user(self, telegram_id: int):
        return await self.users.find_one({"telegram_id": telegram_id})

    async def token(self, telegram_id: int, oauth=None) -> str | None:
        user = await self.get_user(telegram_id)
        if not user or not user.get("access_token"):
            return None
        expires_at = user.get("access_expires_at")
        if oauth and expires_at and expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5) and user.get("refresh_token"):
            refresh_token = self.cipher.decrypt(user["refresh_token"].encode()).decode()
            grant = await oauth.refresh(refresh_token)
            now = datetime.now(timezone.utc)
            update = {"access_token": self.cipher.encrypt(grant.access_token.encode()).decode(), "access_expires_at": now + timedelta(seconds=grant.expires_in or 0), "scope": grant.scope, "updated_at": now}
            if grant.refresh_token:
                update["refresh_token"] = self.cipher.encrypt(grant.refresh_token.encode()).decode()
            if grant.refresh_token_expires_in:
                update["refresh_token_expires_at"] = now + timedelta(seconds=grant.refresh_token_expires_in)
            await self.users.update_one({"telegram_id": telegram_id}, {"$set": update})
            return grant.access_token
        return self.cipher.decrypt(user["access_token"].encode()).decode()

    async def delivery_seen(self, delivery_id: str) -> bool:
        if await self.db["github_deliveries"].find_one({"delivery_id": delivery_id}):
            return True
        return False

    async def save_delivery(self, delivery_id: str, telegram_id: int, repository_id: int, event: str, number: int | None, message_id: int) -> None:
        await self.db["github_deliveries"].update_one({"delivery_id": delivery_id, "telegram_id": telegram_id}, {"$set": {"delivery_id": delivery_id, "telegram_id": telegram_id, "repository_id": repository_id, "event": event, "number": number, "message_id": message_id}}, upsert=True)

    async def integrations_for_repository(self, repository_id: int):
        return await self.integrations.find({"repository_id": repository_id}).to_list(length=100)

    async def add_integration(self, telegram_id: int, repo: dict) -> None:
        now = datetime.now(timezone.utc)
        await self.integrations.update_one({"telegram_id": telegram_id, "repository_id": repo["id"]}, {"$set": {"repository_id": repo["id"], "full_name": repo["full_name"], "owner": repo["owner"]["login"], "name": repo["name"], "private": repo.get("private", False), "updated_at": now}, "$setOnInsert": {"created_at": now}}, upsert=True)

    async def list_integrations(self, telegram_id: int):
        return await self.integrations.find({"telegram_id": telegram_id}).sort("full_name", 1).to_list(length=100)

    async def delete_integration(self, telegram_id: int, repository_id: int) -> bool:
        result = await self.integrations.delete_one({"telegram_id": telegram_id, "repository_id": repository_id})
        return result.deleted_count == 1

    async def close(self):
        self.client.close()
