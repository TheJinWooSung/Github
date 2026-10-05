from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from .github.oauth import GitHubOAuth
from .state import SessionStore
from .storage import GitHubStore

def build_web(bot, oauth: GitHubOAuth, sessions: SessionStore, store: GitHubStore):
    app = FastAPI(title="GitHub Telegram Control Center")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/oauth/callback", response_class=HTMLResponse)
    async def oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
        if error:
            return HTMLResponse("<h2>GitHub authorization cancelled.</h2>", status_code=400)
        if not code or not state:
            return HTMLResponse("<h2>Missing OAuth response.</h2>", status_code=400)
        session = await sessions.get(state)
        if not session or not hasattr(session, "telegram_id") or session.expires_at <= __import__("time").time():
            return HTMLResponse("<h2>Authorization session expired.</h2>", status_code=400)
        try:
            grant = await oauth.exchange(code, session.verifier)
            profile = await oauth.user(grant.access_token)
            await store.save_user(session.telegram_id, profile, grant)
            await bot.app.send_message(session.telegram_id, "<b>GitHub connected</b>\n\nYour GitHub account is now authorized.")
            await sessions.delete(state)
            return HTMLResponse("<h2>GitHub connected</h2><p>You can return to Telegram.</p>")
        except Exception as exc:
            return HTMLResponse(f"<h2>GitHub authorization failed</h2><p>{str(exc)}</p>", status_code=400)

    return app
