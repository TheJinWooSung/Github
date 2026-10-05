import hashlib
import hmac
import json
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

def verify_signature(body: bytes, secret: str, signature: str | None) -> None:
    if not signature:
        raise HTTPException(status_code=403, detail="Missing webhook signature")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

def event_text(event: str, payload: dict) -> tuple[str, int | None]:
    repository = payload.get("repository", {}).get("full_name", "unknown/repository")
    action = payload.get("action", "updated")
    sender = payload.get("sender", {}).get("login", "unknown")
    if event == "push":
        ref = payload.get("ref", "").removeprefix("refs/heads/")
        count = len(payload.get("commits", []))
        return f"<b>{repository}</b>\n\n<b>Push</b> · <code>{ref}</code>\n{sender} pushed {count} commit(s).", None
    if event == "pull_request":
        item = payload.get("pull_request", {})
        number = item.get("number") or payload.get("number")
        title = item.get("title", "Pull request")
        return f"<b>{repository}</b>\n\n<b>Pull request #{number}</b> · {action}\n{title}\nby <code>{sender}</code>", number
    if event == "issues":
        item = payload.get("issue", {})
        number = item.get("number")
        title = item.get("title", "Issue")
        return f"<b>{repository}</b>\n\n<b>Issue #{number}</b> · {action}\n{title}\nby <code>{sender}</code>", number
    if event == "release":
        release = payload.get("release", {})
        return f"<b>{repository}</b>\n\n<b>Release</b> · {action}\n{release.get('name') or release.get('tag_name', 'release')}", None
    if event == "workflow_run":
        run = payload.get("workflow_run", {})
        return f"<b>{repository}</b>\n\n<b>Actions</b> · {action}\n{run.get('name', 'workflow')} · <code>{run.get('conclusion') or run.get('status', 'unknown')}</code>", None
    if event == "star":
        return f"<b>{repository}</b>\n\n<b>Star</b> · {action}\nby <code>{sender}</code>", None
    return f"<b>{repository}</b>\n\n<b>{event}</b> · {action}\nby <code>{sender}</code>", None

def build_web(bot, oauth, sessions, store):
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

    @app.post("/webhooks/github")
    async def github_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None), x_github_event: str | None = Header(default=None), x_github_delivery: str | None = Header(default=None)):
        body = await request.body()
        verify_signature(body, bot.config.github_webhook_secret, x_hub_signature_256)
        if not x_github_event or not x_github_delivery:
            raise HTTPException(status_code=400, detail="Missing GitHub delivery headers")
        try:
            payload = json.loads(body)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        repository_id = payload.get("repository", {}).get("id")
        if not repository_id:
            return {"status": "ignored"}
        integrations = await store.integrations_for_repository(repository_id)
        text, number = event_text(x_github_event, payload)
        for integration in integrations:
            if not await store.claim_delivery(x_github_delivery, integration["telegram_id"], repository_id, x_github_event, number, 0):
                continue
            message = await bot.app.send_message(integration["telegram_id"], text)
            await store.save_delivery(x_github_delivery, integration["telegram_id"], repository_id, x_github_event, number, message.id)
        return {"status": "ok"}

    return app
