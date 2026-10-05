from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _text(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if value is None or not value.strip():
        if required:
            raise RuntimeError(f"Missing environment variable: {name}")
        return ""
    return value.strip()


def _int(name: str, default: int | None = None, *, minimum: int | None = None, required: bool = False) -> int:
    raw = os.getenv(name)
    if not raw or not raw.strip():
        if default is None:
            if required:
                raise RuntimeError(f"Missing environment variable: {name}")
            raise RuntimeError(f"Missing integer configuration: {name}")
        value = default
    else:
        try:
            value = int(raw.strip())
        except ValueError as exc:
            raise RuntimeError(f"{name} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    return value


def _optional_int(name: str) -> int | None:
    raw = os.getenv(name)
    if not raw or not raw.strip():
        return None
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _url(name: str, value: str, *, https: bool = False) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(f"{name} must be a valid HTTP(S) URL")
    if https and parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError(f"{name} must use HTTPS")
    return value.rstrip("/")


def _private_key() -> str:
    inline = os.getenv("GITHUB_PRIVATE_KEY")
    path = os.getenv("GITHUB_PRIVATE_KEY_FILE")
    if inline and path:
        raise RuntimeError("Set only one of GITHUB_PRIVATE_KEY or GITHUB_PRIVATE_KEY_FILE")
    if path:
        try:
            value = Path(path).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Unable to read GITHUB_PRIVATE_KEY_FILE: {path}") from exc
    elif inline:
        value = inline
    else:
        raise RuntimeError("Missing GitHub App private key: GITHUB_PRIVATE_KEY or GITHUB_PRIVATE_KEY_FILE")
    value = value.replace("\\n", "\n").strip()
    if "BEGIN" not in value or "PRIVATE KEY" not in value or "END" not in value:
        raise RuntimeError("GITHUB_PRIVATE_KEY must contain a valid PEM private key")
    return value


def _fernet_key() -> str:
    value = _text("TOKEN_ENCRYPTION_KEY", required=True)
    try:
        Fernet(value.encode())
    except Exception as exc:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from exc
    return value


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    api_id: int
    api_hash: str
    mongo_uri: str
    github_app_id: int
    github_installation_id: int
    github_private_key: str
    github_client_id: str
    github_client_secret: str
    github_webhook_secret: str
    webhook_url: str
    token_encryption_key: str
    redis_url: str | None
    log_chat_id: int | None
    host: str
    port: int
    environment: str
    github_api_url: str
    github_api_version: str
    request_timeout: float
    bot_session_name: str
    webhook_path: str
    oauth_callback_path: str
    notifications_enabled: bool

    @classmethod
    def from_env(cls) -> "Config":
        webhook_url = _url("WEBHOOK_URL", _text("WEBHOOK_URL", required=True), https=True)
        environment = _text("ENVIRONMENT", "production").lower()
        if environment not in {"development", "staging", "production", "test"}:
            raise RuntimeError("ENVIRONMENT must be development, staging, production, or test")
        raw_timeout = _text("GITHUB_REQUEST_TIMEOUT", "30")
        try:
            request_timeout = float(raw_timeout)
        except ValueError as exc:
            raise RuntimeError("GITHUB_REQUEST_TIMEOUT must be a number") from exc
        if request_timeout <= 0:
            raise RuntimeError("GITHUB_REQUEST_TIMEOUT must be greater than 0")
        raw_notifications = _text("NOTIFICATIONS_ENABLED", "true").lower()
        if raw_notifications not in _TRUE | _FALSE:
            raise RuntimeError("NOTIFICATIONS_ENABLED must be a boolean")
        return cls(
            bot_token=_text("BOT_TOKEN", required=True),
            api_id=_int("API_ID", minimum=1, required=True),
            api_hash=_text("API_HASH", required=True),
            mongo_uri=_text("MONGO_URI", required=True),
            github_app_id=_int("GITHUB_APP_ID", minimum=1, required=True),
            github_installation_id=_int("GITHUB_INSTALLATION_ID", minimum=1, required=True),
            github_private_key=_private_key(),
            github_client_id=_text("GITHUB_CLIENT_ID", required=True),
            github_client_secret=_text("GITHUB_CLIENT_SECRET", required=True),
            github_webhook_secret=_text("GITHUB_WEBHOOK_SECRET", required=True),
            webhook_url=webhook_url,
            token_encryption_key=_fernet_key(),
            redis_url=_text("REDIS_URL") or None,
            log_chat_id=_optional_int("LOG_CHAT_ID"),
            host=_text("HOST", "0.0.0.0"),
            port=_int("PORT", 8000, minimum=1),
            environment=environment,
            github_api_url=_url("GITHUB_API_URL", _text("GITHUB_API_URL", "https://api.github.com")),
            github_api_version=_text("GITHUB_API_VERSION", "2026-03-10"),
            request_timeout=request_timeout,
            bot_session_name=_text("BOT_SESSION_NAME", "github_control_center"),
            webhook_path="/" + _text("WEBHOOK_PATH", "webhooks/github").strip("/"),
            oauth_callback_path="/" + _text("OAUTH_CALLBACK_PATH", "oauth/callback").strip("/"),
            notifications_enabled=raw_notifications in _TRUE,
        )
