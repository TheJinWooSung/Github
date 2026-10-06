from dataclasses import dataclass
from html import escape
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

START = "GitHub control center"
START_HINT = "Manage repositories, branches, files, commits, pull requests and Actions from Telegram."
REPOSITORIES = "Repositories"
SEARCH = "Search"
STARRED = "Starred"
SETTINGS = "Settings"
CONNECT = "Connect GitHub"
AUTHORIZE_GITHUB = "Authorize GitHub"
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
COMMIT_MESSAGE_PROMPT = "Send the commit message."
SESSION_EXPIRED = "Edit session expired"
COMMIT_SESSION_EXPIRED = "Commit session expired"
COMMIT_CANCELLED = "Commit cancelled"
COMMIT_CREATED = "Commit created"
STAGED = "Staged changes"
STAGE_FILE = "Stage file"
COMMIT_STAGED = "Commit staged"
CLEAR_STAGED = "Clear staged"
STAGED_EMPTY = "No staged changes."
STAGED_CLEARED = "Staged changes cleared."
STAGED_BRANCH_CHANGED = "The branch changed while changes were being staged. Clear the staged changes and reopen the files."
STAGED_COUNT = "files staged"
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
INTEGRATION_EVENTS = "Webhook events"
INTEGRATION_ACTIVE = "Webhook active"
INTEGRATION_ON = "On"
INTEGRATION_OFF = "Off"
INTEGRATION_DELIVERIES = "Deliveries"
DELIVERY_LIST = "Webhook deliveries"
DELIVERY_RETRY = "Retry"
DELIVERY_REFRESH = "Refresh"
DELIVERY_BACK = "Webhook events"
REMOVE = "Remove"
EDIT = "Edit"
CANCEL = "Cancel"
COMMIT = "Commit"
PREVIOUS = "Previous"
NEXT = "Next"
DIRECTORY = "DIR  "
WEB_EDITOR = "Web editor"
DIFF = "Diff"
WEBHOOK_EVENTS = ("push", "pull_request", "issues", "issue_comment", "pull_request_review", "release", "workflow_run", "workflow_job", "deployment", "deployment_status", "star", "fork", "create", "delete")

PR_LIST = "Pull requests"
PR_FILES = "Files"
PR_COMMITS = "Commits"
PR_REVIEWS = "Reviews"
PR_APPROVE = "Approve"
PR_REQUEST_CHANGES = "Request changes"
PR_COMMENT = "Comment"
PR_MERGE = "Merge"
PR_CLOSE = "Close"
PR_REOPEN = "Reopen"
PR_READY = "Ready for review"
PR_DRAFT = "Convert to draft"
PR_BACK = "Repository"
REVIEW_PROMPT = "Send the review text as your next message."
REVIEW_REQUIRED = "A review message is required."
MERGE_CONFIRM = "Confirm merge"
MERGE_METHOD = "Merge method"
PR_UPDATED = "Pull request updated."
PR_MERGED = "Pull request merged."
PR_CLOSED = "Pull request closed."
PR_REOPENED = "Pull request reopened."
PR_REVIEWED = "Review submitted."
PR_EMPTY = "No pull requests found."
PR_ERROR = "Pull request action failed."

ACTIONS_TITLE = "GitHub Actions"
ACTION_WORKFLOWS = "Workflows"
ACTION_RUNS = "Runs"
ACTION_JOBS = "Jobs"
ACTION_ARTIFACTS = "Artifacts"
ACTION_RUN = "Run workflow"
ACTION_RERUN = "Rerun"
ACTION_RERUN_FAILED = "Rerun failed"
ACTION_CANCEL = "Cancel run"
ACTION_BACK = "Repository"
ACTIONS_EMPTY = "No Actions workflows found."
ACTION_RUNS_EMPTY = "No workflow runs found."
ACTION_JOBS_EMPTY = "No jobs found."
ACTION_ARTIFACTS_EMPTY = "No artifacts found."
ACTION_DISPATCHED = "Workflow dispatch requested."
ACTION_RERUNNED = "Workflow rerun requested."
ACTION_CANCELLED = "Workflow run cancelled."
ACTION_LOGS = "Logs"
ACTION_STEPS = "Steps"
ACTION_REFRESH = "Refresh"
ACTION_ERROR = "Actions request failed."
ACTION_CONNECT_REQUIRED = "Connect GitHub first with /connect."
ACTION_NOT_FOUND = "The requested Actions resource was not found."
ACTION_RUN_REQUEST = "Workflow dispatch requested."
ACTION_NO_STEPS = "No steps found."

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
        rows.append(_row((item["full_name"][:42], f"integration:{item['repository_id']}:events"), (REMOVE, f"integration:{item['repository_id']}:delete")))
    rows.append(_row((CONNECT, "connect:start")))
    return InlineKeyboardMarkup(rows)

