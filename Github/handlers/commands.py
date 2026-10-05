from html import escape
from pyrogram import filters

from ..buttons import error_message, repositories as repository_buttons
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

AUTH_REQUIRED = "Connect GitHub first with /connect."
REPO_REQUIRED = "Link a repository first with /addrepo owner/repo."
REPLY_REQUIRED = "Reply to a GitHub issue or pull request notification."
USAGE_REPO = "Use /addrepo owner/repo."
USAGE_ISSUE = "Use /issue title | body."
USAGE_COMPARE = "Use /compare branch1 branch2."
USAGE_LABEL = "Use /label +bug -old-label."
HELP_TEXT = """<b>GitHub for Telegram</b>

<b>Account</b>
/connect · /disconnect · /me

<b>Repositories</b>
/addrepo owner/repo · /removerepo owner/repo · /repos
/repo [owner/repo] · /star · /unstar · /watch · /unwatch
/fork · /archive · /unarchive · /contributors · /languages
/branches · /branch name · /default branch-name

<b>Issues</b>
/issue title | body · /comment text · /close · /reopen
/assign @user · /assignme · /unassign @user
/label +bug -old · /labels · /milestone v1.0
/lock · /unlock · /pin · /unpin

<b>Commits</b>
/commit SHA · /commits · /compare branch1 branch2

<b>Pull requests</b>
/pr keyword · /approve · /requestchanges text · /merge [merge|squash|rebase]
/draft · /ready · /checks · /files · /diff · /reviews · /mergeable · /request @user

<b>Actions</b>
/actions · /run workflow.yml [ref] [key=value]
/rerun · /cancel · /logs

<b>Releases</b>
/release · /release create v1.0.0 · /changelog

<b>Search</b>
/find keyword · /search keyword

<b>Repository</b>
/stats · /activity · /settings · /reload

<b>Notifications</b>
/mute · /done · /read

/help · /privacy
"""

