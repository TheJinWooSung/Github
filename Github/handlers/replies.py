from pyrogram import filters
from ..buttons import NOT_CONNECTED, error_message
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

def register(app, store: GitHubStore, oauth):
    @app.on_message(filters.reply & filters.text)
    async def reply_to_github(client, message):
        if not message.reply_to_message or not message.from_user:
            return
        target = await store.notification(message.from_user.id, message.reply_to_message.id)
        if not target or target.get("event") not in {"issues", "pull_request"} or not target.get("number"):
            return
        token = await store.token(message.from_user.id, oauth)
        if not token:
            await message.reply_text(NOT_CONNECTED)
            return
        integration = await store.integrations.find_one({"telegram_id": message.from_user.id, "repository_id": target["repository_id"]})
        if not integration:
            return
        try:
            service = RepositoryService(GitHubClient(token))
            result = await service.issue_comment(integration["owner"], integration["name"], target["number"], message.text)
            await message.reply_text(f"<b>Comment posted</b>\n\n<code>{result.get('id')}</code>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))
    return reply_to_github
