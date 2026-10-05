from dataclasses import dataclass

@dataclass(frozen=True)
class CommitPreview:
    repository: str
    branch: str
    files: int
    additions: int
    deletions: int
    message: str

def commit_preview(data: CommitPreview) -> str:
    return (f"<b>Review changes</b>\n\n<code>{data.repository}</code> · <code>{data.branch}</code>\n\nFiles  <b>{data.files}</b>\nAdded  <b>+{data.additions}</b>\nRemoved  <b>-{data.deletions}</b>\n\n<b>Commit message</b>\n<code>{data.message}</code>\n\nConfirm this commit?")

def repo_home(owner: str, name: str, branch: str) -> str:
    return f"<b>{owner}/{name}</b>\n\nBranch  <code>{branch}</code>"

def file_view(path: str, size: int, branch: str) -> str:
    return f"<b>{path}</b>\n\nBranch  <code>{branch}</code>\nSize  <code>{size:,} bytes</code>"
