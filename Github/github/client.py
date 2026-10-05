from typing import Any
import asyncio
import httpx

API = "https://api.github.com"
API_VERSION = "2026-03-10"

class GitHubClient:
    def __init__(self, token: str, timeout: float = 30):
        self.token = token
        self.timeout = timeout
        self._lock = asyncio.Lock()

    def headers(self) -> dict[str, str]:
        return {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.token}", "X-GitHub-Api-Version": API_VERSION}

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.token:
            raise RuntimeError("GitHub authentication token is not configured")
        async with self._lock:
            async with httpx.AsyncClient(base_url=API, timeout=self.timeout) as client:
                response = await client.request(method, path, headers=self.headers(), **kwargs)
        if response.status_code == 204:
            return None
        if response.status_code == 401:
            raise RuntimeError("GitHub authentication failed")
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise RuntimeError("GitHub API rate limit reached")
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {"message": response.text}
            message = payload.get("message", response.text) if isinstance(payload, dict) else response.text
            raise RuntimeError(f"GitHub API error {response.status_code}: {message}")
        return response.json()

    async def request_text(self, method: str, path: str, **kwargs: Any) -> str:
        if not self.token:
            raise RuntimeError("GitHub authentication token is not configured")
        async with self._lock:
            async with httpx.AsyncClient(base_url=API, timeout=self.timeout, follow_redirects=True) as client:
                response = await client.request(method, path, headers=self.headers(), **kwargs)
        if response.status_code >= 400:
            try:
                payload = response.json()
                message = payload.get("message", response.text) if isinstance(payload, dict) else response.text
            except ValueError:
                message = response.text
            raise RuntimeError(f"GitHub API error {response.status_code}: {message}")
        return response.text

    async def close(self):
        return None
