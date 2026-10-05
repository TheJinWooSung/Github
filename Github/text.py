from dataclasses import dataclass

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
ACCESS_REQUIRED = "GitHub access is required"

@dataclass(frozen=True)
class CommitView:
    repository: str
    branch: str
    files: int
    additions: int
    deletions: int
    message: str

def commit_preview(data: CommitView) -> str:
    return f"<b>{REVIEW_CHANGES}</b>\\n\\n<code>{data.repository}</code> · <code>{data.branch}</code>\\n\\n{FILES}  <b>{data.files}</b>\\n{ADDED}  <b>+{data.additions}</b>\\n{REMOVED}  <b>-{data.deletions}</b>\\n\\n<b>{COMMIT_MESSAGE}</b>\\n<code>{data.message}</code>\\n\\n{CONFIRM_COMMIT}"

def repo_home(owner: str, name: str, branch: str, description: str | None = None) -> str:
    body = f"<b>{owner}/{name}</b>\\n\\n{BRANCH}  <code>{branch}</code>"
    return f"{body}\\n\\n{description}" if description else body

def file_view(path: str, size: int, branch: str) -> str:
    return f"<b>{path}</b>\\n\\n{BRANCH}  <code>{branch}</code>\\n{SIZE}  <code>{size:,} bytes</code>"

def start() -> str:
    return f"<b>{START}</b>\\n\\n{START_HINT}"

def repository_list(items: list[dict]) -> str:
    if not items:
        return EMPTY
    lines = [f"<b>{REPOSITORIES}</b>"]
    for item in items[:20]:
        full_name = item.get("full_name", item.get("name", "repository"))
        private = " · private" if item.get("private") else ""
        lines.append(f"\\n<code>{full_name}</code>{private}")
    return "".join(lines)

def branch_list(items: list[dict]) -> str:
    if not items:
        return EMPTY
    lines = [f"<b>{BRANCHES}</b>"]
    for item in items[:30]:
        lines.append(f"\\n<code>{item.get('name', 'unknown')}</code>")
    return "".join(lines)

def error_message(message: str | None = None) -> str:
    return f"<b>{ERROR}</b>\\n\\n<code>{message}</code>" if message else f"<b>{ERROR}</b>"
