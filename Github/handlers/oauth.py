from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..buttons import connect_text, error_message
from ..github.oauth import GitHubOAuth
from ..state import OAuthState, SessionStore
from ..storage import GitHubStore

def register(app, oauth: GitHubOAuth, sessions: SessionStore, store: GitHubStore):
    @app.on_message(filters.command("connect"))
    async def connect(client, message):
        state, url, verifier = oauth.begin()
        token = await sessions.create(OAuthState(message.from_user.id, verifier))
        await sessions.set(token, OAuthState(message.from_user.id, verifier, sessions.ttl))
        await message.reply_text(connect_text(), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Authorize GitHub", url=url)]]))
    return connect
