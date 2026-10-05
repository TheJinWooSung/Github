from dataclasses import dataclass
from html import escape
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

START = "GitHub control center"
START_HINT = "Manage repositories, branches, files, commits, pull requests and Actions from Telegram."
REPOSITORIES = "Repositories"
SEARCH = "Search"
STARRED = "Starred"
SETTINGS = "Settings"
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

def start():
    return InlineKeyboardMarkup([_row((REPOSITORIES, "home:repos"), (SEARCH, "home:search")), _row((STARRED, "home:starred"), (SETTINGS, "home:settings"))])

def repository(repository_id: int):
    return InlineKeyboardMarkup([_row((FILES, f"repo:{repository_id}:files"), (COMMITS, f"repo:{repository_id}:commits")), _row((BRANCHES, f"repo:{repository_id}:branches"), (TAGS, f"repo:{repository_id}:tags")), _row((PULL_REQUESTS, f"repo:{repository_id}:pulls"), (ISSUES, f"repo:{repository_id}:issues")), _row((ACTIONS, f"repo:{repository_id}:actions"), (RELEASES, f"repo:{repository_id}:releases")), _row((CONTRIBUTORS, f"repo:{repository_id}:contributors"), (DEPLOYMENTS, f"repo:{repository_id}:deployments")), _row((HOME, "nav:home"))])

def commit_review():
    return InlineKeyboardMarkup([_row(("Edit", "commit:edit"), ("Cancel", "commit:cancel")), _row(("Commit", "commit:confirm"))])

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


def files(items, repository_id: int):
    rows = []
    for index, item in enumerate(items[:20]):
        name = item.get("name", "item")
        label = f"DIR  {name}" if item.get("type") == "dir" else name
        rows.append(_row((label[:55], f"file:{repository_id}:{index}")))
    rows.append(_row((BACK, f"repo:{repository_id}")))
    return InlineKeyboardMarkup(rows)

def file_view(repository_id: int):
    return InlineKeyboardMarkup([_row(("Edit", f"edit:{repository_id}")), _row((BACK, f"repo:{repository_id}:files"))])

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

def file_text(owner: str, name: str, path: str, content: str, branch: str):
    body = content[:3500]
    return f"<b>{escape(owner)}/{escape(name)}</b>\n\n<code>{escape(path)}</code>\n<code>{escape(branch)}</code>\n\n<pre>{escape(body)}</pre>"
