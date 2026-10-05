from pyrogram import filters
from ..buttons import repositories, repository, back, repository_list, repo_home, error_message, BRANCHES, files, files_text
from ..state import BrowserSession, SessionStore

def register(app, service, sessions: SessionStore):
    @app.on_message(filters.command("repos"))
    async def handle_repositories(client, message):
        try:
            user = await service.get_user()
            items = await service.list_for_user(user.get("login"))
            await message.reply_text(repository_list(items), reply_markup=repositories(items))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^repo:"))
    async def handle_repository(client, query):
        data = query.data
        await query.answer()
        parts = data.split(":")
        if len(parts) == 3 and parts[1].isdigit():
            repository_id = int(parts[1])
            repo = await service.get_by_id(repository_id)
            owner = repo["owner"]["login"]
            name = repo["name"]
            branch = repo.get("default_branch", "main")
            if parts[2] == "files":
                items = await service.contents(owner, name, "", branch)
                browser = BrowserSession(query.from_user.id, query.message.chat.id, repository_id, owner, name, branch, "")
                token = await sessions.create(browser)
                await query.message.edit_text(files_text(owner, name, branch, "", items), reply_markup=files(items, token))
                return
            if parts[2] == "branches":
                items = await service.branches(owner, name)
                body = f"<b>{BRANCHES}</b>\n\n" + "\n".join(f"<code>{item.get('name', 'branch')}</code>" for item in items[:30])
                await query.message.edit_text(body, reply_markup=back(f"repo:{repository_id}"))
                return
        if data.count(":") == 1:
            repository_id = int(data.split(":", 1)[1])
            repo = await service.get_by_id(repository_id)
            owner = repo["owner"]["login"]
            name = repo["name"]
            branch = repo.get("default_branch", "main")
            await query.message.edit_text(repo_home(owner, name, branch, repo.get("description")), reply_markup=repository(repository_id))
    return handle_repositories, handle_repository
