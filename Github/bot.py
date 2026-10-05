import asyncio
from pyrogram import Client
from .config import Config
from .github.auth import GitHubAppAuth
from .github.client import GitHubClient
from .github.repositories import RepositoryService
from .handlers.start import register as register_start
from .handlers.repos import register as register_repositories
from .handlers.files import register as register_files
from .state import SessionStore

class GitHubBot:
    def __init__(self, config: Config):
        self.config = config
        self.app = Client("github_control_center", api_id=config.api_id, api_hash=config.api_hash, bot_token=config.bot_token, in_memory=True)
        self.github = GitHubClient("")
        self.repositories = RepositoryService(self.github)
        self.sessions = SessionStore(config.redis_url)
        self.auth = GitHubAppAuth(config.github_app_id, config.github_private_key)
        self._auth_task: asyncio.Task | None = None
        self._registered = False

    async def authenticate(self):
        data = await self.auth.installation_token(self.config.github_installation_id)
        token = data.get("token")
        if not token:
            raise RuntimeError("GitHub installation token was not returned")
        self.github.token = token

    async def _refresh_auth(self):
        while True:
            await asyncio.sleep(45 * 60)
            try:
                await self.authenticate()
            except Exception:
                await asyncio.sleep(60)
                try:
                    await self.authenticate()
                except Exception:
                    continue

    def register(self):
        if self._registered:
            return self
        register_start(self.app)
        register_repositories(self.app, self.repositories, self.sessions)
        register_files(self.app, self.repositories, self.sessions)
        self._registered = True
        return self

    async def start(self):
        await self.authenticate()
        self.register()
        await self.app.start()
        self._auth_task = asyncio.create_task(self._refresh_auth())

    async def stop(self):
        if self._auth_task:
            self._auth_task.cancel()
            try:
                await self._auth_task
            except asyncio.CancelledError:
                pass
            self._auth_task = None
        if self.app.is_connected:
            await self.app.stop()
        await self.sessions.close()

    def run(self):
        self.register()
        self.app.run()

def build_bot(config: Config) -> GitHubBot:
    return GitHubBot(config).register()
