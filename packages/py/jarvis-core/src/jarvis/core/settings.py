from __future__ import annotations

import base64
import binascii
import hashlib
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="JARVIS_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = (
        "postgresql+psycopg://jarvis_runtime:jarvis_runtime_dev_only@localhost:5432/jarvis"
    )
    migration_database_url: str = (
        "postgresql+psycopg://jarvis_owner:jarvis_dev_only@localhost:5432/jarvis"
    )
    session_hmac_key: str = Field(
        default="development-only-change-me-32-characters",
        min_length=32,
    )
    session_hmac_key_version: str = "v1"
    token_encryption_key: str | None = None
    web_origin: str = "http://localhost:5173"
    session_cookie_name: str = "__Host-jarvis_session"
    session_ttl_seconds: int = 60 * 60 * 12

    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_authorization_endpoint: str | None = None
    oidc_token_endpoint: str | None = None
    oidc_jwks_uri: str | None = None
    oidc_redirect_uri: str = "http://localhost:8000/api/v1/auth/callback"
    oidc_owner_subject: str | None = None
    oidc_required_amr: tuple[str, ...] = ("mfa",)
    oidc_max_auth_age_seconds: int = 3600
    oidc_allowed_return_paths: tuple[str, ...] = ("/", "/example")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Settings:
        if self.environment in {"staging", "production"}:
            if self.session_hmac_key.startswith("development-only"):
                raise ValueError("A production session HMAC key is required")
            if not self.token_encryption_key:
                raise ValueError("A production token encryption key is required")
            if not self.web_origin.startswith("https://"):
                raise ValueError("Production web origin must use HTTPS")
        if self.oidc_configured and not self.oidc_owner_subject:
            raise ValueError("Configured OIDC requires an owner subject allowlist")
        if self.token_encryption_key:
            try:
                decoded = base64.urlsafe_b64decode(self.token_encryption_key.encode("ascii"))
            except (ValueError, binascii.Error) as exc:
                raise ValueError("Token encryption key must be URL-safe base64") from exc
            if len(decoded) != 32:
                raise ValueError("Token encryption key must decode to exactly 32 bytes")
        return self

    @property
    def secure_cookies(self) -> bool:
        return self.environment in {"staging", "production"}

    @property
    def effective_session_cookie_name(self) -> str:
        if self.secure_cookies:
            return self.session_cookie_name
        return "jarvis_session"

    @property
    def effective_oidc_binding_cookie_name(self) -> str:
        if self.secure_cookies:
            return "__Host-jarvis_oidc_binding"
        return "jarvis_oidc_binding"

    @property
    def fernet_key(self) -> bytes:
        if self.token_encryption_key:
            return self.token_encryption_key.encode("ascii")
        digest = hashlib.sha256(self.session_hmac_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    @property
    def oidc_configured(self) -> bool:
        return all(
            (
                self.oidc_issuer,
                self.oidc_client_id,
                self.oidc_authorization_endpoint,
                self.oidc_token_endpoint,
                self.oidc_jwks_uri,
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
