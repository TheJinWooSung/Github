from pyrogram import filters
from ..buttons import NOT_CONNECTED, INTEGRATION_USAGE, INTEGRATION_ADDED, INTEGRATION_EXISTS, INTEGRATION_REMOVED, INTEGRATION_NOT_FOUND, INTEGRATIONS_EMPTY, INTEGRATION_LIST, error_message, integrations
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

def register(app, store: GitHubStore, oauth):
    @app.on_message(filters.command("newintegration"))
    async def new_integration(client, message):
        token = await store.token(message.from_user.id, oauth)
        if not token:
            await message.reply_text(NOT_CONNECTED)
            return
        if len(message.command) < 2 or "/" not in message.command[1]:
            await message.reply_text(INTEGRATION_USAGE)
            return
        full_name = message.command[1].strip("/")
        owner, name = full_name.split("/", 1)
        try:
            repo = await RepositoryService(GitHubClient(token)).get(owner, name)
            existing = await store.list_integrations(message.from_user.id)
            if any(item["repository_id"] == repo["id"] for item in existing):
                await message.reply_text(INTEGRATION_EXISTS)
                return
            await store.add_integration(message.from_user.id, repo)
            await message.reply_text(INTEGRATION_ADDED)
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("listintegrations"))
    async def list_integrations(client, message):
        items = await store.list_integrations(message.from_user.id)
        if not items:
            await message.reply_text(INTEGRATIONS_EMPTY)
            return
        lines = [f"<b>{INTEGRATION_LIST}</b>"]
        for item in items:
            lines.append(f"\n<code>{item['full_name']}</code>")
        await message.reply_text("\n".join(lines), reply_markup=integrations(items))

    @app.on_message(filters.command("delintegration"))
    async def delete_integration(client, message):
        if len(message.command) < 2 or not message.command[1].isdigit():
            items = await store.list_integrations(message.from_user.id)
            await message.reply_text(INTEGRATIONS_EMPTY if not items else INTEGRATION_LIST, reply_markup=integrations(items))
            return
        removed = await store.delete_integration(message.from_user.id, int(message.command[1]))
        await message.reply_text(INTEGRATION_REMOVED if removed else INTEGRATION_NOT_FOUND)

    @app.on_callback_query(filters.regex(r"^integration:\d+:delete$"))
    async def delete_callback(client, query):
        await query.answer()
        repository_id = int(query.data.split(":")[1])
        removed = await store.delete_integration(query.from_user.id, repository_id)
        items = await store.list_integrations(query.from_user.id)
        await query.message.edit_text(INTEGRATIONS_EMPTY if not items else INTEGRATION_LIST, reply_markup=integrations(items) if items else None)
        if not removed:
            return

    return new_integration, list_integrations, delete_integration, delete_callback
