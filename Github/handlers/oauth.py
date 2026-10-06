import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..buttons import AUTHORIZE_GITHUB, connect_text
from ..github.oauth import GitHubOAuth
from ..state import OAuthState, SessionStore
from ..storage import GitHubStore

def register(app, oauth: GitHubOAuth, sessions: SessionStore, store: GitHubStore):
    @app.on_message(filters.command("connect"))
    async def connect(client, message):
        state, url, verifier = oauth.begin()
        await sessions.set(state, OAuthState(message.from_user.id, verifier, time.time() + sessions.ttl))
        await message.reply_text(connect_text(), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(AUTHORIZE_GITHUB, url=url)]]))
    return connect
