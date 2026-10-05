from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet

class GitHubStore:
    def __init__(self, mongo_uri: str, encryption_key: str):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client.get_default_database() or self.client["github"]
        self.users = self.db["github_users"]
        self.repositories = self.db["github_repositories"]
        self.integrations = self.db["github_integrations"]
        self.deliveries = self.db["github_deliveries"]
        self.settings = self.db["github_settings"]
        self.cipher = Fernet(encryption_key.encode())

    async def setup(self):
        await self.users.create_index("telegram_id", unique=True)
        await self.repositories.create_index([("telegram_id", 1), ("repository_id", 1)], unique=True)
        await self.repositories.create_index([("telegram_id", 1), ("updated_at", -1)])
        await self.integrations.create_index([("telegram_id", 1), ("repository_id", 1)], unique=True)
        await self.deliveries.create_index([("delivery_id", 1), ("telegram_id", 1)], unique=True)
        await self.deliveries.create_index("created_at", expireAfterSeconds=60 * 60 * 24 * 30)
        await self.settings.create_index("telegram_id", unique=True)

    async def save_user(self, telegram_id: int, profile: dict, grant) -> None:
        now = datetime.now(timezone.utc)
        update = {
            "telegram_id": telegram_id,
            "github_id": profile["id"],
            "login": profile["login"],
            "avatar_url": profile.get("avatar_url"),
            "access_token": self.cipher.encrypt(grant.access_token.encode()).decode(),
            "refresh_token": self.cipher.encrypt(grant.refresh_token.encode()).decode() if grant.refresh_token else None,
            "expires_in": grant.expires_in,
            "refresh_token_expires_in": grant.refresh_token_expires_in,
            "access_expires_at": now + timedelta(seconds=grant.expires_in or 0),
            "refresh_token_expires_at": now + timedelta(seconds=grant.refresh_token_expires_in or 0) if grant.refresh_token_expires_in else None,
            "scope": grant.scope,
            "updated_at": now,
        }
        await self.users.update_one({"telegram_id": telegram_id}, {"$set": update, "$setOnInsert": {"created_at": now}}, upsert=True)

    async def disconnect_user(self, telegram_id: int) -> None:
        await self.users.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"access_token": None, "refresh_token": None, "scope": "", "access_expires_at": None, "refresh_token_expires_at": None, "updated_at": datetime.now(timezone.utc)}},
        )

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
            update = {
                "access_token": self.cipher.encrypt(grant.access_token.encode()).decode(),
                "access_expires_at": now + timedelta(seconds=grant.expires_in or 0),
                "scope": grant.scope,
                "updated_at": now,
            }
            if grant.refresh_token:
                update["refresh_token"] = self.cipher.encrypt(grant.refresh_token.encode()).decode()
            if grant.refresh_token_expires_in:
                update["refresh_token_expires_at"] = now + timedelta(seconds=grant.refresh_token_expires_in)
            await self.users.update_one({"telegram_id": telegram_id}, {"$set": update})
            return grant.access_token
        return self.cipher.decrypt(user["access_token"].encode()).decode()

    async def add_repository(self, telegram_id: int, repo: dict) -> None:
        now = datetime.now(timezone.utc)
        await self.repositories.update_one(
            {"telegram_id": telegram_id, "repository_id": repo["id"]},
            {"$set": {
                "telegram_id": telegram_id,
                "repository_id": repo["id"],
                "full_name": repo["full_name"],
                "owner": repo["owner"]["login"],
                "name": repo["name"],
                "private": repo.get("private", False),
                "default_branch": repo.get("default_branch", "main"),
                "updated_at": now,
            }, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

    async def remove_repository(self, telegram_id: int, repository_id: int) -> bool:
        result = await self.repositories.delete_one({"telegram_id": telegram_id, "repository_id": repository_id})
        return result.deleted_count == 1

    async def repository(self, telegram_id: int, repository_id: int):
        return await self.repositories.find_one({"telegram_id": telegram_id, "repository_id": repository_id})

    async def repository_by_name(self, telegram_id: int, full_name: str):
        return await self.repositories.find_one({"telegram_id": telegram_id, "full_name": full_name})

    async def list_repositories(self, telegram_id: int):
        return await self.repositories.find({"telegram_id": telegram_id}).sort("full_name", 1).to_list(length=200)

    async def set_current_repository(self, telegram_id: int, repository_id: int) -> None:
        await self.settings.update_one({"telegram_id": telegram_id}, {"$set": {"current_repository_id": repository_id, "updated_at": datetime.now(timezone.utc)}}, upsert=True)

    async def current_repository(self, telegram_id: int):
        settings = await self.settings.find_one({"telegram_id": telegram_id})
        if not settings or not settings.get("current_repository_id"):
            return None
        return await self.repository(telegram_id, int(settings["current_repository_id"]))

    async def save_setting(self, telegram_id: int, key: str, value) -> None:
        await self.settings.update_one({"telegram_id": telegram_id}, {"$set": {key: value, "updated_at": datetime.now(timezone.utc)}}, upsert=True)

    async def get_settings(self, telegram_id: int) -> dict:
        item = await self.settings.find_one({"telegram_id": telegram_id})
        return item or {}

    async def claim_delivery(self, delivery_id: str, telegram_id: int, repository_id: int, event: str, number: int | None, message_id: int = 0) -> bool:
        result = await self.deliveries.update_one(
            {"delivery_id": delivery_id, "telegram_id": telegram_id},
            {"$setOnInsert": {
                "delivery_id": delivery_id,
                "telegram_id": telegram_id,
                "repository_id": repository_id,
                "event": event,
                "number": number,
                "message_id": message_id,
                "created_at": datetime.now(timezone.utc),
                "status": "processing",
            }},
            upsert=True,
        )
        return result.upserted_id is not None

    async def save_delivery(self, delivery_id: str, telegram_id: int, repository_id: int, event: str, number: int | None, message_id: int) -> None:
        await self.deliveries.update_one(
            {"delivery_id": delivery_id, "telegram_id": telegram_id},
            {"$set": {"message_id": message_id, "status": "sent", "sent_at": datetime.now(timezone.utc)}},
        )

    async def fail_delivery(self, delivery_id: str, telegram_id: int, error: str | None = None) -> None:
        await self.deliveries.update_one({"delivery_id": delivery_id, "telegram_id": telegram_id}, {"$set": {"status": "failed", "error": error, "failed_at": datetime.now(timezone.utc)}})

    async def list_deliveries(self, telegram_id: int, repository_id: int, limit: int = 25):
        return await self.deliveries.find({"telegram_id": telegram_id, "repository_id": repository_id}).sort("created_at", -1).to_list(length=limit)

    async def delivery(self, telegram_id: int, delivery_id: str):
        return await self.deliveries.find_one({"telegram_id": telegram_id, "delivery_id": delivery_id})

    async def update_delivery_status(self, telegram_id: int, delivery_id: str, status: str) -> bool:
        result = await self.deliveries.update_one({"telegram_id": telegram_id, "delivery_id": delivery_id}, {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}})
        return result.modified_count == 1

    async def integrations_for_repository(self, repository_id: int):
        return await self.integrations.find({"repository_id": repository_id}).to_list(length=100)

    async def notification(self, telegram_id: int, message_id: int):
        return await self.deliveries.find_one({"telegram_id": telegram_id, "message_id": message_id, "status": "sent"})

    async def integration(self, telegram_id: int, repository_id: int):
        return await self.integrations.find_one({"telegram_id": telegram_id, "repository_id": repository_id})

    async def add_integration(self, telegram_id: int, repo: dict, hook_id: int | None = None) -> None:
        now = datetime.now(timezone.utc)
        await self.integrations.update_one(
            {"telegram_id": telegram_id, "repository_id": repo["id"]},
            {"$set": {
                "repository_id": repo["id"],
                "full_name": repo["full_name"],
                "owner": repo["owner"]["login"],
                "name": repo["name"],
                "private": repo.get("private", False),
                "hook_id": hook_id,
                "events": repo.get("webhook_events", []),
                "active": repo.get("webhook_active", True),
                "updated_at": now,
            }, "$setOnInsert": {"telegram_id": telegram_id, "created_at": now}},
            upsert=True,
        )

    async def list_integrations(self, telegram_id: int):
        return await self.integrations.find({"telegram_id": telegram_id}).sort("full_name", 1).to_list(length=100)

    async def update_integration(self, telegram_id: int, repository_id: int, **fields) -> bool:
        allowed = {"events", "active", "hook_id"}
        payload = {key: value for key, value in fields.items() if key in allowed}
        if not payload:
            return False
        payload["updated_at"] = datetime.now(timezone.utc)
        result = await self.integrations.update_one({"telegram_id": telegram_id, "repository_id": repository_id}, {"$set": payload})
        return result.modified_count == 1

    async def delete_integration(self, telegram_id: int, repository_id: int) -> bool:
        result = await self.integrations.delete_one({"telegram_id": telegram_id, "repository_id": repository_id})
        return result.deleted_count == 1

    async def close(self):
        self.client.close()
