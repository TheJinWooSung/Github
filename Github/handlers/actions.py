from html import escape
from pyrogram import filters
from ..buttons import (
    ACTION_ARTIFACTS,
    ACTION_CANCELLED,
    ACTION_DISPATCHED,
    ACTION_ERROR,
    ACTION_CONNECT_REQUIRED,
    ACTION_NOT_FOUND,
    ACTION_RUN_REQUEST,
    ACTION_RERUNNED,
    ACTION_RUNS,
    ACTION_WORKFLOWS,
    ACTION_LOGS,
    ACTION_STEPS,
    ACTION_NO_STEPS,
    ACTION_JOBS_EMPTY,
    ACTION_ARTIFACTS_EMPTY,
    ACTION_RUNS_EMPTY,
    ACTIONS_EMPTY,
    action_artifacts,
    action_job_view,
    action_jobs,
    action_run_view,
    action_runs,
    workflow_actions,
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
            await query.message.edit_text(error_message(ACTION_CONNECT_REQUIRED))
            return
        try:
            repo, _, _ = await repository(service, repository_id)
            await query.message.edit_text(actions_text(repo["full_name"]), reply_markup=actions_home(repository_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^actions:\d+:(workflows|runs|artifacts)$"))
    async def action_lists(client, query):
        await query.answer()
        _, repository_id, section = query.data.split(":")
        repository_id = int(repository_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message(ACTION_CONNECT_REQUIRED))
            return
        try:
            repo, owner, name = await repository(service, repository_id)
            if section == "workflows":
                items = (await service.workflows(owner, name)).get("workflows", [])
                text = f"<b>{escape(repo['full_name'])}</b>\n\n<b>{ACTION_WORKFLOWS}</b>"
                await query.message.edit_text(text, reply_markup=action_workflows(items, repository_id))
            elif section == "runs":
                items = (await service.workflow_runs(owner, name)).get("workflow_runs", [])
                text = f"<b>{escape(repo['full_name'])}</b>\n\n<b>{ACTION_RUNS}</b>"
                await query.message.edit_text(text, reply_markup=action_runs(items, repository_id))
            else:
                items = (await service.artifacts(owner, name)).get("artifacts", [])
                text = f"<b>{escape(repo['full_name'])}</b>\n\n<b>{ACTION_ARTIFACTS}</b>"
                await query.message.edit_text(text, reply_markup=action_artifacts(items, repository_id))
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
            runs = (await service.workflow_runs_for(owner, name, workflow_id)).get("workflow_runs", [])
            text = workflow_text(item) + f"\n\n<b>{ACTION_RUNS}</b>  {len(runs)}"
            await query.message.edit_text(text, reply_markup=workflow_actions(repository_id, workflow_id, runs))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^run:\d+:\d+$"))
    async def run_view(client, query):
        await query.answer()
        _, repository_id, run_id = query.data.split(":")
        repository_id, run_id = int(repository_id), int(run_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message("Connect GitHub first with /connect."))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            item = await service.workflow_run(owner, name, run_id)
            await query.message.edit_text(run_text(item), reply_markup=action_run_view(repository_id, run_id, item.get("status", ""), item.get("conclusion")))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^workflow:\d+:\d+:run$"))
    async def workflow_dispatch(client, query):
        await query.answer()
        _, repository_id, workflow_id, _ = query.data.split(":")
        repository_id, workflow_id = int(repository_id), int(workflow_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message(ACTION_CONNECT_REQUIRED))
            return
        try:
            repo, owner, name = await repository(service, repository_id)
            workflow = await service.workflow(owner, name, workflow_id)
            ref = repo.get("default_branch") or "main"
            await service.run_workflow(owner, name, workflow_id, ref)
            await query.message.edit_text(
                f"<b>{ACTION_RUN_REQUEST}</b>\n\n<code>{escape(workflow.get('name', 'workflow'))}</code> · <code>{escape(ref)}</code>",
                reply_markup=workflow_actions(repository_id, workflow_id, []),
            )
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^run:\d+:\d+:refresh$"))
    async def run_refresh(client, query):
        await query.answer()
        _, repository_id, run_id, _ = query.data.split(":")
        repository_id, run_id = int(repository_id), int(run_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message(ACTION_CONNECT_REQUIRED))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            item = await service.workflow_run(owner, name, run_id)
            await query.message.edit_text(
                run_text(item),
                reply_markup=action_run_view(
                    repository_id,
                    run_id,
                    item.get("status", ""),
                    item.get("conclusion"),
                ),
            )
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^run:\d+:\d+:(jobs|artifacts)$"))
    async def run_data(client, query):
        await query.answer()
        _, repository_id, run_id, section = query.data.split(":")
        repository_id, run_id = int(repository_id), int(run_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message("Connect GitHub first with /connect."))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            if section == "jobs":
                items = (await service.jobs(owner, name, run_id)).get("jobs", [])
                await query.message.edit_text(
                    f"<b>{ACTION_RUNS}</b> · <code>{run_id}</code>\n\n{ACTION_JOBS_EMPTY if not items else ''}".rstrip(),
                    reply_markup=action_jobs(items, repository_id, run_id),
                )
            else:
                items = (await service.run_artifacts(owner, name, run_id)).get("artifacts", [])
                await query.message.edit_text(
                    f"<b>{ACTION_ARTIFACTS}</b> · <code>{run_id}</code>\n\n{ACTION_ARTIFACTS_EMPTY if not items else ''}".rstrip(),
                    reply_markup=action_artifacts(items, repository_id, run_id),
                )
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^run:\d+:\d+:(rerun|rerun_failed|cancel)$"))
    async def run_action(client, query):
        await query.answer()
        _, repository_id, run_id, action = query.data.split(":")
        repository_id, run_id = int(repository_id), int(run_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message("Connect GitHub first with /connect."))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            if action == "cancel":
                await service.cancel_run(owner, name, run_id)
                message = ACTION_CANCELLED
            else:
                await service.rerun(owner, name, run_id, failed_only=action == "rerun_failed")
                message = ACTION_RERUNNED
            await query.message.edit_text(f"<b>{message}</b>\n\n<code>{run_id}</code>", reply_markup=action_run_view(repository_id, run_id, "queued", None))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^job:\d+:\d+:\d+$"))
    async def job_view(client, query):
        await query.answer()
        _, repository_id, run_id, job_id = query.data.split(":")
        repository_id, run_id, job_id = int(repository_id), int(run_id), int(job_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message("Connect GitHub first with /connect."))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            jobs = (await service.jobs(owner, name, run_id)).get("jobs", [])
            item = next((job for job in jobs if job.get("id") == job_id), None)
            if not item:
                raise RuntimeError(ACTION_NOT_FOUND)
            await query.message.edit_text(job_text(item), reply_markup=action_job_view(repository_id, run_id, job_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^job:\d+:\d+:\d+:steps$"))
    async def job_steps(client, query):
        await query.answer()
        _, repository_id, run_id, job_id, _ = query.data.split(":")
        repository_id, run_id, job_id = int(repository_id), int(run_id), int(job_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message(ACTION_CONNECT_REQUIRED))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            jobs = (await service.jobs(owner, name, run_id)).get("jobs", [])
            item = next((job for job in jobs if job.get("id") == job_id), None)
            if not item:
                raise RuntimeError(ACTION_NOT_FOUND)
            steps = item.get("steps") or []
            lines = [f"<b>{escape(item.get('name', ACTION_STEPS))}</b>", ""]
            if not steps:
                lines.append(ACTION_NO_STEPS)
            else:
                for step in steps:
                    status = step.get("conclusion") or step.get("status") or "unknown"
                    number = step.get("number", "")
                    name_text = escape(step.get("name", "step"))
                    lines.append(f"<code>{number}</code> {name_text} · <code>{escape(status)}</code>")
            await query.message.edit_text("\n".join(lines)[:3900], reply_markup=action_job_view(repository_id, run_id, job_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^job:\d+:\d+:\d+:logs$"))
    async def job_logs(client, query):
        await query.answer()
        _, repository_id, run_id, job_id, _ = query.data.split(":")
        repository_id, run_id, job_id = int(repository_id), int(run_id), int(job_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message("Connect GitHub first with /connect."))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            jobs = (await service.jobs(owner, name, run_id)).get("jobs", [])
            item = next((job for job in jobs if job.get("id") == job_id), None)
            if not item:
                raise RuntimeError("Job not found")
            logs = await service.job_logs(owner, name, job_id)
            await query.message.edit_text(action_logs_text(item.get("name", ACTION_LOGS), logs), reply_markup=action_job_view(repository_id, run_id, job_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^artifact:\d+:\d+:\d+$"))
    async def run_artifact_view(client, query):
        await query.answer()
        _, repository_id, run_id, artifact_id = query.data.split(":")
        repository_id, run_id, artifact_id = int(repository_id), int(run_id), int(artifact_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message(ACTION_CONNECT_REQUIRED))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            data = (await service.run_artifacts(owner, name, run_id)).get("artifacts", [])
            item = next((artifact for artifact in data if artifact.get("id") == artifact_id), None)
            if not item:
                raise RuntimeError(ACTION_NOT_FOUND)
            await query.message.edit_text(artifact_text(item), reply_markup=action_artifacts(data, repository_id, run_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^artifact:\d+:\d+$"))
    async def artifact_view(client, query):
        await query.answer()
        _, repository_id, artifact_id = query.data.split(":")
        repository_id, artifact_id = int(repository_id), int(artifact_id)
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(error_message("Connect GitHub first with /connect."))
            return
        try:
            _, owner, name = await repository(service, repository_id)
            data = (await service.artifacts(owner, name)).get("artifacts", [])
            item = next((artifact for artifact in data if artifact.get("id") == artifact_id), None)
            if not item:
                raise RuntimeError(ACTION_NOT_FOUND)
            await query.message.edit_text(artifact_text(item), reply_markup=actions_home(repository_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))