def integration_events(repository_id: int, events: list[str], active: bool = True):
    rows = []
    for event in WEBHOOK_EVENTS:
        state = INTEGRATION_ON if event in events else INTEGRATION_OFF
        rows.append(_row((f"{event} · {state}", f"integration:{repository_id}:toggle:{event}")))
    rows.append(_row((f"{INTEGRATION_ACTIVE}: {INTEGRATION_ON if active else INTEGRATION_OFF}", f"integration:{repository_id}:active"), (INTEGRATION_DELIVERIES, f"integration:{repository_id}:deliveries")))
    rows.append(_row((BACK, "integrations:list")))
    return InlineKeyboardMarkup(rows)

def integration_deliveries(items, repository_id: int):
    rows = []
    for item in items[:25]:
        delivery = str(item.get("delivery_id", ""))[:12]
        label = f"{item.get('event', 'event')} · {item.get('status', 'unknown')} · {delivery}"
        rows.append(_row((label[:60], f"delivery:{repository_id}:{item.get('delivery_id', '')}")))
    rows.append(_row((DELIVERY_REFRESH, f"integration:{repository_id}:deliveries:refresh")))
    rows.append(_row((BACK, f"integration:{repository_id}:events")))
    return InlineKeyboardMarkup(rows)

def integration_delivery_text(item: dict):
    return f"<b>Webhook delivery</b>\n\n<code>{escape(str(item.get('delivery_id', '')))}</code>\n{escape(item.get('event', 'event'))} · <code>{escape(item.get('status', 'unknown'))}</code>" + (f"\n\n{escape(item.get('error', ''))}" if item.get("error") else "")

def integration_delivery_actions(repository_id: int, delivery_id: str, failed: bool):
    rows = []
    if failed:
        rows.append(_row((DELIVERY_RETRY, f"delivery:{repository_id}:{delivery_id}:retry")))
    rows.append(_row((DELIVERY_BACK, f"integration:{repository_id}:deliveries")))
    return InlineKeyboardMarkup(rows)

def integration_events_text(full_name: str, events: list[str], active: bool):
    selected = ", ".join(events) if events else "none"
    state = INTEGRATION_ON if active else INTEGRATION_OFF
    return f"<b>{INTEGRATION_EVENTS}</b>\n\n<code>{escape(full_name)}</code>\n{INTEGRATION_ACTIVE}: <b>{state}</b>\n\n<code>{escape(selected)}</code>"

def connect_text():
    return f"<b>{CONNECT}</b>\n\n{CONNECT_HINT}"

def repository(repository_id: int):
    return InlineKeyboardMarkup([_row((FILES, f"repo:{repository_id}:files"), (COMMITS, f"repo:{repository_id}:commits")), _row((BRANCHES, f"repo:{repository_id}:branches"), (TAGS, f"repo:{repository_id}:tags")), _row((PULL_REQUESTS, f"repo:{repository_id}:pulls"), (ISSUES, f"repo:{repository_id}:issues")), _row((ACTIONS, f"repo:{repository_id}:actions"), (RELEASES, f"repo:{repository_id}:releases")), _row((CONTRIBUTORS, f"repo:{repository_id}:contributors"), (DEPLOYMENTS, f"repo:{repository_id}:deployments")), _row((HOME, "nav:home"))])

def commit_review(token: str):
    return InlineKeyboardMarkup([_row((EDIT, f"edit:{token}"), (CANCEL, f"commit:{token}:cancel")), _row((COMMIT, f"commit:{token}:confirm"))])

def back(target: str = "nav:back"):
    return InlineKeyboardMarkup([_row((BACK, target))])

def pagination(prefix: str, page: int, has_next: bool = True):
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(PREVIOUS, callback_data=f"{prefix}:page:{page - 1}"))
    if has_next:
        row.append(InlineKeyboardButton(NEXT, callback_data=f"{prefix}:page:{page + 1}"))
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
        label = f"{DIRECTORY}{name}" if item.get("type") == "dir" else name
        rows.append(_row((label[:55], f"file:{browser_token}:{index}")))
    rows.append(_row((BACK, f"browse:{parent_token}:back" if parent_token else "nav:back")))
    return InlineKeyboardMarkup(rows)