def register(app, store: GitHubStore, oauth):
    async def service_for(user_id: int):
        token = await store.token(user_id, oauth)
        return RepositoryService(GitHubClient(token)) if token else None

    async def current(user_id: int, message=None, explicit: str | None = None):
        service = await service_for(user_id)
        if not service:
            return None, None
        target = explicit
        if not target and message and len(message.command) > 1:
            target = message.command[1].strip()
        if target and "/" in target:
            owner, name = target.strip("/").split("/", 1)
            repo = await service.get(owner, name)
            return service, repo
        linked = await store.current_repository(user_id)
        if not linked:
            return service, None
        repo = await service.get_by_id(linked["repository_id"])
        await store.add_repository(user_id, repo)
        return service, repo

    async def context_from_reply(message):
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

    async def require_repo(message):
        service, repo = await current(message.from_user.id, message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return None, None
        if not repo:
            await message.reply_text(REPO_REQUIRED)
            return None, None
        await store.set_current_repository(message.from_user.id, int(repo["id"]))
        return service, repo

    def repo_parts(repo):
        return repo["owner"]["login"], repo["name"]

    @app.on_message(filters.command("me"))
    async def me(client, message):
        service = await service_for(message.from_user.id)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        try:
            user = await service.get_user()
            lines = [
                f"<b>{escape(user.get('login', 'unknown'))}</b>",
                f"<code>ID {user.get('id', '')}</code>",
            ]
            if user.get("name"):
                lines.append(escape(user["name"]))
            if user.get("email"):
                lines.append(escape(user["email"]))
            if user.get("html_url"):
                lines.append(escape(user["html_url"]))
            await message.reply_text("\n".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("disconnect"))
    async def disconnect(client, message):
        user = await store.get_user(message.from_user.id)
        if not user or not user.get("access_token"):
            await message.reply_text(AUTH_REQUIRED)
            return
        try:
            token = await store.token(message.from_user.id, oauth)
            if token:
                await oauth.revoke(token)
        except Exception:
            pass
        await store.disconnect_user(message.from_user.id)
        await message.reply_text("<b>GitHub disconnected.</b>")

    @app.on_message(filters.command("addrepo"))
    async def addrepo(client, message):
        if len(message.command) < 2 or "/" not in message.command[1]:
            await message.reply_text(USAGE_REPO)
            return
        service = await service_for(message.from_user.id)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        try:
            owner, name = message.command[1].strip("/").split("/", 1)
            repo = await service.get(owner, name)
            await store.add_repository(message.from_user.id, repo)
            await store.set_current_repository(message.from_user.id, int(repo["id"]))
            await message.reply_text(f"<b>Repository linked</b>\n\n<code>{escape(repo['full_name'])}</code>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("removerepo"))
    async def removerepo(client, message):
        if len(message.command) < 2:
            await message.reply_text(USAGE_REPO.replace("addrepo", "removerepo"))
            return
        item = await store.repository_by_name(message.from_user.id, message.command[1].strip("/"))
        if not item:
            await message.reply_text("<b>Repository is not linked.</b>")
            return
        removed = await store.remove_repository(message.from_user.id, int(item["repository_id"]))
        await message.reply_text("<b>Repository removed.</b>" if removed else "<b>Repository is not linked.</b>")

    @app.on_message(filters.command("repos"))
    async def repos(client, message):
        service = await service_for(message.from_user.id)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        items = await store.list_repositories(message.from_user.id)
        if not items:
            await message.reply_text("<b>No linked repositories.</b>\n\nUse /addrepo owner/repo.")
            return
        lines = ["<b>Linked repositories</b>"]
        for item in items:
            marker = " · current" if (await store.current_repository(message.from_user.id) or {}).get("repository_id") == item["repository_id"] else ""
            lines.append(f"\n<code>{escape(item['full_name'])}</code>{marker}")
        await message.reply_text("".join(lines), reply_markup=repository_buttons(items))

    @app.on_message(filters.command("repo"))
    async def repo(client, message):
        service, item = await current(message.from_user.id, message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not item:
            await message.reply_text(REPO_REQUIRED)
            return
        try:
            owner, name = repo_parts(item)
            data = await service.get(owner, name)
            await store.add_repository(message.from_user.id, data)
            await store.set_current_repository(message.from_user.id, int(data["id"]))
            lines = [
                f"<b>{escape(data['full_name'])}</b>",
                escape(data.get("description") or "No description"),
                "",
                f"<code>{escape(data.get('default_branch', 'main'))}</code> · {escape(data.get('visibility', 'public'))}",
                f"stars {data.get('stargazers_count', 0)} · forks {data.get('forks_count', 0)} · issues {data.get('open_issues_count', 0)}",
                f"watchers {data.get('subscribers_count', 0)} · size {data.get('size', 0)} KB",
            ]
            await message.reply_text("\n".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command(["star", "unstar", "watch", "unwatch", "archive", "unarchive"]))
    async def repo_state(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        action = message.command[0].lower()
        owner, name = repo_parts(repo)
        try:
            if action == "star":
                await service.star(owner, name)
                text = "Repository starred."
            elif action == "unstar":
                await service.unstar(owner, name)
                text = "Repository unstarred."
            elif action == "watch":
                await service.watch(owner, name, True)
                text = "Repository watched."
            elif action == "unwatch":
                await service.watch(owner, name, False)
                text = "Repository unwatched."
            elif action == "archive":
                await service.update_repository(owner, name, archived=True)
                text = "Repository archived."
            else:
                await service.update_repository(owner, name, archived=False)
                text = "Repository unarchived."
            await message.reply_text(f"<b>{text}</b>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("fork"))
    async def fork(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        owner, name = repo_parts(repo)
        try:
            target = message.command[1] if len(message.command) > 1 else ""
            data = await service.fork(owner, name, organization=target if target and "/" not in target else None, repository=target if target and "/" not in target else None)
            await message.reply_text(f"<b>Fork created</b>\n\n<code>{escape(data.get('full_name', 'fork'))}</code>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command(["contributors", "languages", "branches"]))
    async def repository_data(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        owner, name = repo_parts(repo)
        action = message.command[0].lower()
        try:
            if action == "contributors":
                items = await service.contributors(owner, name)
                lines = [f"<b>{escape(repo['full_name'])}</b>"]
                lines.extend(f"\n{index}. <code>{escape(item.get('login') or 'unknown')}</code> · {item.get('contributions', 0)}" for index, item in enumerate(items[:20], 1))
            elif action == "languages":
                data = await service.languages(owner, name)
                total = sum(data.values()) or 1
                lines = [f"<b>{escape(repo['full_name'])}</b>"]
                lines.extend(f"\n<code>{escape(key)}</code> · {value / total * 100:.1f}%" for key, value in sorted(data.items(), key=lambda pair: pair[1], reverse=True))
            else:
                items = await service.branches(owner, name)
                lines = [f"<b>{escape(repo['full_name'])}</b>"]
                lines.extend(f"\n<code>{escape(item.get('name', 'branch'))}</code>" for item in items[:40])
            await message.reply_text("".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("branch"))
    async def branch(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        owner, name = repo_parts(repo)
        args = message.command[1:]
        try:
            if not args:
                items = await service.branches(owner, name)
                lines = [f"<b>{escape(repo['full_name'])}</b>"]
                lines.extend(f"\n<code>{escape(item.get('name', 'branch'))}</code>" for item in items[:40])
                await message.reply_text("".join(lines))
                return
            action = args[0].lower()
            if action == "create":
                if len(args) < 2:
                    await message.reply_text("Use /branch create name [from].")
                    return
                branch_name = args[1]
                source = args[2] if len(args) > 2 else repo.get("default_branch", "main")
                source_ref = await service.ref(owner, name, f"heads/{source}")
                await service.create_branch(owner, name, branch_name, source_ref["object"]["sha"])
                await message.reply_text(f"<b>Branch created.</b>\n\n<code>{escape(branch_name)}</code> ← <code>{escape(source)}</code>")
                return
            if action == "delete":
                if len(args) < 2:
                    await message.reply_text("Use /branch delete name.")
                    return
                branch_name = args[1]
                if branch_name == repo.get("default_branch"):
                    await message.reply_text("<b>The default branch cannot be deleted here.</b>")
                    return
                await service.delete_branch(owner, name, branch_name)
                await message.reply_text(f"<b>Branch deleted.</b>\n\n<code>{escape(branch_name)}</code>")
                return
            if action == "rename":
                if len(args) < 3:
                    await message.reply_text("Use /branch rename old new.")
                    return
                old, new = args[1], args[2]
                source_ref = await service.ref(owner, name, f"heads/{old}")
                await service.create_branch(owner, name, new, source_ref["object"]["sha"])
                try:
                    await service.delete_branch(owner, name, old)
                except Exception:
                    try:
                        await service.delete_branch(owner, name, new)
                    except Exception:
                        pass
                    raise
                await message.reply_text(f"<b>Branch renamed.</b>\n\n<code>{escape(old)}</code> → <code>{escape(new)}</code>")
                return
            item = await service.branch(owner, name, args[0])
            commit = item.get("commit", {})
            await message.reply_text(f"<b>{escape(item.get('name', 'branch'))}</b>\n\n<code>{escape(commit.get('sha', '')[:12])}</code>\n{escape(commit.get('commit', {}).get('message', ''))}")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("default"))
    async def default_branch(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        if len(message.command) < 2:
            await message.reply_text("Use /default branch-name.")
            return
        owner, name = repo_parts(repo)
        try:
            data = await service.update_repository(owner, name, default_branch=message.command[1])
            await store.add_repository(message.from_user.id, data)
            await message.reply_text(f"<b>Default branch updated.</b>\n\n<code>{escape(data.get('default_branch', message.command[1]))}</code>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("issue"))
    async def issue(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        raw = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else ""
        title, _, body = raw.partition("|")
        if not title.strip():
            await message.reply_text(USAGE_ISSUE)
            return
        owner, name = repo_parts(repo)
        try:
            item = await service.create_issue(owner, name, title.strip(), body.strip())
            await message.reply_text(f"<b>Issue created</b>\n\n<code>#{item.get('number')}</code> {escape(item.get('title', title.strip()))}")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command(["comment", "close", "reopen", "lock", "unlock", "assign", "assignme", "unassign", "label", "milestone", "pin", "unpin"]))
    async def issue_action(client, message):
        service, repo, number = await context_from_reply(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo or number is None:
            await message.reply_text(REPLY_REQUIRED)
            return
        owner, name = repo_parts(repo)
        action = message.command[0].lower()
        value = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else ""
        try:
            if action == "comment":
                if not value:
                    await message.reply_text("Use /comment text.")
                    return
                await service.issue_comment(owner, name, number, value)
            elif action in {"close", "reopen"}:
                await service.update_issue(owner, name, number, state="closed" if action == "close" else "open")
            elif action == "lock":
                await service.lock_issue(owner, name, number)
            elif action == "unlock":
                await service.unlock_issue(owner, name, number)
            elif action == "assignme":
                user = await service.get_user()
                await service.add_assignees(owner, name, number, [user["login"]])
            elif action in {"assign", "unassign"}:
                if not value:
                    await message.reply_text("Use /assign @username.")
                    return
                users = [value.lstrip("@")]
                if action == "assign":
                    await service.add_assignees(owner, name, number, users)
                else:
                    await service.remove_assignees(owner, name, number, users)
            elif action == "label":
                if not value:
                    await message.reply_text(USAGE_LABEL)
                    return
                current_labels = await service.issue_labels(owner, name, number)
                labels = [item["name"] for item in current_labels]
                add = [x[1:] for x in value.split() if x.startswith("+") and len(x) > 1]
                remove = [x[1:] for x in value.split() if x.startswith("-") and len(x) > 1]
                labels = [x for x in labels if x not in remove]
                labels.extend(x for x in add if x not in labels)
                await service.set_issue_labels(owner, name, number, labels)
            elif action == "milestone":
                if not value:
                    await message.reply_text("Use /milestone milestone-title.")
                    return
                milestones = await service.client.request("GET", f"/repos/{owner}/{name}/milestones", params={"state": "open", "per_page": 100})
                match = next((m for m in milestones if m.get("title", "").lower() == value.lower()), None)
                if not match:
                    await message.reply_text("Milestone not found.")
                    return
                await service.update_issue(owner, name, number, milestone=match["number"])
            else:
                issue_item = await service.issue(owner, name, number)
                node_id = issue_item.get("node_id")
                if not node_id:
                    raise RuntimeError("GitHub issue node ID is unavailable")
                mutation = "pinIssue" if action == "pin" else "unpinIssue"
                await service.client.graphql(
                    f"mutation($issueId:ID!){{ {mutation}(input:{{issueId:$issueId}}){{ issue {{ number }} }} }}",
                    {"issueId": node_id},
                )
            await message.reply_text(f"<b>#{number} updated.</b>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("labels"))
    async def labels(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        owner, name = repo_parts(repo)
        try:
            items = await service.labels(owner, name)
            if not items:
                await message.reply_text("<b>No labels.</b>")
                return
            lines = [f"<b>Labels · {escape(repo['full_name'])}</b>"]
            lines.extend(f"\n<code>{escape(item.get('name', 'label'))}</code>" for item in items[:80])
            await message.reply_text("".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("commit"))
    async def commit(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        if len(message.command) < 2:
            await message.reply_text("Use /commit SHA.")
            return
        owner, name = repo_parts(repo)
        try:
            item = await service.commit(owner, name, message.command[1])
            data = item.get("commit", {})
            message_text = escape((data.get("message") or "").split("\n", 1)[0])
            author = escape(data.get("author", {}).get("name") or item.get("author", {}).get("login") or "unknown")
            files = item.get("files") or []
            await message.reply_text(
                f"<b>{escape(item.get('sha', '')[:12])}</b>\n\n{message_text}\n\nby <code>{author}</code>\nfiles {len(files)} · +{item.get('stats', {}).get('additions', 0)} -{item.get('stats', {}).get('deletions', 0)}"
            )
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("commits"))
    async def commits(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        owner, name = repo_parts(repo)
        try:
            items = await service.commits(owner, name, message.command[1] if len(message.command) > 1 else None, per_page=30)
            lines = [f"<b>Commits · {escape(repo['full_name'])}</b>"]
            lines.extend(f"\n<code>{escape(item.get('sha', '')[:10])}</code> {escape((item.get('commit', {}).get('message') or 'commit').split(chr(10), 1)[0])[:110]}" for item in items)
            await message.reply_text("".join(lines) if items else "<b>No commits found.</b>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("compare"))
    async def compare(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        if len(message.command) < 3:
            await message.reply_text(USAGE_COMPARE)
            return
        owner, name = repo_parts(repo)
        try:
            item = await service.compare(owner, name, message.command[1], message.command[2])
            lines = [
                f"<b>{escape(message.command[1])} → {escape(message.command[2])}</b>",
                "",
                f"<code>{escape(item.get('status', 'unknown'))}</code> · ahead {item.get('ahead_by', 0)} · behind {item.get('behind_by', 0)}",
                f"commits {item.get('total_commits', 0)} · files {len(item.get('files') or [])}",
            ]
            for file in (item.get("files") or [])[:25]:
                lines.append(f"\n<code>{escape(file.get('status', 'modified'))}</code> {escape(file.get('filename', 'file'))} · +{file.get('additions', 0)} -{file.get('deletions', 0)}")
            await message.reply_text("".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command(["release"]))
    async def release(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        owner, name = repo_parts(repo)
        args = message.command[1:]
        try:
            if args and args[0].lower() == "create":
                if len(args) < 2:
                    await message.reply_text("Use /release create v1.0.0.")
                    return
                tag = args[1]
                body = " ".join(args[2:]).strip()
                data = await service.client.request("POST", f"/repos/{owner}/{name}/releases", json={"tag_name": tag, "name": tag, "body": body, "generate_release_notes": not bool(body), "draft": False, "prerelease": False})
                await message.reply_text(f"<b>Release created</b>\n\n<code>{escape(data.get('tag_name', tag))}</code>")
                return
            data = await service.client.request("GET", f"/repos/{owner}/{name}/releases/latest")
            lines = [
                f"<b>{escape(data.get('name') or data.get('tag_name', 'Latest release'))}</b>",
                f"<code>{escape(data.get('tag_name', ''))}</code>",
                "",
                escape(data.get("body") or "No release notes."),
            ]
            if data.get("html_url"):
                lines.append(f"\n{escape(data['html_url'])}")
            await message.reply_text("\n".join(lines)[:7000])
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("changelog"))
    async def changelog(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        owner, name = repo_parts(repo)
        try:
            data = await service.client.request("POST", f"/repos/{owner}/{name}/releases/generate-notes", json={"tag_name": message.command[1] if len(message.command) > 1 else "next-release"})
            name_text = data.get("name") or data.get("tag_name", "Release notes")
            body = data.get("body") or "No generated notes."
            await message.reply_text(f"<b>{escape(name_text)}</b>\n\n{escape(body)}"[:7000])
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command(["find", "search"]))
    async def search(client, message):
        service, repo = await current(message.from_user.id, message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        query = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else ""
        if not query:
            await message.reply_text("Use /find keyword.")
            return
        try:
            if message.command[0].lower() == "find":
                base = f"repo:{repo['full_name']} {query}" if repo else query
                data = await service.search_issues(base)
                items = data.get("items", [])
                title = "Issues"
            else:
                base = f"repo:{repo['full_name']} {query}" if repo else query
                data = await service.client.request("GET", "/search/code", params={"q": base, "per_page": 20})
                items = data.get("items", [])
                title = "Code"
            lines = [f"<b>{title}</b>"]
            for item in items[:20]:
                lines.append(f"\n<code>{escape(item.get('full_name') or item.get('title') or item.get('name', 'result'))}</code>")
            await message.reply_text("".join(lines) if len(lines) > 1 else "<b>No results.</b>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("stats"))
    async def stats(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        owner, name = repo_parts(repo)
        try:
            data = await service.get(owner, name)
            lines = [
                f"<b>{escape(data['full_name'])}</b>",
                f"stars {data.get('stargazers_count', 0)}",
                f"watchers {data.get('subscribers_count', 0)}",
                f"forks {data.get('forks_count', 0)}",
                f"open issues {data.get('open_issues_count', 0)}",
                f"size {data.get('size', 0)} KB",
                f"network {data.get('network_count', 0)} · subscribers {data.get('subscribers_count', 0)}",
            ]
            await message.reply_text("\n".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("activity"))
    async def activity(client, message):
        service, repo = await require_repo(message)
        if not service:
            return
        owner, name = repo_parts(repo)
        try:
            events = await service.client.request("GET", f"/repos/{owner}/{name}/activity", params={"per_page": 25, "direction": "desc"})
            lines = [f"<b>Activity · {escape(repo['full_name'])}</b>"]
            for event in events[:20]:
                actor = escape(event.get("pusher", {}).get("login", "unknown"))
                ref = escape((event.get("ref") or "").removeprefix("refs/heads/"))
                kind = escape(event.get("push_type") or "activity")
                lines.append(f"\n<code>{kind}</code> · {actor} · {ref}")
            await message.reply_text("".join(lines) if events else "<b>No recent activity.</b>")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("settings"))
    async def settings(client, message):
        current_settings = await store.get_settings(message.from_user.id)
        if len(message.command) > 1:
            value = message.command[1].lower()
            if value in {"on", "off"}:
                await store.save_setting(message.from_user.id, "notifications_enabled", value == "on")
            elif value.startswith("events="):
                events = [item.strip() for item in value[7:].split(",") if item.strip()]
                allowed = {"push", "pull_request", "issues", "release", "workflow_run", "star", "fork", "create", "delete", "deployment"}
                events = [item for item in events if item in allowed]
                if events:
                    await store.save_setting(message.from_user.id, "events", events)
            current_settings = await store.get_settings(message.from_user.id)
        enabled = current_settings.get("notifications_enabled", True)
        events = current_settings.get("events", ["push", "pull_request", "issues", "release", "workflow_run", "star"])
        await message.reply_text(f"<b>Settings</b>\n\nnotifications <code>{'on' if enabled else 'off'}</code>\nevents <code>{escape(', '.join(events))}</code>\n\n/settings on|off\n/settings events=push,pull_request,issues")

    @app.on_message(filters.command("reload"))
    async def reload(client, message):
        await message.reply_text("<b>Cache reloaded.</b>")

    @app.on_message(filters.command(["mute", "done", "read"]))
    async def notification_action(client, message):
        if not message.reply_to_message:
            await message.reply_text(REPLY_REQUIRED)
            return
        notification = await store.notification(message.from_user.id, message.reply_to_message.id)
        if not notification:
            await message.reply_text(REPLY_REQUIRED)
            return
        action = message.command[0].lower()
        if action == "mute":
            await store.save_setting(message.from_user.id, f"mute:{notification['repository_id']}", True)
            text = "Repository notifications muted."
        else:
            await store.save_setting(message.from_user.id, f"notification:{notification['_id']}", action)
            text = "Notification marked as done." if action == "done" else "Notification marked as read."
        await message.reply_text(f"<b>{text}</b>")

    @app.on_message(filters.command("privacy"))
    async def privacy(client, message):
        await message.reply_text("<b>Privacy</b>\n\nGitHub OAuth tokens are encrypted before storage. Telegram messages used for commands and GitHub notifications are processed only to provide the requested bot functionality. Secrets are never stored in the repository.")

    @app.on_message(filters.command("help"))
    async def help_command(client, message):
        await message.reply_text(HELP_TEXT)

    return me, disconnect, addrepo, removerepo, repos, repo, repo_state, fork, repository_data, branch, default_branch, issue, issue_action, labels, commit, commits, compare, release, changelog, search, stats, activity, settings, reload, notification_action, privacy, help_command
