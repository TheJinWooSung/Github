from pyrogram import filters
from ..buttons import NOT_CONNECTED, PR_ERROR, PR_REVIEWED, PR_MERGED, PR_CLOSED, PR_REOPENED, REVIEW_PROMPT, REVIEW_REQUIRED, MERGE_CONFIRM, error_message, pull_requests, pull_request_view, pull_request_text, pull_request_files_text, pull_request_commits_text, pull_request_reviews_text
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..state import ReviewSession, SessionStore
from ..storage import GitHubStore

def register(app, store: GitHubStore, sessions: SessionStore, oauth):
    async def service_for(user_id: int):
        token = await store.token(user_id, oauth)
        if not token:
            return None
        return RepositoryService(GitHubClient(token))

    @app.on_callback_query(filters.regex(r"^repo:\d+:pulls$"))
    async def list_pull_requests(client, query):
        await query.answer()
        repository_id = int(query.data.split(":")[1])
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(NOT_CONNECTED)
            return
        try:
            repo = await service.get_by_id(repository_id)
            items = await service.pull_requests(repo["owner"]["login"], repo["name"])
            await query.message.edit_text(f"<b>{repo['full_name']}</b>\n\nPull requests", reply_markup=pull_requests(items, repository_id))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^pr:\d+:\d+$"))
    async def show_pull_request(client, query):
        await query.answer()
        _, repository_id, number = query.data.split(":")
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(NOT_CONNECTED)
            return
        try:
            repo = await service.get_by_id(int(repository_id))
            item = await service.pull_request(repo["owner"]["login"], repo["name"], int(number))
            await query.message.edit_text(pull_request_text(item), reply_markup=pull_request_view(int(repository_id), int(number), item.get("state", "open"), item.get("draft", False)))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^pr:\d+:\d+:(files|commits|reviews)$"))
    async def pull_request_data(client, query):
        await query.answer()
        _, repository_id, number, action = query.data.split(":")
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(NOT_CONNECTED)
            return
        try:
            repo = await service.get_by_id(int(repository_id))
            owner, name = repo["owner"]["login"], repo["name"]
            if action == "files":
                body = pull_request_files_text(await service.pull_request_files(owner, name, int(number)))
            elif action == "commits":
                body = pull_request_commits_text(await service.pull_request_commits(owner, name, int(number)))
            else:
                body = pull_request_reviews_text(await service.pull_request_reviews(owner, name, int(number)))
            await query.message.edit_text(body, reply_markup=pull_request_view(int(repository_id), int(number), "open"))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^pr:\d+:\d+:(approve|changes|comment)$"))
    async def review_action(client, query):
        await query.answer()
        _, repository_id, number, action = query.data.split(":")
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(NOT_CONNECTED)
            return
        try:
            repo = await service.get_by_id(int(repository_id))
            owner, name = repo["owner"]["login"], repo["name"]
            if action == "approve":
                await service.submit_review(owner, name, int(number), "APPROVE")
                await query.message.edit_text(PR_REVIEWED, reply_markup=pull_request_view(int(repository_id), int(number), "open"))
                return
            event = "REQUEST_CHANGES" if action == "changes" else "COMMENT"
            session = ReviewSession(query.from_user.id, query.message.chat.id, int(repository_id), owner, name, int(number), event)
            token = await sessions.create_review(session)
            await query.message.edit_text(REVIEW_PROMPT)
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_callback_query(filters.regex(r"^pr:\d+:\d+:(merge|close|reopen|ready)$"))
    async def state_action(client, query):
        await query.answer()
        _, repository_id, number, action = query.data.split(":")
        service = await service_for(query.from_user.id)
        if not service:
            await query.message.edit_text(NOT_CONNECTED)
            return
        try:
            repo = await service.get_by_id(int(repository_id))
            owner, name = repo["owner"]["login"], repo["name"]
            number = int(number)
            if action == "merge":
                item = await service.pull_request(owner, name, number)
                if item.get("state") != "open":
                    await query.message.edit_text(PR_ERROR)
                    return
                result = await service.merge_pull_request(owner, name, number, "squash", item.get("head", {}).get("sha"))
                if not result.get("merged"):
                    await query.message.edit_text(f"{PR_ERROR}\n\n{result.get('message', 'GitHub did not merge the pull request.')}")
                    return
                await query.message.edit_text(PR_MERGED, reply_markup=pull_request_view(int(repository_id), number, "closed"))
            elif action == "close":
                await service.update_pull_request(owner, name, number, state="closed")
                await query.message.edit_text(PR_CLOSED, reply_markup=pull_request_view(int(repository_id), number, "closed"))
            elif action == "reopen":
                await service.update_pull_request(owner, name, number, state="open")
                await query.message.edit_text(PR_REOPENED, reply_markup=pull_request_view(int(repository_id), number, "open"))
            else:
                await service.update_pull_request(owner, name, number, state="open")
                await query.message.edit_text(PR_REVIEWED, reply_markup=pull_request_view(int(repository_id), number, "open"))
        except Exception as exc:
            await query.message.edit_text(error_message(str(exc)))

    @app.on_message(filters.text & ~filters.command(["start", "connect", "repos", "newintegration", "listintegrations", "delintegration"]))
    async def review_text(client, message):
        token = await sessions.review(message.from_user.id)
        if not token:
            return
        session = await sessions.get(token)
        if not isinstance(session, ReviewSession):
            return
        body = message.text.strip()
        if not body:
            await message.reply_text(REVIEW_REQUIRED)
            return
        service = await service_for(message.from_user.id)
        if not service:
            await message.reply_text(NOT_CONNECTED)
            return
        try:
            await service.submit_review(session.owner, session.name, session.number, session.event, body)
            await sessions.delete(token)
            await message.reply_text(PR_REVIEWED)
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    return list_pull_requests, show_pull_request, pull_request_data, review_action, state_action, review_text
