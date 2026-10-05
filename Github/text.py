from dataclasses import dataclass

REVIEW_CHANGES = "Review changes"
COMMIT_MESSAGE = "Commit message"
CONFIRM_COMMIT = "Confirm this commit?"
FILES = "Files"
ADDED = "Added"
REMOVED = "Removed"
BRANCH = "Branch"
SIZE = "Size"

@dataclass(frozen=True)
class CommitView:
    repository: str
    branch: str
    files: int
    additions: int
    deletions: int
    message: str

def commit_preview(data: CommitView) -> str:
    return (f"<b>{REVIEW_CHANGES}</b>\n\n<code>{data.repository}</code> · <code>{data.branch}</code>\n\n{FILES}  <b>{data.files}</b>\n{ADDED}  <b>+{data.additions}</b>\n{REMOVED}  <b>-{data.deletions}</b>\n\n<b>{COMMIT_MESSAGE}</b>\n<code>{data.message}</code>\n\n{CONFIRM_COMMIT}")

def repo_home(owner: str, name: str, branch: str) -> str:
    return f"<b>{owner}/{name}</b>\n\n{BRANCH}  <code>{branch}</code>"

def file_view(path: str, size: int, branch: str) -> str:
    return f"<b>{path}</b>\n\n{BRANCH}  <code>{branch}</code>\n{SIZE}  <code>{size:,} bytes</code>"
