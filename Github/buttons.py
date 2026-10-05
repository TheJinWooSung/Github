from dataclasses import dataclass
from html import escape
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

START = "GitHub control center"
START_HINT = "Manage repositories, branches, files, commits, pull requests and Actions from Telegram."
REPOSITORIES = "Repositories"
SEARCH = "Search"
STARRED = "Starred"
SETTINGS = "Settings"
CONNECT = "Connect GitHub"
INTEGRATIONS = "Integrations"
CONNECT_HINT = "Authorize GitHub to manage your repositories from Telegram."
BACK = "Back"
HOME = "Home"
FILES = "Files"
COMMITS = "Commits"
BRANCHES = "Branches"
TAGS = "Tags"
PULL_REQUESTS = "Pull requests"
ISSUES = "Issues"
ACTIONS = "Actions"
RELEASES = "Releases"
CONTRIBUTORS = "Contributors"
DEPLOYMENTS = "Deployments"
REVIEW_CHANGES = "Review changes"
COMMIT_MESSAGE = "Commit message"
CONFIRM_COMMIT = "Confirm this commit?"
ADDED = "Added"
REMOVED = "Removed"
BRANCH = "Branch"
SIZE = "Size"
EMPTY = "Nothing found"
ERROR = "Something went wrong"
EDIT_FILE = "Edit file"
EDIT_INSTRUCTION = "Send the complete new file content as your next message."
COMMIT_INSTRUCTION = "Send the commit message for this change."
SESSION_EXPIRED = "Edit session expired"
COMMIT_SESSION_EXPIRED = "Commit session expired"
COMMIT_CANCELLED = "Commit cancelled"
COMMIT_CREATED = "Commit created"
UNCHANGED_FILE = "No changes were made to the file."
INVALID_COMMIT_MESSAGE = "Commit message is required."
NOT_CONNECTED = "Connect GitHub first with /connect."
INTEGRATION_USAGE = "Usage: /newintegration owner/repository"
INTEGRATION_ADDED = "Repository integration added."
INTEGRATION_EXISTS = "Repository integration already exists."
INTEGRATION_REMOVED = "Repository integration removed."
INTEGRATION_NOT_FOUND = "Repository integration was not found."
INTEGRATIONS_EMPTY = "No repository integrations are configured."
INTEGRATION_LIST = "Repository integrations"

@dataclass(frozen=True)
class CommitView:
    repository: str
    branch: str
    files: int
    additions: int
    deletions: int
    message: str

def _row(*items):
    return [InlineKeyboardButton(label, callback_data=data) for label, data in items]

def start(connect_url: str | None = None):
    rows = [_row((REPOSITORIES, "home:repos"), (SEARCH, "home:search")), _row((STARRED, "home:starred"), (SETTINGS, "home:settings"))]
    if connect_url:
        rows.insert(0, [InlineKeyboardButton(CONNECT, url=connect_url)])
    return InlineKeyboardMarkup(rows)

def integrations(items):
    rows = []
    for item in items[:50]:
        rows.append(_row((item["full_name"][:55], f"integration:{item['repository_id']}:delete")))
    rows.append(_row((CONNECT, "connect:start")))
    return InlineKeyboardMarkup(rows)

def connect_text():
    return f"<b>{CONNECT}</b>\n\n{CONNECT_HINT}"

def repository(repository_id: int):
    return InlineKeyboardMarkup([_row((FILES, f"repo:{repository_id}:files"), (COMMITS, f"repo:{repository_id}:commits")), _row((BRANCHES, f"repo:{repository_id}:branches"), (TAGS, f"repo:{repository_id}:tags")), _row((PULL_REQUESTS, f"repo:{repository_id}:pulls"), (ISSUES, f"repo:{repository_id}:issues")), _row((ACTIONS, f"repo:{repository_id}:actions"), (RELEASES, f"repo:{repository_id}:releases")), _row((CONTRIBUTORS, f"repo:{repository_id}:contributors"), (DEPLOYMENTS, f"repo:{repository_id}:deployments")), _row((HOME, "nav:home"))])

def commit_review(token: str):
    return InlineKeyboardMarkup([_row(("Edit", f"edit:{token}"), ("Cancel", f"commit:{token}:cancel")), _row(("Commit", f"commit:{token}:confirm"))])

def back(target: str = "nav:back"):
    return InlineKeyboardMarkup([_row((BACK, target))])