def file_view(repository_id: int, edit_token: str, browser_token: str, webapp_url: str | None = None, path: str | None = None, branch: str | None = None):
    rows = [_row((EDIT, f"edit:{edit_token}"))]
    if webapp_url and path is not None and branch is not None:
        from urllib.parse import urlencode
        url = webapp_url.rstrip("/") + "/webapp/editor?" + urlencode({"repo": repository_id, "path": path, "branch": branch})
        rows.append([InlineKeyboardButton(WEB_EDITOR, web_app=WebAppInfo(url=url))])
    rows.append(_row((BACK, f"browse:{browser_token}:back")))
    return InlineKeyboardMarkup(rows)

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


def pull_requests(items, repository_id: int, state: str = "open"):
    rows = []
    for item in items[:20]:
        number = item.get("number")
        title = escape(item.get("title", "Pull request"))[:48]
        rows.append(_row((f"#{number} {title}", f"pr:{repository_id}:{number}")))
    rows.append(_row((BACK, f"repo:{repository_id}")))
    return InlineKeyboardMarkup(rows)

def pull_request_view(repository_id: int, number: int, state: str, draft: bool = False):
    rows = [
        _row((PR_FILES, f"pr:{repository_id}:{number}:files"), (PR_COMMITS, f"pr:{repository_id}:{number}:commits"), (DIFF, f"pr:{repository_id}:{number}:diff")),
        _row((PR_REVIEWS, f"pr:{repository_id}:{number}:reviews"), (PR_COMMENT, f"pr:{repository_id}:{number}:comment")),
    ]
    if state == "open":
        if draft:
            rows.append(_row((PR_READY, f"pr:{repository_id}:{number}:ready")))
        else:
            rows.append(_row((PR_APPROVE, f"pr:{repository_id}:{number}:approve"), (PR_REQUEST_CHANGES, f"pr:{repository_id}:{number}:changes")))
        rows.append(_row((PR_MERGE, f"pr:{repository_id}:{number}:merge"), (PR_CLOSE, f"pr:{repository_id}:{number}:close")))
    else:
        rows.append(_row((PR_REOPEN, f"pr:{repository_id}:{number}:reopen")))
    rows.append(_row((PR_BACK, f"repo:{repository_id}:pulls")))
    return InlineKeyboardMarkup(rows)

def pull_request_text(item: dict):
    title = escape(item.get("title", "Pull request"))
    number = item.get("number", "?")
    state = escape(item.get("state", "unknown"))
    draft = " · draft" if item.get("draft") else ""
    user = escape(item.get("user", {}).get("login", "unknown"))
    base = escape(item.get("base", {}).get("ref", "?"))
    head = escape(item.get("head", {}).get("ref", "?"))
    body = escape(item.get("body") or "")
    lines = [f"<b>#{number} {title}</b>", f"<code>{state}{draft}</code>", "", f"{head} → {base}", f"by <code>{user}</code>"]
    if body:
        lines.extend(["", body[:2500]])
    stats = []
    if item.get("changed_files") is not None:
        stats.append(f"files {item['changed_files']}")
    if item.get("additions") is not None:
        stats.append(f"+{item['additions']}")
    if item.get("deletions") is not None:
        stats.append(f"-{item['deletions']}")
    if stats:
        lines.extend(["", " · ".join(stats)])
    return "\n".join(lines)

def pull_request_files_text(items):
    if not items:
        return f"<b>{PR_FILES}</b>\n\n{EMPTY}"
    lines = [f"<b>{PR_FILES}</b>"]
    for item in items[:30]:
        lines.append(f"\n<code>{escape(item.get('filename', 'file'))}</code> · +{item.get('additions', 0)} -{item.get('deletions', 0)}")
    return "".join(lines)

def pull_request_commits_text(items):
    if not items:
        return f"<b>{PR_COMMITS}</b>\n\n{EMPTY}"
    lines = [f"<b>{PR_COMMITS}</b>"]
    for item in items[:30]:
        sha = escape(item.get("sha", "")[:10])
        message = escape((item.get("commit", {}).get("message") or "commit").split("\n", 1)[0])
        lines.append(f"\n<code>{sha}</code> {message[:100]}")
    return "".join(lines)

def pull_request_reviews_text(items):
    if not items:
        return f"<b>{PR_REVIEWS}</b>\n\n{EMPTY}"
    lines = [f"<b>{PR_REVIEWS}</b>"]
    for item in items[-30:]:
        user = escape(item.get("user", {}).get("login", "unknown"))
        state = escape(item.get("state", "PENDING"))
        body = escape(item.get("body") or "")
        lines.append(f"\n<b>{user}</b> · <code>{state}</code>")
        if body:
            lines.append(f"\n{body[:500]}")
    return "".join(lines)


