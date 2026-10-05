from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass(frozen=True)
class Config:
    bot_token: str
    api_id: int
    api_hash: str
    mongo_uri: str
    github_app_id: int
    github_installation_id: int
    github_private_key: str
    github_client_id: str
    github_client_secret: str
    github_webhook_secret: str
    webhook_url: str
    token_encryption_key: str
    redis_url: str | None = None
    log_chat_id: int | None = None

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        required = ("BOT_TOKEN", "API_ID", "API_HASH", "MONGO_URI", "GITHUB_APP_ID", "GITHUB_INSTALLATION_ID", "GITHUB_PRIVATE_KEY", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GITHUB_WEBHOOK_SECRET", "WEBHOOK_URL", "TOKEN_ENCRYPTION_KEY")
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
        log_chat_id = os.getenv("LOG_CHAT_ID")
        return cls(bot_token=os.environ["BOT_TOKEN"], api_id=int(os.environ["API_ID"]), api_hash=os.environ["API_HASH"], mongo_uri=os.environ["MONGO_URI"], github_app_id=int(os.environ["GITHUB_APP_ID"]), github_installation_id=int(os.environ["GITHUB_INSTALLATION_ID"],), github_private_key=os.environ["GITHUB_PRIVATE_KEY"].replace("\\n","\n"), github_client_id=os.environ["GITHUB_CLIENT_ID"], github_client_secret=os.environ["GITHUB_CLIENT_SECRET"], github_webhook_secret=os.environ["GITHUB_WEBHOOK_SECRET"], webhook_url=os.environ["WEBHOOK_URL"].rstrip("/"), token_encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"], redis_url=os.getenv("REDIS_URL"), log_chat_id=int(log_chat_id) if log_chat_id else None)
