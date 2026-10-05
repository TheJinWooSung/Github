import asyncio
from pyrogram import Client
from .config import Config
from .github.auth import GitHubAppAuth
from .github.client import GitHubClient
from .github.oauth import GitHubOAuth
from .github.repositories import RepositoryService
from .handlers.start import register as register_start
from .handlers.repos import register as register_repositories
from .handlers.files import register as register_files
from .handlers.oauth import register as register_oauth
from .handlers.integrations import register as register_integrations
from .handlers.pulls import register as register_pulls
from .handlers.pr_commands import register as register_pr_commands
from .handlers.replies import register as register_replies
from .handlers.actions import register as register_actions
from .handlers.action_commands import register as register_action_commands
from .handlers.discussions import register as register_discussions
from .handlers.commands import register as register_commands
from .state import SessionStore
from .storage import GitHubStore
from .web import build_web

class GitHubBot:
    def __init__(self, config: Config):
        self.config = config
        self.app = Client(config.bot_session_name, api_id=config.api_id, api_hash=config.api_hash, bot_token=config.bot_token, in_memory=True)
        self.github = GitHubClient("", timeout=config.request_timeout, base_url=config.github_api_url, api_version=config.github_api_version)
        self.repositories = RepositoryService(self.github)
        self.sessions = SessionStore(config.redis_url)
        self.store = GitHubStore(config.mongo_uri, config.token_encryption_key)
        self.auth = GitHubAppAuth(config.github_app_id, config.github_private_key, timeout=config.request_timeout, api_version=config.github_api_version, base_url=config.github_api_url)
        self.oauth = GitHubOAuth(config.github_client_id, config.github_client_secret, f"{config.webhook_url}{config.oauth_callback_path}", timeout=config.request_timeout, api_version=config.github_api_version)
        self.web = build_web(self, self.oauth, self.sessions, self.store)
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
        register_repositories(self.app, self.repositories, self.sessions, self.store)
        register_files(self.app, self.repositories, self.sessions, self.config.webhook_url)
        register_oauth(self.app, self.oauth, self.sessions, self.store)
        register_integrations(self.app, self.store, self.oauth, f"{self.config.webhook_url}{self.config.webhook_path}", self.config.github_webhook_secret)
        register_pulls(self.app, self.store, self.sessions, self.oauth)
        register_pr_commands(self.app, self.store, self.oauth)
        register_replies(self.app, self.store, self.oauth)
        register_actions(self.app, self.store, self.oauth)
        register_action_commands(self.app, self.store, self.oauth)
        register_discussions(self.app, self.store, self.oauth)
        register_commands(self.app, self.store, self.oauth)
        self._registered = True
        return self

    async def start(self):
        await self.store.setup()
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
        await self.store.close()

    def run(self):
        self.register()
        self.app.run()

def build_bot(config: Config) -> GitHubBot:
    return GitHubBot(config).register()
