from html import escape
from pyrogram import filters

from ..buttons import error_message
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

AUTH_REQUIRED = "Connect GitHub first with /connect."
REPO_REQUIRED = "Link a repository first with /addrepo owner/repo."

def register(app, store: GitHubStore, oauth):
    async def service_for(user_id: int):
        token = await store.token(user_id, oauth)
        return RepositoryService(GitHubClient(token)) if token else None

    @app.on_message(filters.command("me"))
    async def me(client, message):
        service = await service_for(message.from_user.id)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        try:
            user = await service.get_user()
            lines = [f"<b>{escape(user.get('login', 'unknown'))}</b>", f"<code>ID {user.get('id', '')}</code>"]
            if user.get("name"):
                lines.append(escape(user["name"]))
            if user.get("email"):
                lines.append(escape(user["email"]))
            await message.reply_text("\n".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("repo"))
    async def repo(client, message):
        service = await service_for(message.from_user.id)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        raw = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else ""
        if "/" not in raw:
            await message.reply_text(REPO_REQUIRED)
            return
        owner, name = raw.split("/", 1)
        try:
            item = await service.get(owner, name)
            text = f"<b>{escape(item['full_name'])}</b>\n\n{escape(item.get('description') or 'No description')}\n\n<code>{escape(item.get('default_branch', 'main'))}</code> · {item.get('visibility', 'public')}\n⭐ {item.get('stargazers_count', 0)} · forks {item.get('forks_count', 0)} · issues {item.get('open_issues_count', 0)}"
            await message.reply_text(text)
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command(["contributors", "languages", "branches"]))
    async def repository_data(client, message):
        service = await service_for(message.from_user.id)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        raw = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else ""
        if "/" not in raw:
            await message.reply_text(REPO_REQUIRED)
            return
        owner, name = raw.split("/", 1)
        try:
            action = message.command[0].lower()
            if action == "contributors":
                items = await service.contributors(owner, name)
                lines = [f"<b>{escape(owner)}/{escape(name)}</b>"]
                lines.extend(f"\n{index}. <code>{escape(item.get('login') or 'unknown')}</code> · {item.get('contributions', 0)}" for index, item in enumerate(items[:15], 1))
            elif action == "languages":
                data = await service.languages(owner, name)
                total = sum(data.values()) or 1
                lines = [f"<b>{escape(owner)}/{escape(name)}</b>"]
                lines.extend(f"\n<code>{escape(key)}</code> · {value / total * 100:.1f}%" for key, value in sorted(data.items(), key=lambda pair: pair[1], reverse=True))
            else:
                items = await service.branches(owner, name)
                lines = [f"<b>{escape(owner)}/{escape(name)}</b>"]
                lines.extend(f"\n<code>{escape(item.get('name', 'branch'))}</code>" for item in items[:30])
            await message.reply_text("".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    return me, repo, repository_data
