from typing import Any, AsyncIterator
from .client import GitHubClient

class RepositoryService:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def get(self, owner: str, name: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}")

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

    async def issues(self, owner: str, name: str, state: str = "open", page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/issues", params={"state": state, "page": page, "per_page": min(per_page, 100)})

    async def pull_requests(self, owner: str, name: str, state: str = "open", page: int = 1, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/pulls", params={"state": state, "page": page, "per_page": min(per_page, 100)})

    async def pull_request(self, owner: str, name: str, number: int) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/pulls/{number}")

    async def workflows(self, owner: str, name: str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/workflows")

    async def workflow_runs(self, owner: str, name: str, page: int = 1, per_page: int = 30) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/runs", params={"page": page, "per_page": min(per_page, 100)})

    async def workflow(self, owner: str, name: str, workflow_id: int | str) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/workflows/{workflow_id}")

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
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/jobs/{job_id}/logs")

    async def artifacts(self, owner: str, name: str, page: int = 1, per_page: int = 30) -> dict[str, Any]:
        return await self.client.request("GET", f"/repos/{owner}/{name}/actions/artifacts", params={"page": page, "per_page": min(per_page, 100)})

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
