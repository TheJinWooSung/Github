from html import escape
from pyrogram import filters

from ..buttons import error_message
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

AUTH_REQUIRED = "Connect GitHub first with /connect."
REPLY_REQUIRED = "Reply to a pull request notification."
INVALID_METHOD = "Use merge, squash, or rebase."

def register(app, store: GitHubStore, oauth):
    async def service_for(user_id: int):
        token = await store.token(user_id, oauth)
        return RepositoryService(GitHubClient(token)) if token else None

    async def context(message):
        if not message.reply_to_message:
            return None, None, None
        notification = await store.notification(message.from_user.id, message.reply_to_message.id)
        if not notification or not notification.get("number"):
            return None, None, None
        service = await service_for(message.from_user.id)
        if not service:
            return None, None, None
        repo = await service.get_by_id(notification["repository_id"])
        return service, repo, int(notification["number"])

    async def result(message, title, number):
        await message.reply_text(f"<b>{escape(title)}</b>\n\n<code>#{number}</code>")

    @app.on_message(filters.command("approve"))
    async def approve(client, message):
        service, repo, number = await context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPLY_REQUIRED)
            return
        try:
            await service.submit_review(repo["owner"]["login"], repo["name"], number, "APPROVE")
            await result(message, "Pull request approved", number)
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("requestchanges"))
    async def request_changes(client, message):
        service, repo, number = await context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPLY_REQUIRED)
            return
        body = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else ""
        if not body:
            await message.reply_text("Use /requestchanges review text.")
            return
        try:
            await service.submit_review(repo["owner"]["login"], repo["name"], number, "REQUEST_CHANGES", body)
            await result(message, "Changes requested", number)
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("merge"))
    async def merge(client, message):
        service, repo, number = await context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPLY_REQUIRED)
            return
        method = message.command[1].lower() if len(message.command) > 1 else "merge"
        if method not in {"merge", "squash", "rebase"}:
            await message.reply_text(INVALID_METHOD)
            return
        try:
            item = await service.pull_request(repo["owner"]["login"], repo["name"], number)
            if item.get("merged"):
                await result(message, "Pull request is already merged", number)
                return
            head_sha = item.get("head", {}).get("sha")
            merged = await service.merge_pull_request(repo["owner"]["login"], repo["name"], number, method, head_sha)
            title = "Pull request merged" if merged.get("merged") else merged.get("message", "Pull request was not merged")
            await result(message, title, number)
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command(["draft", "ready"]))
    async def draft_state(client, message):
        service, repo, number = await context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPLY_REQUIRED)
            return
        try:
            draft = message.command[0].lower() == "draft"
            await service.update_pull_request(repo["owner"]["login"], repo["name"], number, draft=draft)
            await result(message, "Pull request updated", number)
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("files"))
    async def files(client, message):
        service, repo, number = await context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPLY_REQUIRED)
            return
        try:
            items = await service.pull_request_files(repo["owner"]["login"], repo["name"], number)
            lines = [f"<b>Files · #{number}</b>"]
            for item in items[:40]:
                lines.append(f"\n<code>{escape(item.get('status', 'modified'))}</code> {escape(item.get('filename', 'file'))} · +{item.get('additions', 0)} -{item.get('deletions', 0)}")
            await message.reply_text("".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("diff"))
    async def diff(client, message):
        service, repo, number = await context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPLY_REQUIRED)
            return
        try:
            text = await service.pull_request_diff(repo["owner"]["login"], repo["name"], number)
            text = text[-7000:]
            await message.reply_text(f"<pre>{escape(text)}</pre>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command(["reviews", "mergeable", "checks"]))
    async def pr_status(client, message):
        service, repo, number = await context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPLY_REQUIRED)
            return
        try:
            owner, name = repo["owner"]["login"], repo["name"]
            item = await service.pull_request(owner, name, number)
            action = message.command[0].lower()
            if action == "reviews":
                reviews = await service.pull_request_reviews(owner, name, number)
                lines = [f"<b>Reviews · #{number}</b>"]
                lines.extend(f"\n<code>{escape(item.get('user', {}).get('login', 'reviewer'))}</code> · {escape(review.get('state', 'PENDING'))}" for review in reviews for item in [review])
            elif action == "mergeable":
                lines = [f"<b>Mergeable · #{number}</b>", f"\nstate: <code>{escape(str(item.get('mergeable')))}</code>", f"\nstatus: <code>{escape(item.get('mergeable_state', 'unknown'))}</code>"]
            else:
                status = await service.client.request("GET", f"/repos/{owner}/{name}/commits/{item.get('head', {}).get('sha')}/status")
                lines = [f"<b>Checks · #{number}</b>", f"\n<code>{escape(status.get('state', 'unknown'))}</code> · {status.get('total_count', 0)}"]
            await message.reply_text("".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("request"))
    async def request_reviewer(client, message):
        service, repo, number = await context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPLY_REQUIRED)
            return
        if len(message.command) < 2:
            await message.reply_text("Use /request @username.")
            return
        try:
            await service.request_reviewers(repo["owner"]["login"], repo["name"], number, reviewers=[message.command[1].lstrip("@")])
            await result(message, "Reviewer requested", number)
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    return approve, request_changes, merge, draft_state, files, diff, pr_status, request_reviewer
