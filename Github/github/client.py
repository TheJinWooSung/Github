from typing import Any
import asyncio
import os
import httpx

API = "https://api.github.com"
API_VERSION = "2026-03-10"

class GitHubClient:
    def __init__(self, token: str, timeout: float | None = None, base_url: str | None = None, api_version: str | None = None):
        self.token = token
        self.timeout = timeout if timeout is not None else float(os.getenv("GITHUB_REQUEST_TIMEOUT", "30"))
        self.base_url = (base_url or os.getenv("GITHUB_API_URL") or API).rstrip("/")
        self.api_version = api_version or os.getenv("GITHUB_API_VERSION") or API_VERSION
        self._lock = asyncio.Lock()

    def headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": self.api_version,
            "User-Agent": "GitHub-for-Telegram",
        }
        if extra:
            headers.update(extra)
        return headers

    async def _request(self, method: str, path: str, text: bool = False, **kwargs: Any):
        if not self.token:
            raise RuntimeError("GitHub authentication token is not configured")
        supplied = kwargs.pop("headers", None)
        headers = self.headers(supplied)
        retryable = method.upper() in {"GET", "HEAD", "OPTIONS"}
        last_error = None
        for attempt in range(3):
            try:
                async with self._lock:
                    async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, follow_redirects=True) as client:
                        response = await client.request(method, path, headers=headers, **kwargs)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteError, httpx.ReadError) as exc:
                last_error = exc
                if not retryable or attempt == 2:
                    raise RuntimeError(f"GitHub connection failed: {exc}") from exc
                await asyncio.sleep(0.5 * (2 ** attempt))
                continue
            if retryable and response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 0.5 * (2 ** attempt)
                except ValueError:
                    delay = 0.5 * (2 ** attempt)
                await asyncio.sleep(min(delay, 30.0))
                continue
            break
        if last_error:
            raise RuntimeError(f"GitHub connection failed: {last_error}") from last_error
        if response.status_code == 204:
            return None
        if response.status_code == 401:
            raise RuntimeError("GitHub authentication failed")
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            retry = response.headers.get("Retry-After") or response.headers.get("X-RateLimit-Reset")
            raise RuntimeError(f"GitHub API rate limit reached{f'; retry {retry}' if retry else ''}")
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {"message": response.text}
            message = payload.get("message", response.text) if isinstance(payload, dict) else response.text
            raise RuntimeError(f"GitHub API error {response.status_code}: {message}")
        return response.text if text else response.json()

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        return await self._request(method, path, **kwargs)

    async def request_text(self, method: str, path: str, **kwargs: Any) -> str:
        return await self._request(method, path, text=True, **kwargs)

    async def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.token:
            raise RuntimeError("GitHub authentication token is not configured")
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        async with self._lock:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                response = await client.post("/graphql", headers=self.headers(), json=payload)
        if response.status_code >= 400:
            try:
                data = response.json()
                message = data.get("message", response.text) if isinstance(data, dict) else response.text
            except ValueError:
                message = response.text
            raise RuntimeError(f"GitHub GraphQL error {response.status_code}: {message}")
        data = response.json()
        if data.get("errors"):
            messages = "; ".join(str(item.get("message", "GraphQL error")) for item in data["errors"])
            raise RuntimeError(messages)
        return data.get("data") or {}

    async def close(self):
        return None
