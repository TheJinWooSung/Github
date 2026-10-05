import base64
from pyrogram import filters
from ..buttons import back, files, file_view, files_text, file_text, error_message
from ..state import EditSession, SessionStore

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
        active = None
        token = None
        for key, value in list(sessions.memory.items()):
            if value.user_id == message.from_user.id and value.status == "awaiting_content":
                active, token = value, key
                break
        if not active:
            return
        active.content = message.text
        active.status = "awaiting_message"
        await sessions.set(token, active)
        await message.reply_text("<b>Commit message</b>\n\nSend the commit message for this change.", reply_markup=back())

    @app.on_message(filters.text & ~filters.command(["start", "repos"]))
    async def handle_commit_message(client, message):
        for key, value in list(sessions.memory.items()):
            if value.user_id == message.from_user.id and value.status == "awaiting_message":
                value.message = message.text.strip()
                value.status = "ready"
                await sessions.set(key, value)
                await message.reply_text(f"<b>Review changes</b>\n\n<code>{value.owner}/{value.name}</code> · <code>{value.branch}</code>\n\nFILE  <code>{value.path}</code>\n\n<b>Commit message</b>\n<code>{value.message}</code>\n\nConfirm this commit?", reply_markup=back(f"commit:{key}:confirm"))
                return
    return handle_file, handle_edit
