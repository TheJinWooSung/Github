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
    oauth_callback_path = bot.config.oauth_callback_path
    webhook_path = bot.config.webhook_path

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get(oauth_callback_path, response_class=HTMLResponse)
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
        return HTMLResponse(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="dark light">
<script src="https://telegram.org/js/telegram-web-app.js?63"></script>
<title>GitHub · Web editor</title>
<style>
:root{{color-scheme:dark;--bg:#0b1020;--panel:#111a2e;--panel-2:#172239;--line:#273651;--text:#edf3ff;--muted:#93a4c1;--accent:#8b7cff;--accent-2:#6d5dfc;--good:#3dd9a4;--danger:#ff7388}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(900px 420px at 90% -10%,#29245b 0%,transparent 60%),var(--bg);color:var(--text);font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}}
.shell{{max-width:1100px;margin:0 auto;padding:clamp(14px,3vw,30px);display:flex;flex-direction:column;gap:18px;min-height:100vh}}
.topbar{{display:flex;align-items:center;justify-content:space-between;gap:14px}}.brand{{display:flex;align-items:center;gap:12px;min-width:0}}.mark{{display:grid;place-items:center;width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,#a69bff,#6554f5);color:white;font-size:20px;font-weight:800;box-shadow:0 8px 24px #6d5dfc35}}.eyebrow{{color:#a9a0ff;font-size:11px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}}h1{{font-size:clamp(20px,4vw,27px);line-height:1.2;margin:2px 0 0;letter-spacing:-.04em}}.subtitle{{color:var(--muted);font-size:12px;margin-top:3px;overflow-wrap:anywhere}}
.status{{display:flex;align-items:center;gap:7px;border:1px solid var(--line);background:#111a2eaa;padding:8px 11px;border-radius:999px;color:var(--muted);font-size:12px;white-space:nowrap}}.dot{{width:7px;height:7px;border-radius:50%;background:var(--good);box-shadow:0 0 12px #3dd9a477}}
.card{{background:linear-gradient(145deg,#131d32f2,#0f1728f2);border:1px solid var(--line);border-radius:20px;overflow:hidden;box-shadow:0 20px 60px #0002}}.filebar{{padding:14px 17px;display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);background:#ffffff03}}.file-meta{{min-width:0}}.file-label{{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.1em;font-weight:800}}.filepath{{font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere;margin-top:4px}}.branch{{display:inline-flex;align-items:center;gap:6px;color:#c5bdff;background:#8b7cff16;border:1px solid #8b7cff38;border-radius:8px;padding:5px 8px;font:12px ui-monospace,monospace;white-space:nowrap}}
.editor-wrap{{position:relative;padding:0;background:#0b1220}}.editor-head{{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;border-bottom:1px solid #202c42;color:var(--muted);font-size:11px}}.editor-head span:first-child{{display:flex;align-items:center;gap:7px}}.editor-lights{{display:flex;gap:5px}}.editor-lights i{{display:block;width:7px;height:7px;border-radius:50%;background:#ff6b79}}.editor-lights i:nth-child(2){{background:#ffc66d}}.editor-lights i:nth-child(3){{background:#4cdbab}}
textarea{{display:block;width:100%;min-height:52vh;height:calc(100dvh - 320px);max-height:900px;resize:vertical;border:0;outline:0;padding:20px clamp(14px,3vw,26px);background:transparent;color:#dce7ff;font:13px/1.75 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;tab-size:4;caret-color:#a69bff;white-space:pre;overflow:auto}}textarea:focus{{box-shadow:inset 0 0 0 1px #8b7cff30}}textarea::selection{{background:#6657d966}}
.footer{{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:14px 17px;border-top:1px solid var(--line);background:#ffffff03}}.hint{{color:var(--muted);font-size:12px;min-width:0}}.actions{{display:flex;gap:9px;align-items:center;flex-shrink:0}}button{{appearance:none;border:1px solid var(--line);border-radius:11px;padding:11px 15px;background:var(--panel-2);color:var(--text);font:600 13px inherit;cursor:pointer;transition:transform .15s,border-color .15s,opacity .15s}}button:hover{{border-color:#8174ff;transform:translateY(-1px)}}button:disabled{{opacity:.55;cursor:wait;transform:none}}.primary{{border-color:transparent;background:linear-gradient(135deg,#9184ff,#6655f5);color:white;box-shadow:0 7px 20px #6655f533}}.message{{display:none;border-radius:12px;padding:11px 14px;font-size:13px;overflow-wrap:anywhere}}.message.show{{display:block}}.message.error{{background:#ff738812;border:1px solid #ff73883d;color:#ff9baa}}.message.success{{background:#3dd9a411;border:1px solid #3dd9a43d;color:#7ae8c3}}.loading{{color:var(--muted);padding:20px;text-align:center}}
@media(max-width:560px){{.shell{{padding:14px;gap:13px}}.topbar{{align-items:flex-start}}.status{{font-size:0;padding:10px}}.status .dot{{width:8px;height:8px}}.filebar{{align-items:flex-start;flex-direction:column}}textarea{{height:calc(100dvh - 360px);min-height:42vh;padding:15px;font-size:12px}}.footer{{align-items:stretch;flex-direction:column}}.actions{{display:grid;grid-template-columns:1fr 1fr}}button{{padding:12px 10px}}.hint{{line-height:1.4}}}}
</style>
</head>
<body>
<main class="shell">
<header class="topbar">
<div class="brand"><div class="mark">⌘</div><div><div class="eyebrow">GitHub control center</div><h1>Web editor</h1><div class="subtitle">Edit a file and commit it straight to your repository.</div></div></div>
<div class="status"><span class="dot"></span><span id="state">Connecting</span></div>
</header>
<div id="message" class="message" role="status" aria-live="polite"></div>
<section class="card">
<div class="filebar"><div class="file-meta"><div class="file-label">Editing file</div><div class="filepath">{html.escape(path)}</div></div><div class="branch">⑂ {html.escape(branch)}</div></div>
<div class="editor-wrap"><div class="editor-head"><span><span class="editor-lights"><i></i><i></i><i></i></span> SOURCE</span><span id="counter">Loading file…</span></div><textarea id="e" spellcheck="false" autocapitalize="off" autocomplete="off" autocorrect="off" aria-label="File contents" placeholder="Loading file…" disabled></textarea><div id="loading" class="loading">Loading file contents…</div></div>
<div class="footer"><div class="hint" id="hint">Your changes are not committed until you choose Commit changes.</div><div class="actions"><button id="close" type="button">Close editor</button><button id="save" class="primary" type="button" disabled>Commit changes ↗</button></div></div>
</section>
</main>
<script>
const tg=window.Telegram?.WebApp;
const e=document.getElementById("e"),saveButton=document.getElementById("save"),closeButton=document.getElementById("close"),state=document.getElementById("state"),counter=document.getElementById("counter"),loading=document.getElementById("loading"),message=document.getElementById("message"),hint=document.getElementById("hint");
if(tg){{tg.ready();tg.expand();tg.setHeaderColor?.("#0b1020");tg.setBackgroundColor?.("#0b1020");}}
const headers={{"X-Telegram-Init-Data":tg?.initData||""}};
let originalContent="",loaded=false;
function showMessage(text,type){{message.textContent=text;message.className="message show "+type;}}
function updateCount(){{const lines=e.value?e.value.split("\n").length:0;counter.textContent=lines+" lines · "+new TextEncoder().encode(e.value).length.toLocaleString()+" bytes";}}
async function load(){{try{{const r=await fetch("/api/webapp/file?repo={repo}&path="+encodeURIComponent({json.dumps(path)})+"&branch="+encodeURIComponent({json.dumps(branch)}),{{headers}});const d=await r.json();if(!r.ok)throw Error(d.detail||"Could not load this file");e.value=d.content||"";originalContent=e.value;loaded=true;e.disabled=false;saveButton.disabled=false;loading.hidden=true;state.textContent="File loaded";hint.textContent="Edits stay in this editor until you commit them.";updateCount();}}catch(err){{loading.textContent="Unable to load file";state.textContent="Load failed";showMessage(err.message||"Could not load file","error");}}}}
e.addEventListener("input",()=>{{updateCount();state.textContent=e.value===originalContent?"No changes":"Unsaved edits";}});
closeButton.addEventListener("click",()=>{{if(e.value!==originalContent&&!confirm("Discard your uncommitted changes and close?"))return;if(tg)tg.close();else window.history.back();}});
saveButton.addEventListener("click",async()=>{{if(!loaded)return;if(e.value===originalContent){{showMessage("There are no changes to commit.","error");return;}}const commitMessage=prompt("Commit message");if(!commitMessage||!commitMessage.trim())return;saveButton.disabled=true;saveButton.textContent="Committing…";state.textContent="Saving changes";message.className="message";try{{const r=await fetch("/api/webapp/commit",{{method:"POST",headers:Object.assign({{"Content-Type":"application/json"}},headers),body:JSON.stringify({{repo:{repo},path:{json.dumps(path)},branch:{json.dumps(branch)},content:e.value,message:commitMessage.trim()}})}});const d=await r.json();if(!r.ok)throw Error(d.detail||"Commit failed");originalContent=e.value;state.textContent="Committed";hint.textContent="Commit "+d.sha.slice(0,10)+" created successfully.";showMessage("Changes committed · "+d.sha.slice(0,10),"success");if(tg?.HapticFeedback)tg.HapticFeedback.notificationOccurred("success");}}catch(err){{state.textContent="Commit failed";showMessage(err.message||"Commit failed","error");if(tg?.HapticFeedback)tg.HapticFeedback.notificationOccurred("error");}}finally{{saveButton.disabled=false;saveButton.textContent="Commit changes ↗";}}}});
load();
</script>
</body>
</html>""")

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

    @app.post(webhook_path)
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
