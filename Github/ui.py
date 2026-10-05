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
    return (f"<b>Review changes</b>\n\n<code>{data.repository}</code> · <code>{data.branch}</code>\n\nFiles  <b>{data.files}</b>\nAdded  <b>+{data.additions}</b>\nRemoved  <b>-{data.deletions}</b>\n\n<b>Commit message</b>\n{data.message}")
