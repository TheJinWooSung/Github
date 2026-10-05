import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode
import httpx

@dataclass(frozen=True)
class OAuthGrant:
    access_token: str
    refresh_token: str | None
    expires_in: int | None
    refresh_token_expires_in: int | None
    scope: str

class GitHubOAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, timeout: float = 30, api_version: str = "2026-03-10"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.timeout = timeout
        self.api_version = api_version

    def begin(self) -> tuple[str, str, str]:
        state = secrets.token_urlsafe(32)
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        query = urlencode({"client_id": self.client_id, "redirect_uri": self.redirect_uri, "state": state, "code_challenge": challenge, "code_challenge_method": "S256", "scope": "repo read:user user:email offline_access", "prompt": "select_account"})
        return state, f"https://github.com/login/oauth/authorize?{query}", verifier

    async def exchange(self, code: str, verifier: str) -> OAuthGrant:
        payload = {"client_id": self.client_id, "client_secret": self.client_secret, "code": code, "redirect_uri": self.redirect_uri, "code_verifier": verifier}
        headers = {"Accept": "application/json", "X-GitHub-Api-Version": self.api_version}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post("https://github.com/login/oauth/access_token", data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        if not data.get("access_token"):
            raise RuntimeError(data.get("error_description") or data.get("error") or "GitHub authorization failed")
        return OAuthGrant(data["access_token"], data.get("refresh_token"), data.get("expires_in"), data.get("refresh_token_expires_in"), data.get("scope", ""))

    async def user(self, token: str) -> dict:
        headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": self.api_version}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get("https://api.github.com/user", headers=headers)
            response.raise_for_status()
            return response.json()

    async def revoke(self, access_token: str) -> None:
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": self.api_version}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request("DELETE", f"https://api.github.com/applications/{self.client_id}/token", auth=auth, headers=headers, json={"access_token": access_token})
        if response.status_code not in {204, 404}:
            response.raise_for_status()

    async def refresh(self, refresh_token: str) -> OAuthGrant:
        payload = {"client_id": self.client_id, "client_secret": self.client_secret, "grant_type": "refresh_token", "refresh_token": refresh_token}
        headers = {"Accept": "application/json", "X-GitHub-Api-Version": self.api_version}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post("https://github.com/login/oauth/access_token", data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        if not data.get("access_token"):
            raise RuntimeError(data.get("error_description") or data.get("error") or "GitHub token refresh failed")
        return OAuthGrant(data["access_token"], data.get("refresh_token"), data.get("expires_in"), data.get("refresh_token_expires_in"), data.get("scope", ""))
