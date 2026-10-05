from pyrogram import filters
from ..buttons import NOT_CONNECTED, INTEGRATION_USAGE, INTEGRATION_ADDED, INTEGRATION_EXISTS, INTEGRATION_REMOVED, INTEGRATION_NOT_FOUND, INTEGRATIONS_EMPTY, INTEGRATION_LIST, INTEGRATION_EVENTS, WEBHOOK_EVENTS, error_message, integrations, integration_events, integration_events_text, integration_deliveries, integration_delivery_text, integration_delivery_actions, DELIVERY_LIST
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

def register(app, store: GitHubStore, oauth, webhook_url: str, webhook_secret: str):
    @app.on_message(filters.command("newintegration"))
    async def new_integration(client, message):
        token = await store.token(message.from_user.id, oauth)
        if not token:
            await message.reply_text(NOT_CONNECTED)
            return
        if len(message.command) < 2 or "/" not in message.command[1]:
            await message.reply_text(INTEGRATION_USAGE)
            return
        owner, name = message.command[1].strip("/").split("/", 1)
        try:
            service = RepositoryService(GitHubClient(token))
            repo = await service.get(owner, name)
            existing = await store.list_integrations(message.from_user.id)
            if any(item["repository_id"] == repo["id"] for item in existing):
                await message.reply_text(INTEGRATION_EXISTS)
                return
            settings = await store.get_settings(message.from_user.id)
            events = settings.get("events") or ["push", "pull_request", "issues", "release", "workflow_run", "star"]
            hook = await service.create_webhook(owner, name, webhook_url, webhook_secret, events)
            repo["webhook_events"] = events
            repo["webhook_active"] = hook.get("active", True)
            await store.add_integration(message.from_user.id, repo, hook.get("id"))
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
        repository_id = int(message.command[1])
        item = await store.integration(message.from_user.id, repository_id)
        removed = False
        if item:
            token = await store.token(message.from_user.id, oauth)
            if token and item.get("hook_id"):
                await RepositoryService(GitHubClient(token)).delete_webhook(item["owner"], item["name"], item["hook_id"])
            removed = await store.delete_integration(message.from_user.id, repository_id)
        await message.reply_text(INTEGRATION_REMOVED if removed else INTEGRATION_NOT_FOUND)

    @app.on_callback_query(filters.regex(r"^integration:\d+:events$"))
    async def integration_events_view(client, query):
        await query.answer()
        repository_id = int(query.data.split(":")[1])
        item = await store.integration(query.from_user.id, repository_id)
        if not item:
            await query.message.edit_text(INTEGRATIONS_EMPTY)
            return
        events = item.get("events") or list(WEBHOOK_EVENTS)
        await query.message.edit_text(integration_events_text(item["full_name"], events, item.get("active", True)), reply_markup=integration_events(repository_id, events, item.get("active", True)))

    @app.on_callback_query(filters.regex(r"^integration:\d+:toggle:[a-z_]+$"))
    async def integration_event_toggle(client, query):
        await query.answer()
        parts = query.data.split(":")
        repository_id, event = int(parts[1]), parts[3]
        item = await store.integration(query.from_user.id, repository_id)
        if not item or not item.get("hook_id"):
            await query.message.edit_text(INTEGRATIONS_EMPTY)
            return
        events = list(item.get("events") or [])
        if event in events:
            events.remove(event)
        else:
            events.append(event)
        try:
            token = await store.token(query.from_user.id, oauth)
            if not token:
                await query.message.edit_text(NOT_CONNECTED)
                return
            service = RepositoryService(GitHubClient(token))
            updated = await service.update_webhook(item["owner"], item["name"], item["hook_id"], events=events, active=item.get("active", True))
            events = updated.get("events", events)
            await store.update_integration(query.from_user.id, repository_id, events=events)
            await query.message.edit_text(integration_events_text(item["full_name"], events, updated.get("active", item.get("active", True))), reply_markup=integration_events(repository_id, events, updated.get("active", item.get("active", True))))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^integration:\d+:active$"))
    async def integration_active_toggle(client, query):
        await query.answer()
        repository_id = int(query.data.split(":")[1])
        item = await store.integration(query.from_user.id, repository_id)
        if not item or not item.get("hook_id"):
            await query.message.edit_text(INTEGRATIONS_EMPTY)
            return
        try:
            token = await store.token(query.from_user.id, oauth)
            if not token:
                await query.message.edit_text(NOT_CONNECTED)
                return
            active = not item.get("active", True)
            updated = await RepositoryService(GitHubClient(token)).update_webhook(item["owner"], item["name"], item["hook_id"], events=item.get("events") or list(WEBHOOK_EVENTS), active=active)
            await store.update_integration(query.from_user.id, repository_id, active=updated.get("active", active), events=updated.get("events", item.get("events") or list(WEBHOOK_EVENTS)))
            events = updated.get("events", item.get("events") or list(WEBHOOK_EVENTS))
            await query.message.edit_text(integration_events_text(item["full_name"], events, updated.get("active", active)), reply_markup=integration_events(repository_id, events, updated.get("active", active)))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^integration:\d+:deliveries$"))
    async def integration_deliveries_view(client, query):
        await query.answer()
        repository_id = int(query.data.split(":")[1])
        item = await store.integration(query.from_user.id, repository_id)
        if not item:
            await query.message.edit_text(INTEGRATIONS_EMPTY)
            return
        deliveries = await store.list_deliveries(query.from_user.id, repository_id)
        await query.message.edit_text(DELIVERY_LIST, reply_markup=integration_deliveries(deliveries, repository_id))

    @app.on_callback_query(filters.regex(r"^integration:\d+:deliveries:refresh$"))
    async def integration_deliveries_refresh(client, query):
        await query.answer()
        repository_id = int(query.data.split(":")[1])
        integration = await store.integration(query.from_user.id, repository_id)
        if not integration or not integration.get("hook_id"):
            await query.message.edit_text(INTEGRATIONS_EMPTY)
            return
        try:
            token = await store.token(query.from_user.id, oauth)
            if not token:
                await query.message.edit_text(NOT_CONNECTED)
                return
            service = RepositoryService(GitHubClient(token))
            deliveries = await service.webhook_deliveries(integration["owner"], integration["name"], integration["hook_id"], per_page=25)
            for delivery in deliveries:
                await store.sync_webhook_delivery(query.from_user.id, repository_id, delivery)
            local = await store.list_deliveries(query.from_user.id, repository_id)
            await query.message.edit_text(DELIVERY_LIST, reply_markup=integration_deliveries(local, repository_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^delivery:\d+:[^:]+$"))
    async def delivery_view(client, query):
        await query.answer()
        parts = query.data.split(":")
        repository_id, delivery_id = int(parts[1]), parts[2]
        item = await store.delivery(query.from_user.id, delivery_id)
        if not item or int(item.get("repository_id", 0)) != repository_id:
            await query.message.edit_text(INTEGRATIONS_EMPTY)
            return
        await query.message.edit_text(integration_delivery_text(item), reply_markup=integration_delivery_actions(repository_id, delivery_id, item.get("status") == "failed"))

    @app.on_callback_query(filters.regex(r"^delivery:\d+:[^:]+:retry$"))
    async def delivery_retry(client, query):
        await query.answer()
        parts = query.data.split(":")
        repository_id, delivery_id = int(parts[1]), parts[2]
        item = await store.delivery(query.from_user.id, delivery_id)
        integration = await store.integration(query.from_user.id, repository_id)
        if not item or not integration or not integration.get("hook_id"):
            await query.message.edit_text(INTEGRATIONS_EMPTY)
            return
        try:
            token = await store.token(query.from_user.id, oauth)
            if not token:
                await query.message.edit_text(NOT_CONNECTED)
                return
            await RepositoryService(GitHubClient(token)).redeliver_webhook(integration["owner"], integration["name"], integration["hook_id"], delivery_id)
            await store.update_delivery_status(query.from_user.id, delivery_id, "retrying")
            item["status"] = "retrying"
            await query.message.edit_text(integration_delivery_text(item), reply_markup=integration_delivery_actions(repository_id, delivery_id, False))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^integrations:list$"))
    async def integration_list_callback(client, query):
        await query.answer()
        items = await store.list_integrations(query.from_user.id)
        await query.message.edit_text(INTEGRATIONS_EMPTY if not items else INTEGRATION_LIST, reply_markup=integrations(items) if items else None)

    @app.on_callback_query(filters.regex(r"^integration:\d+:delete$"))
    async def delete_callback(client, query):
        await query.answer()
        repository_id = int(query.data.split(":")[1])
        item = await store.integration(query.from_user.id, repository_id)
        removed = False
        if item:
            token = await store.token(query.from_user.id, oauth)
            if token and item.get("hook_id"):
                await RepositoryService(GitHubClient(token)).delete_webhook(item["owner"], item["name"], item["hook_id"])
            removed = await store.delete_integration(query.from_user.id, repository_id)
        items = await store.list_integrations(query.from_user.id)
        await query.message.edit_text(INTEGRATIONS_EMPTY if not items else INTEGRATION_LIST, reply_markup=integrations(items) if items else None)

    return new_integration, list_integrations, delete_integration, delete_callback
