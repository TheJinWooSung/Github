from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Config:
    bot_token: str
    mongo_uri: str
    github_app_id: int
    github_private_key: str
    github_client_id: str
    github_client_secret: str
    github_webhook_secret: str
    webhook_url: str

    @classmethod
    def from_env(cls):
        required = ("BOT_TOKEN", "MONGO_URI", "GITHUB_APP_ID", "GITHUB_PRIVATE_KEY", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GITHUB_WEBHOOK_SECRET", "WEBHOOK_URL")
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
        return cls(bot_token=os.environ["BOT_TOKEN"], mongo_uri=os.environ["MONGO_URI"], github_app_id=int(os.environ["GITHUB_APP_ID"]), github_private_key=os.environ["GITHUB_PRIVATE_KEY"].replace("\\n", "\n"), github_client_id=os.environ["GITHUB_CLIENT_ID"], github_client_secret=os.environ["GITHUB_CLIENT_SECRET"], github_webhook_secret=os.environ["GITHUB_WEBHOOK_SECRET"], webhook_url=os.environ["WEBHOOK_URL"])
