from kurigram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .text import ACTIONS, BACK, BRANCHES, COMMITS, FILES, HOME, ISSUES, PULL_REQUESTS, RELEASES, REPOSITORIES, SEARCH, SETTINGS, STARRED, TAGS, CONTRIBUTORS, DEPLOYMENTS

def _row(*items):
    return [InlineKeyboardButton(label, callback_data=data) for label, data in items]

def start():
    return InlineKeyboardMarkup([_row((REPOSITORIES, "home:repos"), (SEARCH, "home:search")), _row((STARRED, "home:starred"), (SETTINGS, "home:settings"))])

def repository():
    return InlineKeyboardMarkup([_row((FILES, "repo:files"), (COMMITS, "repo:commits")), _row((BRANCHES, "repo:branches"), (TAGS, "repo:tags")), _row((PULL_REQUESTS, "repo:pulls"), (ISSUES, "repo:issues")), _row((ACTIONS, "repo:actions"), (RELEASES, "repo:releases")), _row((CONTRIBUTORS, "repo:contributors"), (DEPLOYMENTS, "repo:deployments")), _row((HOME, "nav:home"))])

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
    rows = []
    for item in items[:20]:
        name = item.get("name", "")
        if name:
            rows.append(_row((name[:60], f"branch:{name}")))
    rows.append(_row((BACK, "nav:back")))
    return InlineKeyboardMarkup(rows)

def repositories(items):
    rows = []
    for item in items[:20]:
        full_name = item.get("full_name", "")
        if full_name:
            rows.append(_row((full_name[:60], f"repo:{full_name}")))
    rows.append(_row((BACK, "nav:home")))
    return InlineKeyboardMarkup(rows)
