from pyrogram import filters
from ..buttons import (
    ACTION_ARTIFACTS,
    ACTION_CANCELLED,
    ACTION_DISPATCHED,
    ACTION_ERROR,
    ACTION_RERUNNED,
    ACTION_RUNS,
    ACTION_WORKFLOWS,
    ACTIONS_EMPTY,
    ACTIONS_TITLE,
    ACTION_LOGS,
    ACTION_JOBS_EMPTY,
    ACTION_RUNS_EMPTY,
    action_artifacts,
    action_job_view,
    action_jobs,
    action_run_view,
    action_runs,
    action_workflows,
    actions_home,
    actions_text,
    action_logs_text,
    artifact_text,
    error_message,
    job_text,
    run_text,
    workflow_text,
)
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

def register(app, store: GitHubStore, oauth):
    async def service_for(user_id: int):
        token = await store.token(user_id, oauth)
        if not token:
            return None
        return RepositoryService(GitHubClient(token))

    async def repository(service, repository_id: int):
        repo = await service.get_by_id(repository_id)
        return repo, repo["owner"]["login"], repo["name"]

    @app.on_callback_query(filters.regex(r"^repo:\d+:actions$"))
    async def actions(client, query):
        await query.answer()
        repository_id = int(query.data.split(":")[1])
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message("Connect GitHub first with /connect."))
            return
        try:
            repo, _, _ = await repository(service, repository_id)
            await query.message.edit_text(actions_text(repo["full_name"]), reply_markup=actions_home(repository_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^actions:\d+:(workflows|runs|artifacts)$"))
    async def action_lists(client, query):
        await query.answer()
        parts = query.data.split(":")
        repository_id = int(parts[1])
        section = parts[2]
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message("Connect GitHub first with /connect."))
            return
        try:
            repo, owner, name = await repository(service, repository_id)
            if section == "workflows":
                data = await service.workflows(owner, name)
                items = data.get("workflows", [])
                await query.message.edit_text(
                    f"<b>{repo['full_name']}</b>\n\n<b>{ACTION_WORKFLOWS}</b>",
                    reply_markup=action_workflows(items, repository_id),
                )
            elif section == "runs":
                data = await service.workflow_runs(owner, name)
                items = data.get("workflow_runs", [])
                await query.message.edit_text(
                    f"<b>{repo['full_name']}</b>\n\n<b>{ACTION_RUNS}</b>",
                    reply_markup=action_runs(items, repository_id),
                )
            else:
                data = await service.artifacts(owner, name)
                items = data.get("artifacts", [])
                await query.message.edit_text(
                    f"<b>{repo['full_name']}</b>\n\n<b>{ACTION_ARTIFACTS}</b>",
                    reply_markup=action_artifacts(items, repository_id),
                )
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^workflow:\d+:\d+$"))
    async def workflow_view(client, query):
        await query.answer()
        _, repository_id, workflow_id = query.data.split(":")
        repository_id, workflow_id = int(repository_id), int(workflow_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message("Connect GitHub first with /connect."))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            item = await service.workflow(owner, name, workflow_id)
            await query.message.edit_text(
                workflow_text(item),
                reply_markup=action_runs(await service.workflow_runs_for(owner, name, workflow_id).then if False else [], repository_id),
            )
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))