def pagination(prefix: str, page: int, has_next: bool = True):
    row = []
    if page > 1:
        row.append(InlineKeyboardButton("Previous", callback_data=f"{prefix}:page:{page - 1}"))
    if has_next:
        row.append(InlineKeyboardButton("Next", callback_data=f"{prefix}:page:{page + 1}"))
    return InlineKeyboardMarkup([row, _row((BACK, "nav:back"))]) if row else back()

def branches(items):
    rows = [_row((item["name"][:60], f"branch:{item['name']}")) for item in items[:20] if item.get("name")]
    rows.append(_row((BACK, "nav:back")))
    return InlineKeyboardMarkup(rows)

def repositories(items):
    rows = [_row((item["full_name"][:60], f"repo:{item['id']}")) for item in items[:20] if item.get("full_name")]
    rows.append(_row((BACK, "nav:home")))
    return InlineKeyboardMarkup(rows)

def start_text():
    return f"<b>{START}</b>\n\n{START_HINT}"

def repository_list(items):
    if not items:
        return EMPTY
    lines = [f"<b>{REPOSITORIES}</b>"]
    for item in items[:20]:
        name = escape(item.get("full_name", item.get("name", "repository")))
        private = " · private" if item.get("private") else ""
        lines.append(f"\n<code>{name}</code>{private}")
    return "".join(lines)

def repo_home(owner: str, name: str, branch: str, description: str | None = None):
    body = f"<b>{escape(owner)}/{escape(name)}</b>\n\n{BRANCH}  <code>{escape(branch)}</code>"
    return f"{body}\n\n{escape(description)}" if description else body

def error_message(message: str | None = None):
    return f"<b>{ERROR}</b>\n\n<code>{escape(message)}</code>" if message else f"<b>{ERROR}</b>"

def commit_preview(data: CommitView):
    return f"<b>{REVIEW_CHANGES}</b>\n\n<code>{escape(data.repository)}</code> · <code>{escape(data.branch)}</code>\n\n{FILES}  <b>{data.files}</b>\n{ADDED}  <b>+{data.additions}</b>\n{REMOVED}  <b>-{data.deletions}</b>\n\n<b>{COMMIT_MESSAGE}</b>\n<code>{escape(data.message)}</code>\n\n{CONFIRM_COMMIT}"

def files(items, browser_token: str, parent_token: str | None = None):
    rows = []
    for index, item in enumerate(items[:20]):
        name = item.get("name", "item")
        label = f"DIR  {name}" if item.get("type") == "dir" else name
        rows.append(_row((label[:55], f"file:{browser_token}:{index}")))
    rows.append(_row((BACK, f"browse:{parent_token}:back" if parent_token else "nav:back")))
    return InlineKeyboardMarkup(rows)

def file_view(repository_id: int, edit_token: str, browser_token: str):
    return InlineKeyboardMarkup([_row(("Edit", f"edit:{edit_token}")), _row((BACK, f"browse:{browser_token}:back"))])

def files_text(owner: str, name: str, branch: str, path: str, items):
    title = f"<b>{escape(owner)}/{escape(name)}</b>  <code>{escape(branch)}</code>"
    location = f"\n\n<code>/{escape(path)}</code>" if path else ""
    if not items:
        return title + location + "\n\n" + EMPTY
    lines = [title + location]
    for item in items[:20]:
        marker = "DIR" if item.get("type") == "dir" else "FILE"
        lines.append(f"\n{marker}  <code>{escape(item.get('name', 'item'))}</code>")
    return "".join(lines)

def edit_prompt(path: str):
    return f"<b>{EDIT_FILE}</b>\n\n<code>{escape(path)}</code>\n\n{EDIT_INSTRUCTION}"

def commit_prompt():
    return f"<b>{COMMIT_MESSAGE}</b>\n\n{COMMIT_INSTRUCTION}"

def commit_result(sha: str, path: str, message: str):
    return f"<b>{COMMIT_CREATED}</b>\n\n<code>{escape(sha[:12])}</code>\n<code>{escape(path)}</code>\n\n{escape(message)}"

def file_text(owner: str, name: str, path: str, content: str, branch: str):
    body = content[:3500]
    return f"<b>{escape(owner)}/{escape(name)}</b>\n\n<code>{escape(path)}</code>\n<code>{escape(branch)}</code>\n\n<pre>{escape(body)}</pre>"
