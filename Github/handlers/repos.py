from pyrogram import filters
from ..buttons import repository, back, files, files_text, repo_home, error_message, BRANCHES
from ..state import BrowserSession, SessionStore

def register(app, service, sessions: SessionStore, store=None):
    @app.on_callback_query(filters.regex(r"^repo:"))
    async def handle_repository(client, query):
        await query.answer()
        try:
            data = query.data
            parts = data.split(":")
            if len(parts) == 3 and parts[1].isdigit():
                repository_id = int(parts[1])
                repo = await service.get_by_id(repository_id)
                if store:
                    await store.add_repository(query.from_user.id, repo)
                    await store.set_current_repository(query.from_user.id, repository_id)
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
                if parts[2] == "tags":
                    items = await service.tags(owner, name)
                    body = f"<b>Tags</b>\n\n" + ("\n".join(f"<code>{item.get('name', 'tag')}</code>" for item in items[:30]) or "No tags.")
                    await query.message.edit_text(body, reply_markup=back(f"repo:{repository_id}"))
                    return
            if data.count(":") == 1:
                repository_id = int(data.split(":", 1)[1])
                repo = await service.get_by_id(repository_id)
                owner = repo["owner"]["login"]
                name = repo["name"]
                branch = repo.get("default_branch", "main")
                await query.message.edit_text(repo_home(owner, name, branch, repo.get("description")), reply_markup=repository(repository_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))
    return handle_repository