def pull_request_list_text(repository: str):
    return f"<b>{escape(repository)}</b>\n\n{PR_LIST}"


def actions_home(repository_id: int):
    return InlineKeyboardMarkup([
        _row((ACTION_WORKFLOWS, f"actions:{repository_id}:workflows"), (ACTION_RUNS, f"actions:{repository_id}:runs")),
        _row((ACTION_ARTIFACTS, f"actions:{repository_id}:artifacts")),
        _row((ACTION_BACK, f"repo:{repository_id}")),
    ])

def action_workflows(items, repository_id: int):
    rows = []
    for item in items[:20]:
        workflow_id = item.get("id")
        name = escape(item.get("name", item.get("path", "workflow")))[:48]
        state = escape(item.get("state", "unknown"))
        rows.append(_row((f"{name} · {state}", f"workflow:{repository_id}:{workflow_id}")))
    rows.append(_row((ACTION_BACK, f"repo:{repository_id}:actions")))
    return InlineKeyboardMarkup(rows)

def action_runs(items, repository_id: int):
    rows = []
    for item in items[:20]:
        run_id = item.get("id")
        name = escape(item.get("name", "workflow"))[:34]
        status = escape(item.get("conclusion") or item.get("status", "unknown"))
        rows.append(_row((f"{name} · {status}", f"run:{repository_id}:{run_id}")))
    rows.append(_row((ACTION_BACK, f"repo:{repository_id}:actions")))
    return InlineKeyboardMarkup(rows)

def action_run_view(repository_id: int, run_id: int, status: str, conclusion: str | None):
    active = status in {"queued", "in_progress", "waiting", "requested", "pending"}
    rows = [
        _row((ACTION_REFRESH, f"run:{repository_id}:{run_id}:refresh")),
        _row((ACTION_JOBS, f"run:{repository_id}:{run_id}:jobs"), (ACTION_ARTIFACTS, f"run:{repository_id}:{run_id}:artifacts")),
        _row((ACTION_RERUN_FAILED, f"run:{repository_id}:{run_id}:rerun_failed"), (ACTION_RERUN, f"run:{repository_id}:{run_id}:rerun")),
    ]
    if active:
        rows.append(_row((ACTION_CANCEL, f"run:{repository_id}:{run_id}:cancel")))
    rows.append(_row((ACTION_BACK, f"repo:{repository_id}:actions")))
    return InlineKeyboardMarkup(rows)

def action_jobs(items, repository_id: int, run_id: int):
    rows = []
    for item in items[:20]:
        job_id = item.get("id")
        name = escape(item.get("name", "job"))[:52]
        status = escape(item.get("conclusion") or item.get("status", "unknown"))
        rows.append(_row((f"{name} · {status}", f"job:{repository_id}:{run_id}:{job_id}")))
    rows.append(_row((ACTION_BACK, f"run:{repository_id}:{run_id}")))
    return InlineKeyboardMarkup(rows)

def action_job_view(repository_id: int, run_id: int, job_id: int):
    return InlineKeyboardMarkup([
        _row((ACTION_STEPS, f"job:{repository_id}:{run_id}:{job_id}:steps"), (ACTION_LOGS, f"job:{repository_id}:{run_id}:{job_id}:logs")),
        _row((ACTION_BACK, f"run:{repository_id}:{run_id}:jobs")),
    ])

def action_artifacts(items, repository_id: int, run_id: int | None = None):
    rows = []
    for item in items[:20]:
        name = escape(item.get("name", "artifact"))[:52]
        artifact_id = item.get("id")
        rows.append(_row((f"{name} · {item.get('size_in_bytes', 0)} bytes", f"artifact:{repository_id}:{run_id}:{artifact_id}" if run_id else f"artifact:{repository_id}:{artifact_id}")))
    target = f"run:{repository_id}:{run_id}" if run_id else f"repo:{repository_id}:actions"
    rows.append(_row((ACTION_BACK, target)))
    return InlineKeyboardMarkup(rows)

def actions_text(repository: str):
    return f"<b>{escape(repository)}</b>\n\n{ACTIONS_TITLE}"

def workflow_text(item: dict):
    return f"<b>{escape(item.get('name', 'Workflow'))}</b>\n\n<code>{escape(item.get('state', 'unknown'))}</code>\n<code>{escape(item.get('path', ''))}</code>"

