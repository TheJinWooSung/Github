from ..buttons import commit_review
from ..text import CommitView, commit_preview

def build_commit_review(repository: str, branch: str, files: int, additions: int, deletions: int, message: str):
    view = CommitView(repository, branch, files, additions, deletions, message)
    return commit_preview(view), commit_review()
