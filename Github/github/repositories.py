from typing import Any, AsyncIterator
from .client import GitHubClient

class RepositoryService:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def get(self, owner: str, name: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}")

    async def get_by_id(self, repository_id: int) -> dict[str, Any]:
        return await self.client.request("GET", f"/repositories/{repository_id}")

    async def list_for_user(self, username: str | None = None, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        path = f"/users/{username}/repos" if username else "/user/repos"
        return await self.client.request("GET", path, params={"page": page, "per_page": min(per_page, 100), "sort": "updated"})

    async def list_for_org(self, org: str, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/orgs/{org}/repos", params={"page": page, "per_page": min(per_page, 100), "sort": "updated"})

    async def search(self, query: str, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        return await self.client.request("GET", "/search/repositories", params={"q": query, "page": page, "per_page": min(per_page, 100)})

    async def branches(self, owner: str, name: str, page: int = 1, per_page: int = 100) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/branches", params={"page": page, "per_page": min(per_page, 100)})

    async def branch(self, owner: str, name: str, branch: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/branches/{branch}")

    async def tags(self, owner: str, name: str, page: int = 1, per_page: int = 100) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/tags", params={"page": page, "per_page": min(per_page, 100)})

    async def contributors(self, owner: str, name: str, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/contributors", params={"page": page, "per_page": min(per_page, 100)})

    async def releases(self, owner: str, name: str, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/releases", params={"page": page, "per_page": min(per_page, 100)})

    async def release(self, owner: str, name: str, release_id: int) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/releases/{release_id}")

    async def deployments(self, owner: str, name: str, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/deployments", params={"page": page, "per_page": min(per_page, 100)})

    async def commits(self, owner: str, name: str, sha: str | None = None, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page": page, "per_page": min(per_page, 100)}
        if sha:
            params["sha"] = sha
        return await self.client.request("GET", f"/repos/{owner}/{name}/commits", params=params)

    async def commit(self, owner: str, name: str, sha: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/commits/{sha}")

    async def compare(self, owner: str, name: str, base: str, head: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/compare/{base}...{head}")

    async def contents(self, owner: str, name: str, path: str = "", ref: str | None = None) -> Any:
        params = {"ref": ref} if ref else None
        return await self.client.request("GET", f"/repos/{owner}/{name}/contents/{path}" if path else f"/repos/{owner}/{name}/contents", params=params)

    async def file(self, owner: str, name: str, path: str, ref: str | None = None) -> dict[str, Any]:
        result = await self.contents(owner, name, path, ref)
        if not isinstance(result, dict):
            raise ValueError("Requested path is not a file")
        return result

    async def blob(self, owner: str, name: str, sha: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/git/blobs/{sha}")

    async def branch_head(self, owner: str, name: str, branch: str) -> str:
        result = await self.ref(owner, name, f"heads/{branch}")
        return result["object"]["sha"]

    async def tree(self, owner: str, name: str, tree_sha: str, recursive: bool = True) -> dict[str, Any]:
        suffix = "?recursive=1" if recursive else ""
        return await self.client.request("GET", f"/repos/{owner}/{name}/git/trees/{tree_sha}{suffix}")

    async def ref(self, owner: str, name: str, ref: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/git/ref/{ref}")

    async def create_branch(self, owner: str, name: str, branch: str, source_sha: str) -> dict[str, Any]:
        return await self.client.request("POST", f"/repos/{owner}/{name}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": source_sha})

    async def update_branch(self, owner: str, name: str, branch: str, sha: str, force: bool = False) -> dict[str, Any]:
        return await self.client.request("PATCH", f"/repos/{owner}/{name}/git/refs/heads/{branch}", json={"sha": sha, "force": force})

    async def delete_branch(self, owner: str, name: str, branch: str) -> Any:
        return await self.client.request("DELETE", f"/repos/{owner}/{name}/git/refs/heads/{branch}")

    async def create_blob(self, owner: str, name: str, content: str, encoding: str = "utf-8") -> dict[str, Any]:
        return await self.client.request("POST", f"/repos/{owner}/{name}/git/blobs", json={"content": content, "encoding": encoding})

    async def create_tree(self, owner: str, name: str, tree: list[dict[str, Any]], base_tree: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"tree": tree}
        if base_tree:
            payload["base_tree"] = base_tree
        return await self.client.request("POST", f"/repos/{owner}/{name}/git/trees", json=payload)

    async def create_commit(self, owner: str, name: str, message: str, tree: str, parents: list[str]) -> dict[str, Any]:
        return await self.client.request("POST", f"/repos/{owner}/{name}/git/commits", json={"message": message, "tree": tree, "parents": parents})

    async def get_user(self) -> dict[str, Any]:
        return await self.client.request("GET", "/user")

    async def starred(self, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", "/user/starred", params={"page": page, "per_page": min(per_page, 100)})

    async def star(self, owner: str, name: str) -> Any:
        return await self.client.request("PUT", f"/user/starred/{owner}/{name}")

    async def unstar(self, owner: str, name: str) -> Any:
        return await self.client.request("DELETE", f"/user/starred/{owner}/{name}")

    async def watching(self, owner: str, name: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/subscription")

    async def watch(self, owner: str, name: str, subscribed: bool = True, ignored: bool = False) -> dict[str, Any]:
        return await self.client.request("PUT", f"/repos/{owner}/{name}/subscription", json={"subscribed": subscribed, "ignored": ignored})

    async def topics(self, owner: str, name: str) -> list[str]:
        result = await self.client.request("GET", f"/repos/{owner}/{name}/topics")
        return result.get("names", [])

    async def update_topics(self, owner: str, name: str, names: list[str]) -> dict[str, Any]:
        return await self.client.request("PUT", f"/repos/{owner}/{name}/topics", json={"names": names})

    async def labels(self, owner: str, name: str, page: int = 1, per_page: int = 100) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/labels", params={"page": page, "per_page": min(per_page, 100)})

    async def issue_comment(self, owner: str, name: str, number: int, body: str):
        return await self.client.request("POST", f"/repos/{owner}/{name}/issues/{number}/comments", json={"body": body})

    async def create_webhook(self, owner: str, name: str, url: str, secret: str, events: list[str]):
        return await self.client.request("POST", f"/repos/{owner}/{name}/hooks", json={"name": "web", "active": True, "events": events, "config": {"url": url, "content_type": "json", "secret": secret, "insecure_ssl": "0"}})

    async def webhook(self, owner: str, name: str, hook_id: int) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/hooks/{hook_id}")

    async def update_webhook(self, owner: str, name: str, hook_id: int, *, events: list[str] | None = None, active: bool | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if events is not None:
            payload["events"] = events
        if active is not None:
            payload["active"] = active
        return await self.client.request("PATCH", f"/repos/{owner}/{name}/hooks/{hook_id}", json=payload)

    async def webhook_deliveries(self, owner: str, name: str, hook_id: int, page: int = 1, per_page: int = 30, status: str | None = None) -> list[dict[str, Any]]:\n        params: dict[str, Any] = {"page": page, "per_page": min(per_page, 100)}\n        if status in {"success", "failure"}:\n            params["status"] = status\n        return await self.client.request("GET", f"/repos/{owner}/{name}/hooks/{hook_id}/deliveries", params=params)\n\n    async def webhook_delivery(self, owner: str, name: str, hook_id: int, delivery_id: str) -> dict[str, Any]:\n        return await self.client.request("GET", f"/repos/{owner}/{name}/hooks/{hook_id}/deliveries/{delivery_id}")\n\n    async def redeliver_webhook(self, owner: str, name: str, hook_id: int, delivery_id: str):
        return await self.client.request("POST", f"/repos/{owner}/{name}/hooks/{hook_id}/deliveries/{delivery_id}/attempts")

    async def delete_webhook(self, owner: str, name: str, hook_id: int):
        return await self.client.request("DELETE", f"/repos/{owner}/{name}/hooks/{hook_id}")

    async def issues(self, owner: str, name: str, state: str = "open", page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/issues", params={"state": state, "page": page, "per_page": min(per_page, 100)})

    async def pull_requests(self, owner: str, name: str, state: str = "open", page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/pulls", params={"state": state, "page": page, "per_page": min(per_page, 100)})

    async def pull_request(self, owner: str, name: str, number: int) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/pulls/{number}")


    async def create_pull_request(self, owner: str, name: str, title: str, head: str, base: str, body: str = "", draft: bool = False) -> dict[str, Any]:
        return await self.client.request("POST", f"/repos/{owner}/{name}/pulls", json={"title": title, "head": head, "base": base, "body": body, "draft": draft})

    async def update_pull_request(self, owner: str, name: str, number: int, **fields: Any) -> dict[str, Any]:
        allowed = {"title", "body", "state", "base", "maintainer_can_modify", "draft"}
        payload = {key: value for key, value in fields.items() if key in allowed and value is not None}
        return await self.client.request("PATCH", f"/repos/{owner}/{name}/pulls/{number}", json=payload)

    async def merge_pull_request(self, owner: str, name: str, number: int, method: str = "merge", expected_head_sha: str | None = None) -> dict[str, Any]:
        payload = {"merge_method": method}
        if expected_head_sha:
            payload["sha"] = expected_head_sha
        return await self.client.request("PUT", f"/repos/{owner}/{name}/pulls/{number}/merge", json=payload)

    async def pull_request_files(self, owner: str, name: str, number: int, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/pulls/{number}/files", params={"page": page, "per_page": min(per_page, 100)})

    async def pull_request_commits(self, owner: str, name: str, number: int, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/pulls/{number}/commits", params={"page": page, "per_page": min(per_page, 100)})

    async def pull_request_reviews(self, owner: str, name: str, number: int, page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/pulls/{number}/reviews", params={"page": page, "per_page": min(per_page, 100)})

    async def mergeable_pull_request(self, owner: str, name: str, number: int) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/pulls/{number}")

    async def pull_request_diff(self, owner: str, name: str, number: int) -> str:
        return await self.client.request_text("GET", f"/repos/{owner}/{name}/pulls/{number}", headers={"Accept": "application/vnd.github.diff"})

    async def request_reviewers(self, owner: str, name: str, number: int, reviewers: list[str] | None = None, team_reviewers: list[str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if reviewers:
            payload["reviewers"] = reviewers
        if team_reviewers:
            payload["team_reviewers"] = team_reviewers
        return await self.client.request("POST", f"/repos/{owner}/{name}/pulls/{number}/requested_reviewers", json=payload)

    async def requested_reviewers(self, owner: str, name: str, number: int) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/pulls/{number}/requested_reviewers")

    async def submit_review(self, owner: str, name: str, number: int, event: str, body: str = "") -> dict[str, Any]:
        payload = {"event": event}
        if body:
            payload["body"] = body
        return await self.client.request("POST", f"/repos/{owner}/{name}/pulls/{number}/reviews", json=payload)

    async def workflows(self, owner: str, name: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/workflows")

    async def workflow_runs(self, owner: str, name: str, page: int = 1, per_page: int = 30) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/runs", params={"page": page, "per_page": min(per_page, 100)})

    async def workflow(self, owner: str, name: str, workflow_id: int | str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/workflows/{workflow_id}")

    async def workflow_run(self, owner: str, name: str, run_id: int) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/runs/{run_id}")

    async def workflow_runs_for(self, owner: str, name: str, workflow_id: int | str, page: int = 1, per_page: int = 30) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/workflows/{workflow_id}/runs", params={"page": page, "per_page": min(per_page, 100)})

    async def run_workflow(self, owner: str, name: str, workflow_id: int | str, ref: str, inputs: dict[str, Any] | None = None) -> Any:
        payload = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs
        return await self.client.request("POST", f"/repos/{owner}/{name}/actions/workflows/{workflow_id}/dispatches", json=payload)

    async def cancel_run(self, owner: str, name: str, run_id: int) -> Any:
        return await self.client.request("POST", f"/repos/{owner}/{name}/actions/runs/{run_id}/cancel")

    async def rerun(self, owner: str, name: str, run_id: int, failed_only: bool = False) -> Any:
        action = "rerun-failed-jobs" if failed_only else "rerun"
        return await self.client.request("POST", f"/repos/{owner}/{name}/actions/runs/{run_id}/{action}")

    async def jobs(self, owner: str, name: str, run_id: int, page: int = 1, per_page: int = 100) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/runs/{run_id}/jobs", params={"page": page, "per_page": min(per_page, 100)})

    async def job_logs(self, owner: str, name: str, job_id: int) -> str:
        return await self.client.request_text("GET", f"/repos/{owner}/{name}/actions/jobs/{job_id}/logs")

    async def artifacts(self, owner: str, name: str, page: int = 1, per_page: int = 30) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/artifacts", params={"page": page, "per_page": min(per_page, 100)})

    async def run_artifacts(self, owner: str, name: str, run_id: int, page: int = 1, per_page: int = 30) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/runs/{run_id}/artifacts", params={"page": page, "per_page": min(per_page, 100)})

    async def update_repository(self, owner: str, name: str, **fields: Any) -> dict[str, Any]:
        allowed = {"name", "description", "homepage", "private", "has_issues", "has_projects", "has_wiki", "is_template", "default_branch", "allow_squash_merge", "allow_merge_commit", "allow_rebase_merge", "delete_branch_on_merge", "allow_auto_merge", "archived"}
        payload = {key: value for key, value in fields.items() if key in allowed and value is not None}
        return await self.client.request("PATCH", f"/repos/{owner}/{name}", json=payload)

    async def fork(self, owner: str, name: str, organization: str | None = None, repository: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if organization:
            payload["organization"] = organization
        if repository:
            payload["name"] = repository
        return await self.client.request("POST", f"/repos/{owner}/{name}/forks", json=payload)

    async def languages(self, owner: str, name: str) -> dict[str, int]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/languages")

    async def create_issue(self, owner: str, name: str, title: str, body: str = "", **fields: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        for key in ("assignees", "milestone", "labels"):
            if fields.get(key) is not None:
                payload[key] = fields[key]
        return await self.client.request("POST", f"/repos/{owner}/{name}/issues", json=payload)

    async def update_issue(self, owner: str, name: str, number: int, **fields: Any) -> dict[str, Any]:
        allowed = {"title", "body", "state", "state_reason", "milestone", "labels", "assignees", "locked"}
        payload = {key: value for key, value in fields.items() if key in allowed and value is not None}
        return await self.client.request("PATCH", f"/repos/{owner}/{name}/issues/{number}", json=payload)

    async def issue(self, owner: str, name: str, number: int) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/issues/{number}")

    async def add_assignees(self, owner: str, name: str, number: int, assignees: list[str]) -> dict[str, Any]:
        return await self.client.request("POST", f"/repos/{owner}/{name}/issues/{number}/assignees", json={"assignees": assignees})

    async def remove_assignees(self, owner: str, name: str, number: int, assignees: list[str]) -> dict[str, Any]:
        return await self.client.request("DELETE", f"/repos/{owner}/{name}/issues/{number}/assignees", json={"assignees": assignees})

    async def issue_labels(self, owner: str, name: str, number: int) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/issues/{number}/labels")

    async def set_issue_labels(self, owner: str, name: str, number: int, labels: list[str]) -> list[dict[str, Any]]:
        return await self.client.request("PUT", f"/repos/{owner}/{name}/issues/{number}/labels", json={"labels": labels})

    async def remove_issue_label(self, owner: str, name: str, number: int, label: str) -> Any:
        return await self.client.request("DELETE", f"/repos/{owner}/{name}/issues/{number}/labels/{label}")

    async def lock_issue(self, owner: str, name: str, number: int, lock_reason: str | None = None) -> Any:
        payload = {"lock_reason": lock_reason} if lock_reason else {}
        return await self.client.request("PUT", f"/repos/{owner}/{name}/issues/{number}/lock", json=payload)

    async def unlock_issue(self, owner: str, name: str, number: int) -> Any:
        return await self.client.request("DELETE", f"/repos/{owner}/{name}/issues/{number}/lock")

    async def search_issues(self, query: str, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        return await self.client.request("GET", "/search/issues", params={"q": query, "page": page, "per_page": min(per_page, 100)})

    async def permissions(self, owner: str, name: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}")

    async def iter_commits(self, owner: str, name: str, sha: str | None = None, per_page: int = 100) -> AsyncIterator[dict[str, Any]]:
        page = 1
        while True:
            items = await self.commits(owner, name, sha, page, per_page)
            if not items:
                return
            for item in items:
                yield item
            if len(items) < per_page:
                return
            page += 1

    async def iter_branches(self, owner: str, name: str, per_page: int = 100) -> AsyncIterator[dict[str, Any]]:
        page = 1
        while True:
            items = await self.branches(owner, name, page, per_page)
            if not items:
                return
            for item in items:
                yield item
            if len(items) < per_page:
                return
            page += 1

    async def iter_repositories(self, username: str, per_page: int = 100) -> AsyncIterator[dict[str, Any]]:
        page = 1
        while True:
            items = await self.list_for_user(username, page, per_page)
            if not items:
                return
            for item in items:
                yield item
            if len(items) < per_page:
                return
            page += 1
