from typing import Any
import httpx

API = "https://api.github.com"

class GitHubClient:
    def __init__(self, token: str):
        self.token = token

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.token}", "X-GitHub-Api-Version": "2026-03-10"}
        async with httpx.AsyncClient(base_url=API, timeout=30) as client:
            response = await client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
