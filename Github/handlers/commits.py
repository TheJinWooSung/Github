from ..buttons import CommitView, commit_review, commit_preview

def build_commit_review(repository: str, branch: str, files: int, additions: int, deletions: int, message: str):
    view = CommitView(repository, branch, files, additions, deletions, message)
    return commit_preview(view), commit_review()
