import base64
import difflib
from pyrogram import filters
from ..buttons import back, files, file_view, files_text, file_text, error_message, commit_preview, CommitView, commit_review, edit_prompt, commit_prompt, commit_result, SESSION_EXPIRED, COMMIT_SESSION_EXPIRED, COMMIT_CANCELLED, UNCHANGED_FILE, INVALID_COMMIT_MESSAGE
from ..state import EditSession, BrowserSession, SessionStore
from ..github.commit import CommitEngine, CommitPlan, FileChange

def decode_content(data: dict) -> str:
    value = data.get("content", "")
    if data.get("encoding") == "base64":
        return base64.b64decode(value.replace("\n", "")).decode("utf-8", errors="replace")
    return value

def diff_stats(original: str, updated: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    matcher = difflib.SequenceMatcher(a=original.splitlines(), b=updated.splitlines())
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            deletions += a2 - a1
        if tag in {"replace", "insert"}:
            additions += b2 - b1
    return additions, deletions

def register(app, service, sessions: SessionStore):
    @app.on_callback_query(filters.regex(r"^file:"))
    async def handle_file(client, query):
        await query.answer()
        try:
            _, browser_token, index = query.data.split(":", 2)
            browser = await sessions.get(browser_token)
            if not isinstance(browser, BrowserSession) or browser.user_id != query.from_user.id or browser.chat_id != query.message.chat.id:
                await query.message.edit_text(error_message(SESSION_EXPIRED), reply_markup=back())
                return
            items = await service.contents(browser.owner, browser.name, browser.path, browser.branch)
            item = items[int(index)]
            if item.get("type") == "dir":
                children = await service.contents(browser.owner, browser.name, item["path"], browser.branch)
                child = BrowserSession(query.from_user.id, query.message.chat.id, browser.repository_id, browser.owner, browser.name, browser.branch, item["path"], browser_token)
                child_token = await sessions.create(child)
                await query.message.edit_text(files_text(browser.owner, browser.name, browser.branch, item["path"], children), reply_markup=files(children, child_token, browser_token))
                return
            data = await service.file(browser.owner, browser.name, item["path"], browser.branch)
            content = decode_content(data)
            session = EditSession(query.from_user.id, query.message.chat.id, browser.repository_id, browser.owner, browser.name, browser.branch, item["path"], content, base_head=await service.branch_head(browser.owner, browser.name, browser.branch), browser_token=browser_token)
            token = await sessions.create(session)
            await query.message.edit_text(file_text(browser.owner, browser.name, item["path"], content, browser.branch), reply_markup=file_view(browser.repository_id, token, browser_token))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)), reply_markup=back())

    @app.on_callback_query(filters.regex(r"^browse:"))
    async def handle_browse(client, query):
        await query.answer()
        try:
            _, token, action = query.data.split(":", 2)
            browser = await sessions.get(token)
            if not isinstance(browser, BrowserSession) or browser.user_id != query.from_user.id or browser.chat_id != query.message.chat.id:
                await query.message.edit_text(error_message(SESSION_EXPIRED), reply_markup=back())
                return
            if action != "back":
                return
            if browser.parent_token:
                parent = await sessions.get(browser.parent_token)
                if not isinstance(parent, BrowserSession):
                    await query.message.edit_text(error_message(SESSION_EXPIRED), reply_markup=back())
                    return
                items = await service.contents(parent.owner, parent.name, parent.path, parent.branch)
                await query.message.edit_text(files_text(parent.owner, parent.name, parent.branch, parent.path, items), reply_markup=files(items, browser.parent_token, parent.parent_token))
                await sessions.delete(token)
                return
            items = await service.contents(browser.owner, browser.name, "", browser.branch)
            await query.message.edit_text(files_text(browser.owner, browser.name, browser.branch, "", items), reply_markup=files(items, token))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)), reply_markup=back())

    @app.on_callback_query(filters.regex(r"^edit:"))
    async def handle_edit(client, query):
        await query.answer()
        token = query.data.split(":", 1)[1]
        session = await sessions.get(token)
        if not isinstance(session, EditSession) or session.user_id != query.from_user.id or session.chat_id != query.message.chat.id:
            await query.message.edit_text(error_message(SESSION_EXPIRED), reply_markup=back())
            return
        session.status = "awaiting_content"
        await sessions.set(token, session)
        await query.message.edit_text(edit_prompt(session.path), reply_markup=back(f"browse:{session.browser_token}:back"))

    @app.on_message(filters.text & ~filters.command(["start", "repos"]))
    async def handle_editor_message(client, message):
        token = await sessions.active(message.from_user.id)
        session = await sessions.get(token) if token else None
        if not isinstance(session, EditSession) or session.chat_id != message.chat.id:
            return
        if session.status == "awaiting_content":
            session.content = message.text
            session.status = "awaiting_message"
            await sessions.set(token, session)
            await message.reply_text(commit_prompt(), reply_markup=back(f"browse:{session.browser_token}:back"))
            return
        if session.status == "awaiting_message":
            session.message = message.text.strip()
            if not session.message:
                await message.reply_text(INVALID_COMMIT_MESSAGE)
                return
            additions, deletions = diff_stats(session.original, session.content or "")
            if additions == 0 and deletions == 0:
                await message.reply_text(UNCHANGED_FILE, reply_markup=back(f"browse:{session.browser_token}:back"))
                return
            session.status = "ready"
            await sessions.set(token, session)
            preview = commit_preview(CommitView(f"{session.owner}/{session.name}", session.branch, 1, additions, deletions, session.message))
            await message.reply_text(preview, reply_markup=commit_review(token))
            return

    @app.on_callback_query(filters.regex(r"^commit:"))
    async def handle_commit(client, query):
        await query.answer()
        _, token, action = query.data.split(":", 2)
        session = await sessions.get(token)
        if not isinstance(session, EditSession) or session.user_id != query.from_user.id or session.chat_id != query.message.chat.id or session.status != "ready":
            await query.message.edit_text(error_message(COMMIT_SESSION_EXPIRED), reply_markup=back())
            return
        if action == "cancel":
            await sessions.delete(token)
            await query.message.edit_text(f"<b>{COMMIT_CANCELLED}</b>", reply_markup=back(f"browse:{session.browser_token}:back"))
            return
        if action != "confirm":
            return
        try:
            plan = CommitPlan(f"{session.owner}/{session.name}", session.branch, session.message or "", [FileChange(session.path, "modified", session.content)])
            result = await CommitEngine(service).execute(plan, session.base_head)
            await sessions.delete(token)
            await query.message.edit_text(commit_result(result["new_sha"], session.path, session.message or ""), reply_markup=back(f"browse:{session.browser_token}:back"))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)), reply_markup=back(f"browse:{session.browser_token}:back"))
    return handle_file, handle_browse, handle_edit, handle_commit
