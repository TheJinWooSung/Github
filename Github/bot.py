from pyrogram import Client
from .config import Config
from .github.auth import GitHubAppAuth
from .github.client import GitHubClient
from .github.repositories import RepositoryService
from .handlers.start import register as register_start
from .handlers.repos import register as register_repositories

class GitHubBot:
    def __init__(self, config: Config):
        self.config = config
        self.app = Client("github_control_center", api_id=config.api_id, api_hash=config.api_hash, bot_token=config.bot_token, in_memory=True)
        self.github = GitHubClient("")
        self.repositories = RepositoryService(self.github)
        self._registered = False

    async def authenticate(self):
        auth = GitHubAppAuth(self.config.github_app_id, self.config.github_private_key)
        data = await auth.installation_token(self.config.github_installation_id)
        token = data.get("token")
        if not token:
            raise RuntimeError("GitHub installation token was not returned")
        self.github.token = token

    def register(self):
        if self._registered:
            return self
        register_start(self.app)
        register_repositories(self.app, self.repositories)
        self._registered = True
        return self

    async def start(self):
        await self.authenticate()
        self.register()
        await self.app.start()

    async def stop(self):
        if self.app.is_connected:
            await self.app.stop()

    def run(self):
        self.register()
        self.app.run()

def build_bot(config: Config) -> GitHubBot:
    return GitHubBot(config).register()
