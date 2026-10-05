from pyrogram import filters
from ..buttons import repositories, repository, back, repository_list, repo_home, error_message, FILES, BRANCHES

def register(app, service):
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
        if data == "repo:files":
            await query.message.edit_text(f"<b>{FILES}</b>", reply_markup=back())
            return
        if data == "repo:branches":
            await query.message.edit_text(f"<b>{BRANCHES}</b>", reply_markup=back())
            return
        if data.count(":") == 1:
            repository_id = int(data.split(":", 1)[1])
            repo = await service.get_by_id(repository_id)
            owner = repo["owner"]["login"]
            name = repo["name"]
            branch = repo.get("default_branch", "main")
            await query.message.edit_text(repo_home(owner, name, branch, repo.get("description")), reply_markup=repository(repository_id))
    return handle_repositories, handle_repository
