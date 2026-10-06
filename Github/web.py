import hashlib
import hmac
import html
import json
import time
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

def verify_signature(body: bytes, secret: str, signature: str | None) -> None:
    if not signature:
        raise HTTPException(status_code=403, detail="Missing webhook signature")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

def event_text(event: str, payload: dict) -> tuple[str, int | None]:
    repository = html.escape(payload.get("repository", {}).get("full_name", "unknown/repository"))
    action = html.escape(payload.get("action", "updated"))
    sender = html.escape(payload.get("sender", {}).get("login", "unknown"))
    if event == "push":
        ref = html.escape(payload.get("ref", "").removeprefix("refs/heads/"))
        count = len(payload.get("commits", []))
        return f"<b>{repository}</b>\n\n<b>Push</b> · <code>{ref}</code>\n{sender} pushed {count} commit(s).", None
    if event == "pull_request":
        item = payload.get("pull_request", {})
        number = item.get("number") or payload.get("number")
        title = html.escape(item.get("title", "Pull request"))
        return f"<b>{repository}</b>\n\n<b>Pull request #{number}</b> · {action}\n{title}\nby <code>{sender}</code>", number
    if event == "issues":
        item = payload.get("issue", {})
        number = item.get("number")
        title = html.escape(item.get("title", "Issue"))
        return f"<b>{repository}</b>\n\n<b>Issue #{number}</b> · {action}\n{title}\nby <code>{sender}</code>", number
    if event == "release":
        release = payload.get("release", {})
        title = html.escape(release.get("name") or release.get("tag_name", "release"))
        return f"<b>{repository}</b>\n\n<b>Release</b> · {action}\n{title}", None
    if event == "workflow_run":
        run = payload.get("workflow_run", {})
        name = html.escape(run.get("name", "workflow"))
        state = html.escape(run.get("conclusion") or run.get("status", "unknown"))
        return f"<b>{repository}</b>\n\n<b>Actions</b> · {action}\n{name} · <code>{state}</code>", run.get("id")
    if event == "star":
        return f"<b>{repository}</b>\n\n<b>Star</b> · {action}\nby <code>{sender}</code>", None
    return f"<b>{repository}</b>\n\n<b>{html.escape(event)}</b> · {action}\nby <code>{sender}</code>", None

