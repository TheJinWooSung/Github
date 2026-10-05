import time
import jwt
from cryptography.hazmat.primitives import serialization

class GitHubAppAuth:
    def __init__(self, app_id: int, private_key: str):
        self.app_id = app_id
        self.private_key = private_key.encode()

    def jwt(self) -> str:
        key = serialization.load_pem_private_key(self.private_key, password=None)
        now = int(time.time())
        return jwt.encode({"iat": now - 30, "exp": now + 540, "iss": self.app_id}, key, algorithm="RS256")
