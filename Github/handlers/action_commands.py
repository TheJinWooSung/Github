from html import escape
from pyrogram import filters

from ..buttons import error_message
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

AUTH_REQUIRED = "Connect GitHub first with /connect."
REPO_REQUIRED = "Link a repository first with /addrepo owner/repo."
REPLY_REQUIRED = "Reply to an Actions notification."
RUN_USAGE = "Use /run workflow.yml [ref] [key=value]."

def register(app, store: GitHubStore, oauth):
    async def service_for(user_id: int):
        token = await store.token(user_id, oauth)
        return RepositoryService(GitHubClient(token)) if token else None

    async def repo_context(message):
        service = await service_for(message.from_user.id)
        if not service:
            return None, None
        linked = await store.current_repository(message.from_user.id)
        if not linked:
            return service, None
        repo = await service.get_by_id(int(linked["repository_id"]))
        return service, repo

    async def reply_context(message):
        if not message.reply_to_message:
            return None, None, None
        notification = await store.notification(message.from_user.id, message.reply_to_message.id)
        if not notification or notification.get("event") != "workflow_run" or not notification.get("number"):
            return None, None, None
        service = await service_for(message.from_user.id)
        if not service:
            return None, None, None
        repo = await service.get_by_id(int(notification["repository_id"]))
        return service, repo, int(notification["number"])

    @app.on_message(filters.command("actions"))
    async def actions(client, message):
        service, repo = await repo_context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPO_REQUIRED)
            return
        owner, name = repo["owner"]["login"], repo["name"]
        try:
            data = await service.workflow_runs(owner, name, per_page=30)
            runs = data.get("workflow_runs", [])
            lines = [f"<b>Actions · {escape(repo['full_name'])}</b>"]
            for run in runs[:25]:
                state = escape(run.get("conclusion") or run.get("status", "unknown"))
                lines.append(f"\n<code>{run.get('id')}</code> {escape(run.get('name', 'workflow'))} · {state}\n{escape(run.get('head_branch') or '-')}")
            await message.reply_text("".join(lines) if len(lines) > 1 else "<b>No workflow runs found.</b>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("run"))
    async def run(client, message):
        service, repo = await repo_context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPO_REQUIRED)
            return
        if len(message.command) < 2:
            await message.reply_text(RUN_USAGE)
            return
        owner, name = repo["owner"]["login"], repo["name"]
        workflow_name = message.command[1]
        ref = repo.get("default_branch", "main")
        input_start = 2
        if len(message.command) > 2 and "=" not in message.command[2]:
            ref = message.command[2]
            input_start = 3
        inputs = {}
        for item in message.command[input_start:]:
            if "=" in item:
                key, value = item.split("=", 1)
                if key:
                    inputs[key] = value
        try:
            workflows = await service.workflows(owner, name)
            workflow = next((item for item in workflows.get("workflows", []) if item.get("path") == workflow_name or item.get("name") == workflow_name or str(item.get("id")) == workflow_name), None)
            if not workflow:
                await message.reply_text("<b>Workflow not found.</b>")
                return
            await service.run_workflow(owner, name, workflow["id"], ref, inputs)
            await message.reply_text(f"<b>Workflow dispatched.</b>\n\n<code>{escape(workflow.get('path', workflow_name))}</code> · <code>{escape(ref)}</code>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command(["rerun", "cancel", "logs"]))
    async def run_action(client, message):
        service, repo, run_id = await reply_context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPLY_REQUIRED)
            return
        owner, name = repo["owner"]["login"], repo["name"]
        action = message.command[0].lower()
        try:
            if action == "rerun":
                await service.rerun(owner, name, run_id, failed_only=False)
                await message.reply_text(f"<b>Workflow rerun requested.</b>\n\n<code>{run_id}</code>")
                return
            if action == "cancel":
                await service.cancel_run(owner, name, run_id)
                await message.reply_text(f"<b>Workflow cancellation requested.</b>\n\n<code>{run_id}</code>")
                return
            run_data = await service.workflow_run(owner, name, run_id)
            jobs = await service.jobs(owner, name, run_id, per_page=100)
            job_items = jobs.get("jobs", [])
            if not job_items:
                await message.reply_text("<b>No jobs found.</b>")
                return
            selected = next((item for item in job_items if item.get("conclusion") == "failure"), job_items[-1])
            logs = await service.job_logs(owner, name, int(selected["id"]))
            await message.reply_text(f"<b>{escape(run_data.get('name', 'Workflow'))}</b>\n\n<pre>{escape(logs[-10000:])}</pre>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    return actions, run, run_action
