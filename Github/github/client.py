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

    def headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": API_VERSION,
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
        async with self._lock:
            async with httpx.AsyncClient(base_url=API, timeout=self.timeout, follow_redirects=True) as client:
                response = await client.request(method, path, headers=headers, **kwargs)
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

    async def close(self):
        return None