def workflow_actions(repository_id: int, workflow_id: int, runs, include_run: bool = True):
    rows = []
    if include_run:
        rows.append(_row((ACTION_RUN, f"workflow:{repository_id}:{workflow_id}:run")))
    for item in runs[:20]:
        run_id = item.get("id")
        name = escape(item.get("name", "workflow"))[:34]
        status = escape(item.get("conclusion") or item.get("status", "unknown"))
        rows.append(_row((f"{name} · {status}", f"run:{repository_id}:{run_id}")))
    rows.append(_row((ACTION_BACK, f"repo:{repository_id}:actions")))
    return InlineKeyboardMarkup(rows)

def run_text(item: dict):
    name = escape(item.get('name', 'Workflow run'))
    status = escape(item.get('conclusion') or item.get('status', 'unknown'))
    branch = escape(item.get('head_branch') or '-')
    actor = escape(item.get('actor', {}).get('login', 'unknown'))
    sha = escape(item.get('head_sha', '')[:10])
    return f"<b>{name}</b>\n\n<code>{status}</code> · <code>{branch}</code>\nby <code>{actor}</code>\n<code>{sha}</code>"

def job_text(item: dict):
    name = escape(item.get('name', 'Job'))
    status = escape(item.get('conclusion') or item.get('status', 'unknown'))
    return f"<b>{name}</b>\n\n<code>{status}</code>"

def artifact_text(item: dict):
    name = escape(item.get('name', 'Artifact'))
    size = item.get('size_in_bytes', 0)
    expired = "expired" if item.get('expired') else "available"
    return f"<b>{name}</b>\n\n<code>{size} bytes</code> · {expired}"

def action_logs_text(name: str, content: str):
    return f"<b>{escape(name)}</b>\n\n<pre>{escape(content[-3500:])}</pre>"


def stage_actions(token: str):
    return InlineKeyboardMarkup([_row((COMMIT_STAGED, f"stage:{token}:commit"), (CLEAR_STAGED, f"stage:{token}:clear"))])

def staged_text(repository: str, branch: str, changes):
    lines = [f"<b>{escape(repository)}</b> · <code>{escape(branch)}</code>", "", f"<b>{STAGED}</b>"]
    if not changes:
        return "\n".join(lines + [STAGED_EMPTY])
    for change in changes[:50]:
        marker = {"added": "+", "modified": "~", "deleted": "-"}.get(change.status, "~")
        lines.append(f"<code>{marker}</code> {escape(change.path)}")
    lines.extend(["", f"<b>{len(changes)}</b> {STAGED_COUNT}", "", f"<b>{COMMIT_STAGED}</b>"])
    return "\n".join(lines)


DIFF_TITLE = "Changes"
DIFF_EMPTY = "No diff available."
DIFF_BINARY = "Binary file"
DIFF_NO_PATCH = "No textual patch available."
DIFF_PREVIOUS = "Previous"
DIFF_NEXT = "Next"
DIFF_BACK = "Back to PR"
DIFF_COMMENT = "Comment on file"
DIFF_TRUNCATED = "Diff truncated for Telegram."

def pull_request_diff_text(item: dict, index: int, total: int):
    filename = escape(item.get("filename", "file"))
    status = escape(item.get("status", "modified"))
    additions = item.get("additions", 0)
    deletions = item.get("deletions", 0)
    patch = item.get("patch")
    header = f"<b>{DIFF_TITLE} · {index + 1}/{total}</b>\n\n<code>{filename}</code>\n{status} · +{additions} -{deletions}"
    if item.get("previous_filename"):
        header += f"\nfrom <code>{escape(item['previous_filename'])}</code>"
    if item.get("binary"):
        return header + f"\n\n{DIFF_BINARY}"
    if not patch:
        return header + f"\n\n{DIFF_NO_PATCH}"
    body = escape(patch[-3000:])
    return header + f"\n\n<pre>{body}</pre>"

def pull_request_diff_actions(repository_id: int, number: int, index: int, total: int):
    row = []
    if index > 0:
        row.append(InlineKeyboardButton(DIFF_PREVIOUS, callback_data=f"diff:{repository_id}:{number}:{index - 1}"))
    if index + 1 < total:
        row.append(InlineKeyboardButton(DIFF_NEXT, callback_data=f"diff:{repository_id}:{number}:{index + 1}"))
    rows = [row] if row else []
    rows.append(_row((DIFF_BACK, f"pr:{repository_id}:{number}")))
    return InlineKeyboardMarkup(rows)
