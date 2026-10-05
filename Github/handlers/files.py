import base64
from pyrogram import filters
from ..buttons import back, files, file_view, files_text, file_text, error_message, commit_preview, CommitView, commit_review
from ..state import EditSession, SessionStore
from ..github.commit import CommitEngine, CommitPlan, FileChange

def decode_content(data: dict) -> str:
    value = data.get("content", "")
    if data.get("encoding") == "base64":
        return base64.b64decode(value.replace("\n", "")).decode("utf-8", errors="replace")
    return value

def register(app, service, sessions: SessionStore):
    @app.on_callback_query(filters.regex(r"^file:"))
    async def handle_file(client, query):
        await query.answer()
        try:
            _, repository_id, index = query.data.split(":", 2)
            repository_id = int(repository_id)
            repo = await service.get_by_id(repository_id)
            owner = repo["owner"]["login"]
            name = repo["name"]
            branch = repo.get("default_branch", "main")
            items = await service.contents(owner, name, "", branch)
            item = items[int(index)]
            if item.get("type") == "dir":
                children = await service.contents(owner, name, item["path"], branch)
                await query.message.edit_text(files_text(owner, name, branch, item["path"], children), reply_markup=files(children, repository_id))
                return
            data = await service.file(owner, name, item["path"], branch)
            content = decode_content(data)
            session = EditSession(query.from_user.id, query.message.chat.id, repository_id, owner, name, branch, item["path"], content, base_head=(await service.branch_head(owner, name, branch)))
            token = await sessions.create(session)
            await query.message.edit_text(file_text(owner, name, item["path"], content, branch), reply_markup=file_view(repository_id, token))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)), reply_markup=back())

    @app.on_callback_query(filters.regex(r"^edit:"))
    async def handle_edit(client, query):
        await query.answer()
        token = query.data.split(":", 1)[1]
        session = await sessions.get(token)
        if not session or session.user_id != query.from_user.id:
            await query.message.edit_text(error_message("Edit session expired"), reply_markup=back())
            return
        session.status = "awaiting_content"
        await sessions.set(token, session)
        await query.message.edit_text(f"<b>Edit file</b>\n\n<code>{session.path}</code>\n\nSend the complete new file content as your next message.", reply_markup=back())

    @app.on_message(filters.text & ~filters.command(["start", "repos"]))
    async def handle_editor_message(client, message):
        token = await sessions.active(message.from_user.id)
        session = await sessions.get(token) if token else None
        if not session:
            return
        if session.status == "awaiting_content":
            session.content = message.text
            session.status = "awaiting_message"
            await sessions.set(token, session)
            await message.reply_text("<b>Commit message</b>\\n\\nSend the commit message for this change.", reply_markup=back())
            return
        if session.status == "awaiting_message":
            session.message = message.text.strip()
            session.status = "ready"
            await sessions.set(token, session)
            additions = sum(1 for line in (session.content or "").splitlines() if line.strip())
            preview = commit_preview(CommitView(f"{session.owner}/{session.name}", session.branch, 1, additions, 0, session.message))
            await message.reply_text(preview, reply_markup=commit_review(token))
            return

    @app.on_callback_query(filters.regex(r"^commit:"))
    async def handle_commit(client, query):
        await query.answer()
        _, token, action = query.data.split(":", 2)
        session = await sessions.get(token)
        if not session or session.user_id != query.from_user.id or session.status != "ready":
            await query.message.edit_text(error_message("Commit session expired"), reply_markup=back())
            return
        if action == "cancel":
            await sessions.delete(token)
            await query.message.edit_text("<b>Commit cancelled</b>", reply_markup=back(f"repo:{session.repository_id}"))
            return
        if action != "confirm":
            return
        engine = CommitEngine(service)
        try:
            plan = CommitPlan(f"{session.owner}/{session.name}", session.branch, session.message or "", [FileChange(session.path, "modified", session.content)])
            result = await engine.execute(plan, session.base_head)
            await sessions.delete(token)
            await query.message.edit_text(f"<b>Commit created</b>\\n\\n<code>{result[\"new_sha\"][:12]}</code>\\n<code>{session.path}</code>\\n\n{session.message}", reply_markup=back(f"repo:{session.repository_id}"))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)), reply_markup=back(f"repo:{session.repository_id}"))
    return handle_file, handle_edit, handle_commit
