from html import escape
from pyrogram import filters

from ..buttons import error_message
from ..github.client import GitHubClient
from ..github.repositories import RepositoryService
from ..storage import GitHubStore

AUTH_REQUIRED = "Connect GitHub first with /connect."
REPO_REQUIRED = "Link a repository first with /addrepo owner/repo."
DISCUSSION_USAGE = "Use /discussion or /discussion number."
ANSWER_USAGE = "Use /answered COMMENT_NODE_ID."

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

    @app.on_message(filters.command("discussion"))
    async def discussion(client, message):
        service, repo = await repo_context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPO_REQUIRED)
            return
        owner, name = repo["owner"]["login"], repo["name"]
        try:
            number = int(message.command[1]) if len(message.command) > 1 else None
            if number is not None:
                query = """
                query($owner:String!,$name:String!,$number:Int!){
                  repository(owner:$owner,name:$name){
                    discussion(number:$number){
                      number title body url isAnswered
                      category{name}
                      author{login}
                    }
                  }
                }
                """
                data = await service.client.graphql(query, {"owner": owner, "name": name, "number": number})
                item = (data.get("repository") or {}).get("discussion")
                if not item:
                    await message.reply_text("<b>Discussion not found.</b>")
                    return
                body = escape(item.get("body") or "")
                lines = [
                    f"<b>#{item['number']} {escape(item.get('title') or 'Discussion')}</b>",
                    f"<code>{escape(item.get('category', {}).get('name') or 'Discussion')}</code> · {'answered' if item.get('isAnswered') else 'open'}",
                ]
                if item.get("author", {}).get("login"):
                    lines.append(f"by <code>{escape(item['author']['login'])}</code>")
                if body:
                    lines.extend(["", body[:3000]])
                if item.get("url"):
                    lines.extend(["", escape(item["url"])])
                await message.reply_text("\n".join(lines))
                return
            query = """
            query($owner:String!,$name:String!){
              repository(owner:$owner,name:$name){
                discussions(first:20,orderBy:{field:UPDATED_AT,direction:DESC}){
                  nodes{number title url isAnswered category{name} author{login}}
                }
              }
            }
            """
            data = await service.client.graphql(query, {"owner": owner, "name": name})
            items = ((data.get("repository") or {}).get("discussions") or {}).get("nodes") or []
            if not items:
                await message.reply_text("<b>No discussions found.</b>")
                return
            lines = [f"<b>Discussions · {escape(repo['full_name'])}</b>"]
            for item in items:
                state = "answered" if item.get("isAnswered") else "open"
                lines.append(f"\n<code>#{item.get('number')}</code> {escape(item.get('title') or 'Discussion')} · {state}")
            await message.reply_text("".join(lines))
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    @app.on_message(filters.command("answered"))
    async def answered(client, message):
        service, repo = await repo_context(message)
        if not service:
            await message.reply_text(AUTH_REQUIRED)
            return
        if not repo:
            await message.reply_text(REPO_REQUIRED)
            return
        if len(message.command) < 2:
            await message.reply_text(ANSWER_USAGE)
            return
        comment_id = message.command[1]
        mutation = """
        mutation($id:ID!){
          markDiscussionCommentAsAnswer(input:{id:$id}){
            discussion{number title isAnswered}
          }
        }
        """
        try:
            data = await service.client.graphql(mutation, {"id": comment_id})
            item = data.get("markDiscussionCommentAsAnswer", {}).get("discussion") or {}
            await message.reply_text(f"<b>Discussion answered.</b>\n\n<code>#{item.get('number', '?')}</code> {escape(item.get('title') or 'Discussion')}")
        except Exception as exc:
            await message.reply_text(error_message(str(exc)))

    return discussion, answered
