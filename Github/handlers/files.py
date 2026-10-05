import base64
import difflib
from pyrogram import filters
from ..buttons import back, files, file_view, files_text, file_text, error_message, commit_preview, CommitView, commit_review, edit_prompt, commit_prompt, commit_result, stage_actions, staged_text, SESSION_EXPIRED, COMMIT_SESSION_EXPIRED, COMMIT_CANCELLED, UNCHANGED_FILE, INVALID_COMMIT_MESSAGE
from ..state import EditSession, BrowserSession, SessionStore, CommitStageSession, StagedChange
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

def register(app, service, sessions: SessionStore, webapp_url: str | None = None):
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
            await query.message.edit_text(file_text(browser.owner, browser.name, item["path"], content, browser.branch), reply_markup=file_view(browser.repository_id, token, browser_token, webapp_url, item["path"], browser.branch))
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
            existing_token = await sessions.stage(message.from_user.id)
            stage = await sessions.get(existing_token) if existing_token else None
            if not isinstance(stage, CommitStageSession) or stage.chat_id != message.chat.id or stage.repository_id != session.repository_id or stage.branch != session.branch:
                stage = CommitStageSession(message.from_user.id, message.chat.id, session.repository_id, session.owner, session.name, session.branch, [])
                existing_token = await sessions.create_stage(stage)
            stage.changes = [item for item in stage.changes if item.path != session.path]
            stage.changes.append(StagedChange(session.path, "modified", session.content, additions, deletions))
            await sessions.set(existing_token, stage)
            await sessions.delete(token)
            await message.reply_text(staged_text(f"{stage.owner}/{stage.name}", stage.branch, stage.changes), reply_markup=stage_actions(existing_token))
            return

    @app.on_callback_query(filters.regex(r"^commit:"))
    async def handle_commit(client, query):
        await query.answer()
        _, token, action = query.data.split(":", 2)
        session = await sessions.get(token)
        if not isinstance(session, EditSession) or session.user_id != query.from_user.id:
            await query.message.edit_text(error_message(COMMIT_SESSION_EXPIRED), reply_markup=back())
            return
        if action == "cancel":
            await sessions.delete(token)
            await query.message.edit_text(f"<b>{COMMIT_CANCELLED}</b>", reply_markup=back(f"browse:{session.browser_token}:back"))
            return

    @app.on_callback_query(filters.regex(r"^stage:"))
    async def handle_stage(client, query):
        await query.answer()
        _, token, action = query.data.split(":", 2)
        stage = await sessions.get(token)
        if not isinstance(stage, CommitStageSession) or stage.user_id != query.from_user.id or stage.chat_id != query.message.chat.id:
            await query.message.edit_text(error_message(COMMIT_SESSION_EXPIRED), reply_markup=back())
            return
        if action == "clear":
            await sessions.delete(token)
            await query.message.edit_text("<b>Staged changes cleared.</b>", reply_markup=back("nav:back"))
            return
        if action != "commit" or not stage.changes:
            await query.message.edit_text(staged_text(f"{stage.owner}/{stage.name}", stage.branch, stage.changes), reply_markup=stage_actions(token))
            return
        try:
            await query.message.edit_text(staged_text(f"{stage.owner}/{stage.name}", stage.branch, stage.changes))
            await query.message.reply_text("Send the commit message.")
            stage.status = "awaiting_message"
            await sessions.set(token, stage)
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)), reply_markup=back())
    
    @app.on_message(filters.text & ~filters.command(["start", "repos"]))
    async def handle_staged_message(client, message):
        token = await sessions.stage(message.from_user.id)
        stage = await sessions.get(token) if token else None
        if not isinstance(stage, CommitStageSession) or stage.chat_id != message.chat.id or getattr(stage, "status", "awaiting_message") != "awaiting_message":
            return
        text_value = message.text.strip()
        if not text_value:
            await message.reply_text(INVALID_COMMIT_MESSAGE)
            return
        plan = CommitPlan(f"{stage.owner}/{stage.name}", stage.branch, text_value, [FileChange(x.path, x.status, x.content, x.additions, x.deletions) for x in stage.changes])
        try:
            engine = CommitEngine(service)
            result = await engine.execute(plan)
            await sessions.delete(token)
            await message.reply_text(commit_result(result["new_sha"], f"{len(stage.changes)} files", text_value), reply_markup=back("nav:back"))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)), reply_markup=stage_actions(token))

    return handle_file, handle_browse, handle_edit, handle_commit
