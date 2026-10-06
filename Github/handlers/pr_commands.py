from html import escape
from pyrogram import filters

from ..buttons import error_message
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

AUTH_REQUIRED = "Connect GitHub first with /connect."
REPLY_REQUIRED = "Reply to a pull request notification."
INVALID_METHOD = "Use merge, squash, or rebase."
MERGE_CONFIRMATION = "Merge preview ready. Reply to the PR notification with /merge confirm to continue."
REVIEW_USAGE = "Use /requestchanges review text."
REQUEST_USAGE = "Use /request @username."
PR_SEARCH_USAGE = "Use /pr keyword."

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
        repo = await service.get_by_id(int(notification["repository_id"]))
        return service, repo, int(notification["number"])

    async def result(message, title, number):
        await message.reply_text(f"<b>{escape(title)}</b>

<code>#{number}</code>")

    @app.on_message(filters.command("pr"))
    async def search_pr(client, message):
        service = await service_for(message.from_user.id)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        raw = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else ""
        if raw.lower().startswith("create "):
            payload = raw[7:].strip()
            parts = [item.strip() for item in payload.split("|")]
            try:
                if len(parts) >= 3:
                    refs = parts[0].split()
                    if len(refs) < 2:
                        await message.reply_text("Use /pr create head base | title | body.")
                        return
                    head, base, title, body = refs[0], refs[1], parts[1], parts[2]
                else:
                    args = payload.split()
                    if len(args) < 3:
                        await message.reply_text("Use /pr create head base | title | body.")
                        return
                    head, base = args[0], args[1]
                    title = " ".join(args[2:])
                    body = ""
                linked = await store.current_repository(message.from_user.id)
                repo = await service.get_by_id(int(linked["repository_id"])) if linked else None
                if not repo:
                    await message.reply_text(REPO_REQUIRED)
                    return
                owner, name = repo["owner"]["login"], repo["name"]
                draft = title.endswith(" --draft")
                if draft:
                    title = title[:-8].rstrip()
                item = await service.create_pull_request(owner, name, title, head, base, body, draft)
                await message.reply_text(f"<b>Pull request created.</b>

<code>#{item.get('number')}</code> {escape(item.get('title', title))}")
            except Exception as exc:
                await message.reply_text(error_message(str(exc)))
            return
        if not raw:
            await message.reply_text(PR_SEARCH_USAGE)
            return
        try:
            data = await service.search_issues(f"is:pr {raw}")
            items = data.get("items", [])
            lines = ["<b>Pull requests</b>"]
            for item in items[:20]:
                repo_name = item.get("repository_url", "").rsplit("/repos/", 1)[-1]
                lines.append(f"
<code>#{item.get('number')}</code> {escape(item.get('title', 'Pull request'))[:100]}
{escape(repo_name)}")
            await message.reply_text("".join(lines) if len(lines) > 1 else "<b>No pull requests found.</b>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

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
            await message.reply_text(REVIEW_USAGE)
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
        method = next((item.lower() for item in message.command[1:] if item.lower() in {"merge", "squash", "rebase"}), "merge")
        confirming = any(item.lower() == "confirm" for item in message.command[1:])
        if method not in {"merge", "squash", "rebase"}:
            await message.reply_text(INVALID_METHOD)
            return
        try:
            item = await service.pull_request(repo["owner"]["login"], repo["name"], number)
            if item.get("merged"):
                await result(message, "Pull request is already merged", number)
                return
            if not confirming:
                mergeable = item.get("mergeable")
                state = item.get("mergeable_state", "unknown")
                await message.reply_text(f"<b>Merge pull request</b>

<code>#{number}</code>
method <code>{method}</code>
mergeable <code>{escape(str(mergeable))}</code> · <code>{escape(state)}</code>

Reply with /merge {method} confirm to continue.")
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
            await result(message, "Pull request converted to draft" if draft else "Pull request marked ready for review", number)
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
            items = await service.pull_request_files(repo["owner"]["login"], repo["name"], number, per_page=100)
            lines = [f"<b>Files · #{number}</b>"]
            for item in items[:80]:
                lines.append(f"
<code>{escape(item.get('status', 'modified'))}</code> {escape(item.get('filename', 'file'))} · +{item.get('additions', 0)} -{item.get('deletions', 0)}")
            await message.reply_text("".join(lines) if len(lines) > 1 else "<b>No changed files.</b>")
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
            diff_text = await service.pull_request_diff(repo["owner"]["login"], repo["name"], number)
            if not diff_text:
                await message.reply_text("<b>No diff available.</b>")
                return
            await message.reply_text(f"<pre>{escape(diff_text[-12000:])}</pre>")
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
                reviews = await service.pull_request_reviews(owner, name, number, per_page=100)
                lines = [f"<b>Reviews · #{number}</b>"]
                for review in reviews[-50:]:
                    reviewer = escape(review.get("user", {}).get("login", "unknown"))
                    state = escape(review.get("state", "PENDING"))
                    body = escape(review.get("body") or "")
                    lines.append(f"
<code>{reviewer}</code> · <code>{state}</code>")
                    if body:
                        lines.append(f"
{body[:300]}")
            elif action == "mergeable":
                lines = [f"<b>Mergeable · #{number}</b>", f"
mergeable <code>{escape(str(item.get('mergeable')))}</code>", f"
state <code>{escape(item.get('mergeable_state', 'unknown'))}</code>"]
            else:
                sha = item.get("head", {}).get("sha")
                status = await service.client.request("GET", f"/repos/{owner}/{name}/commits/{sha}/status")
                checks = await service.client.request("GET", f"/repos/{owner}/{name}/commits/{sha}/check-runs", params={"per_page": 100})
                lines = [f"<b>Checks · #{number}</b>", f"
status <code>{escape(status.get('state', 'unknown'))}</code> · {status.get('total_count', 0)}", f"
check runs {len(checks.get('check_runs', []))}"]
                for check in checks.get("check_runs", [])[:20]:
                    conclusion = check.get("conclusion") or check.get("status") or "unknown"
                    lines.append(f"
<code>{escape(check.get('name', 'check'))}</code> · {escape(conclusion)}")
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
            await message.reply_text(REQUEST_USAGE)
            return
        reviewer = message.command[1].lstrip("@")
        try:
            if reviewer.startswith("team:"):
                await service.request_reviewers(repo["owner"]["login"], repo["name"], number, team_reviewers=[reviewer[5:]])
            else:
                await service.request_reviewers(repo["owner"]["login"], repo["name"], number, reviewers=[reviewer])
            await result(message, "Reviewer requested", number)
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    return search_pr, approve, request_changes, merge, draft_state, files, diff, pr_status, request_reviewer
