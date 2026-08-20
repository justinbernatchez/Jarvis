from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from jarvis.core.settings import Settings


class TokenSecurity:
    def __init__(self, settings: Settings) -> None:
        self._hmac_key = settings.session_hmac_key.encode("utf-8")
        self._encryption_key = base64.urlsafe_b64decode(settings.fernet_key)

    @staticmethod
    def random_token(byte_count: int = 48) -> str:
        return secrets.token_urlsafe(byte_count)

    def digest(self, value: str, *, purpose: str) -> str:
        message = f"{purpose}:{value}".encode()
        return hmac.new(self._hmac_key, message, hashlib.sha256).hexdigest()

    def verify_digest(self, value: str, expected: str, *, purpose: str) -> bool:
        return hmac.compare_digest(self.digest(value, purpose=purpose), expected)

    def csrf_token(self, session_id: UUID) -> str:
        message = f"csrf:{session_id}".encode()
        digest = hmac.new(self._hmac_key, message, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    def encrypt(self, value: str, *, associated_data: str) -> str:
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self._encryption_key).encrypt(
            nonce,
            value.encode("utf-8"),
            associated_data.encode("utf-8"),
        )
        return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, value: str, *, associated_data: str) -> str:
        payload = base64.urlsafe_b64decode(value.encode("ascii"))
        plaintext = AESGCM(self._encryption_key).decrypt(
            payload[:12],
            payload[12:],
            associated_data.encode("utf-8"),
        )
        return plaintext.decode("utf-8")