def validate_webapp_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> int:
    from urllib.parse import parse_qsl
    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", None)
    if not received_hash: raise HTTPException(status_code=403, detail="Invalid Telegram WebApp data")
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash): raise HTTPException(status_code=403, detail="Invalid Telegram WebApp data")
    try:
        auth_date = int(fields.get("auth_date", "0")); user = json.loads(fields.get("user", "{}")); telegram_id = int(user["id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError): raise HTTPException(status_code=403, detail="Invalid Telegram WebApp user")
    if auth_date <= 0 or time.time() - auth_date > max_age: raise HTTPException(status_code=403, detail="Expired Telegram WebApp data")
    return telegram_id

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
        if not session or not hasattr(session, "telegram_id") or session.expires_at <= time.time():
            return HTMLResponse("<h2>Authorization session expired.</h2>", status_code=400)
        try:
            grant = await oauth.exchange(code, session.verifier)
            profile = await oauth.user(grant.access_token)
            await store.save_user(session.telegram_id, profile, grant)
            await bot.app.send_message(session.telegram_id, "<b>GitHub connected</b>\n\nYour GitHub account is now authorized.")
            await sessions.delete(state)
            return HTMLResponse("<h2>GitHub connected</h2><p>You can return to Telegram.</p>")
        except Exception:
            return HTMLResponse("<h2>GitHub authorization failed.</h2><p>Please restart /connect and try again.</p>", status_code=400)

    @app.get("/webapp/editor", response_class=HTMLResponse)
    async def editor(repo: int, path: str, branch: str):
        return HTMLResponse(f"""<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><script src="https://telegram.org/js/telegram-web-app.js?63"></script><style>body{{margin:0;background:var(--tg-theme-bg-color,#111);color:var(--tg-theme-text-color,#fff);font-family:system-ui}}header{{padding:12px 14px}}textarea{{width:100%;height:calc(100vh - 120px);box-sizing:border-box;background:var(--tg-theme-secondary-bg-color,#181818);color:inherit;border:0;outline:0;padding:14px;font:13px/1.5 monospace;resize:none}}button{{margin:8px;padding:11px 18px;border:0;border-radius:9px;background:var(--tg-theme-button-color,#2481cc);color:var(--tg-theme-button-text-color,#fff)}}small{{opacity:.65}}</style><header><b>Editor</b><br><small>{html.escape(path)}</small></header><textarea id="e"></textarea><div><button onclick="save()">Commit</button><button onclick="Telegram.WebApp.close()">Close</button></div><script>const tg=Telegram.WebApp;tg.ready();tg.expand();const e=document.getElementById("e");const h={{"X-Telegram-Init-Data":tg.initData}};async function load(){{const r=await fetch("/api/webapp/file?repo={repo}&path="+encodeURIComponent({json.dumps(path)})+"&branch="+encodeURIComponent({json.dumps(branch)}),{{headers:h}});const d=await r.json();if(!r.ok)throw Error(d.detail);e.value=d.content||""}}async function save(){{const message=prompt("Commit message");if(!message)return;const r=await fetch("/api/webapp/commit",{{method:"POST",headers:Object.assign({{"Content-Type":"application/json"}},h),body:JSON.stringify({{repo:{repo},path:{json.dumps(path)},branch:{json.dumps(branch)},content:e.value,message}})}});const d=await r.json();if(!r.ok){{alert(d.detail||"Commit failed");return}}alert("Committed "+d.sha.slice(0,10));tg.HapticFeedback&&tg.HapticFeedback.notificationOccurred("success")}}load().catch(e=>alert(e.message));</script>""")

    async def webapp_user(request: Request) -> int:
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        return validate_webapp_init_data(init_data, bot.config.bot_token)

    @app.get("/api/webapp/file")
    async def webapp_file(request: Request, repo: int, path: str, branch: str):
        telegram_id = await webapp_user(request)
        linked = await store.repository(telegram_id, repo)
        if not linked: raise HTTPException(status_code=403, detail="Repository is not connected")
        token = await store.token(telegram_id, oauth)
        if not token: raise HTTPException(status_code=401, detail="Connect GitHub first")
        from .github.client import GitHubClient
        from .github.repositories import RepositoryService
        service = RepositoryService(GitHubClient(token, timeout=bot.config.request_timeout, base_url=bot.config.github_api_url, api_version=bot.config.github_api_version))
        data = await service.file(linked["owner"], linked["name"], path, branch)
        if data.get("type") != "file": raise HTTPException(status_code=400, detail="Requested path is not a file")
        content = data.get("content", "")
        if data.get("encoding") == "base64":
            import base64
            content = base64.b64decode(content.replace("\n", "")).decode("utf-8", errors="replace")
        return {"repository": linked["full_name"], "path": path, "branch": branch, "content": content}

    @app.post("/api/webapp/commit")
    async def webapp_commit(request: Request):
        telegram_id = await webapp_user(request)
        payload = await request.json()
        repo_id, path, branch, content, message = int(payload.get("repo", 0)), str(payload.get("path", "")).strip(), str(payload.get("branch", "")).strip(), payload.get("content"), str(payload.get("message", "")).strip()
        if not repo_id or not path or not branch or not isinstance(content, str) or not message: raise HTTPException(status_code=400, detail="Invalid commit request")
        linked = await store.repository(telegram_id, repo_id)
        if not linked: raise HTTPException(status_code=403, detail="Repository is not connected")
        token = await store.token(telegram_id, oauth)
        if not token: raise HTTPException(status_code=401, detail="Connect GitHub first")
        from .github.client import GitHubClient
        from .github.repositories import RepositoryService
        from .github.commit import CommitEngine, CommitPlan, FileChange
        service = RepositoryService(GitHubClient(token, timeout=bot.config.request_timeout, base_url=bot.config.github_api_url, api_version=bot.config.github_api_version))
        current = await service.branch_head(linked["owner"], linked["name"], branch)
        old = await service.file(linked["owner"], linked["name"], path, branch)
        old_content = old.get("content", "")
        if old.get("encoding") == "base64":
            import base64
            old_content = base64.b64decode(old_content.replace("\n", "")).decode("utf-8", errors="replace")
        if content == old_content: raise HTTPException(status_code=400, detail="No changes were made")
        plan = CommitPlan(linked["full_name"], branch, message, [FileChange(path, "modified", content)])
        result = await CommitEngine(service).execute(plan, expected_head=current)
        return {"sha": result["new_sha"], "repository": linked["full_name"], "path": path, "branch": branch}

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
        repository = payload.get("repository", {})
        repository_id = repository.get("id")
        if not repository_id:
            return {"status": "ignored"}
        integrations = await store.integrations_for_repository(repository_id)
        text, number = event_text(x_github_event, payload)
        for integration in integrations:
            settings = await store.get_settings(integration["telegram_id"])
            if not settings.get("notifications_enabled", True):
                continue
            if settings.get(f"mute:{repository_id}", False):
                continue
            if integration.get("active", True) is False:
                continue
            if x_github_event not in (integration.get("events") or []):
                continue
            if not await store.claim_delivery(x_github_delivery, integration["telegram_id"], repository_id, x_github_event, number, 0):
                continue
            try:
                message = await bot.app.send_message(integration["telegram_id"], text)
                await store.save_delivery(x_github_delivery, integration["telegram_id"], repository_id, x_github_event, number, message.id)
            except Exception as exc:
                await store.fail_delivery(x_github_delivery, integration["telegram_id"], str(exc))
        return {"status": "ok"}

    return app
