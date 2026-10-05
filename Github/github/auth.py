import time
import jwt
import httpx
from cryptography.hazmat.primitives import serialization

class GitHubAppAuth:
    def __init__(self, app_id: int, private_key: str):
        self.app_id = app_id
        self.private_key = private_key.encode()

    def jwt(self) -> str:
        key = serialization.load_pem_private_key(self.private_key, password=None)
        now = int(time.time())
        return jwt.encode({"iat": now - 30, "exp": now + 540, "iss": self.app_id}, key, algorithm="RS256")

    async def installation_token(self, installation_id: int) -> dict:
        token = self.jwt()
        headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2026-03-10"}
        async with httpx.AsyncClient(base_url="https://api.github.com", timeout=30) as client:
            response = await client.post(f"/app/installations/{installation_id}/access_tokens", headers=headers)
            response.raise_for_status()
            return response.json()
