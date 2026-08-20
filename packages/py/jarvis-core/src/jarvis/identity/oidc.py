from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry
from sqlalchemy import text, update
from sqlalchemy.orm import Session

from jarvis.core.errors import AuthenticationError, ConfigurationError
from jarvis.core.security import TokenSecurity
from jarvis.core.settings import Settings
from jarvis.db.session import set_actor_context
from jarvis.identity.models import OIDCLoginTransaction
from jarvis.identity.service import issue_session


@dataclass(frozen=True, slots=True)
class OIDCLoginStart:
    authorization_url: str
    binding_token: str


@dataclass(frozen=True, slots=True)
class ConsumedOIDCLogin:
    transaction_id: UUID
    issuer: str
    verifier: str
    expected_nonce: str
    return_path: str


@dataclass(frozen=True, slots=True)
class OIDCLoginResult:
    user_id: UUID
    session_id: UUID
    raw_session_token: str
    return_path: str


@dataclass(frozen=True, slots=True)
class ValidatedOIDCIdentity:
    issuer: str
    subject: str
    email: str
    display_name: str
    auth_time: datetime
    mfa_context: str
    return_path: str


class OIDCService:
    def __init__(self, settings: Settings, security: TokenSecurity) -> None:
        self._settings = settings
        self._security = security

    def start_login(self, session: Session, *, return_path: str = "/") -> OIDCLoginStart:
        issuer, client_id, authorization_endpoint, _, _ = self._configuration()
        if return_path not in self._settings.oidc_allowed_return_paths:
            raise AuthenticationError("Invalid post-login return path.")

        transaction_id = uuid4()
        state = self._security.random_token(32)
        binding_token = self._security.random_token(32)
        verifier = secrets.token_urlsafe(64)
        nonce = self._security.random_token(32)
        now = datetime.now(UTC)
        transaction = OIDCLoginTransaction(
            id=transaction_id,
            issuer=issuer,
            state_digest=self._security.digest(state, purpose="oidc-state"),
            binding_digest=self._security.digest(binding_token, purpose="oidc-binding"),
            verifier_ciphertext=self._security.encrypt(
                verifier,
                associated_data=f"oidc-login:{transaction_id}:verifier",
            ),
            nonce_ciphertext=self._security.encrypt(
                nonce,
                associated_data=f"oidc-login:{transaction_id}:nonce",
            ),
            return_path=return_path,
            created_at=now,
            expires_at=now + timedelta(minutes=10),
        )
        session.add(transaction)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
            .decode("ascii")
            .rstrip("=")
        )
        query = urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": self._settings.oidc_redirect_uri,
                "scope": "openid profile email",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return OIDCLoginStart(
            authorization_url=f"{authorization_endpoint}?{query}",
            binding_token=binding_token,
        )

    def consume_login(
        self,
        session: Session,
        *,
        state: str,
        binding_token: str,
    ) -> ConsumedOIDCLogin:
        issuer, _, _, _, _ = self._configuration()
        now = datetime.now(UTC)
        row = session.execute(
            update(OIDCLoginTransaction)
            .where(
                OIDCLoginTransaction.state_digest
                == self._security.digest(state, purpose="oidc-state"),
                OIDCLoginTransaction.binding_digest
                == self._security.digest(binding_token, purpose="oidc-binding"),
                OIDCLoginTransaction.consumed_at.is_(None),
                OIDCLoginTransaction.expires_at > now,
                OIDCLoginTransaction.issuer == issuer,
            )
            .values(consumed_at=now)
            .returning(
                OIDCLoginTransaction.id,
                OIDCLoginTransaction.issuer,
                OIDCLoginTransaction.verifier_ciphertext,
                OIDCLoginTransaction.nonce_ciphertext,
                OIDCLoginTransaction.return_path,
            )
        ).one_or_none()
        if row is None:
            raise AuthenticationError("OIDC login state is invalid or expired.")
        verifier = self._security.decrypt(
            row[2],
            associated_data=f"oidc-login:{row[0]}:verifier",
        )
        expected_nonce = self._security.decrypt(
            row[3],
            associated_data=f"oidc-login:{row[0]}:nonce",
        )
        return ConsumedOIDCLogin(
            transaction_id=row[0],
            issuer=row[1],
            verifier=verifier,
            expected_nonce=expected_nonce,
            return_path=row[4],
        )

    def validate_login(
        self,
        *,
        consumed: ConsumedOIDCLogin,
        code: str,
        client: httpx.Client | None = None,
    ) -> ValidatedOIDCIdentity:
        issuer, client_id, _, token_endpoint, jwks_uri = self._configuration()
        if consumed.issuer != issuer:
            raise AuthenticationError("OIDC issuer changed during login.")

        owns_client = client is None
        http = client or httpx.Client(timeout=15)
        try:
            response = http.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": self._settings.oidc_client_secret,
                    "redirect_uri": self._settings.oidc_redirect_uri,
                    "code_verifier": consumed.verifier,
                },
            )
            response.raise_for_status()
            token_payload = response.json()
            jwks_response = http.get(jwks_uri)
            jwks_response.raise_for_status()
            token = jwt.decode(
                token_payload["id_token"],
                KeySet.import_key_set(jwks_response.json()),
            )
            if token.header.get("alg") not in {"RS256", "ES256"}:
                raise AuthenticationError("OIDC signing algorithm is not allowed.")
            claims = cast(dict[str, object], token.claims)
            claims_registry = JWTClaimsRegistry(
                leeway=30,
                iss={"essential": True, "value": issuer},
                aud={"essential": True, "values": [client_id]},
                exp={"essential": True},
                iat={"essential": True},
                auth_time={"essential": True},
                nonce={"essential": True, "value": consumed.expected_nonce},
                sub={"essential": True},
            )
            claims_registry.validate(claims)
        except (httpx.HTTPError, KeyError, ValueError, JoseError) as exc:
            raise AuthenticationError("OIDC token validation failed.") from exc
        finally:
            if owns_client:
                http.close()

        subject = str(claims["sub"])
        if subject != self._settings.oidc_owner_subject:
            raise AuthenticationError("This identity is not invited to JARVIS.")
        audience = claims.get("aud")
        authorized_party = claims.get("azp")
        if authorized_party is not None and authorized_party != client_id:
            raise AuthenticationError("OIDC authorized party is invalid.")
        if isinstance(audience, list):
            audience_values = cast(list[object], audience)
            if len(audience_values) > 1 and authorized_party != client_id:
                raise AuthenticationError("OIDC authorized party is required for this audience.")
        email = str(claims.get("email") or "")
        if not email:
            raise AuthenticationError("OIDC identity did not provide an email address.")
        display_name = str(claims.get("name") or email)
        auth_time_claim = claims["auth_time"]
        if not isinstance(auth_time_claim, int | str):
            raise AuthenticationError("OIDC authentication time is invalid.")
        auth_time = datetime.fromtimestamp(int(auth_time_claim), UTC)
        now = datetime.now(UTC)
        if auth_time > now + timedelta(seconds=60) or (now - auth_time) > timedelta(
            seconds=self._settings.oidc_max_auth_age_seconds
        ):
            raise AuthenticationError("OIDC authentication is too old or in the future.")
        amr = claims.get("amr", [])
        if not isinstance(amr, list):
            raise AuthenticationError("OIDC authentication methods are invalid.")
        amr_values = {str(item) for item in cast(list[object], amr)}
        if not set(self._settings.oidc_required_amr).issubset(amr_values):
            raise AuthenticationError("Required multi-factor authentication was not present.")
        return ValidatedOIDCIdentity(
            issuer=issuer,
            subject=subject,
            email=email,
            display_name=display_name,
            auth_time=auth_time,
            mfa_context=",".join(sorted(amr_values)),
            return_path=consumed.return_path,
        )

    def finish_login(
        self,
        session: Session,
        *,
        identity: ValidatedOIDCIdentity,
    ) -> OIDCLoginResult:
        user_id = session.scalar(
            text(
                """
                SELECT identity.provision_oidc_user(
                    :issuer, :subject, :email, :display_name
                )
                """
            ),
            {
                "issuer": identity.issuer,
                "subject": identity.subject,
                "email": identity.email,
                "display_name": identity.display_name,
            },
        )
        if not isinstance(user_id, UUID):
            raise RuntimeError("OIDC provisioning did not return a user ID")
        set_actor_context(session, user_id)
        user_session, raw_token = issue_session(
            session,
            user_id=user_id,
            settings=self._settings,
            security=self._security,
            auth_time=identity.auth_time,
            mfa_context=identity.mfa_context,
            rotate_existing=True,
        )
        return OIDCLoginResult(
            user_id=user_id,
            session_id=user_session.id,
            raw_session_token=raw_token,
            return_path=identity.return_path,
        )

    def _require_configured(self) -> None:
        if not self._settings.oidc_configured:
            raise ConfigurationError("OIDC authentication is not configured.")

    def _configuration(self) -> tuple[str, str, str, str, str]:
        self._require_configured()
        issuer = self._settings.oidc_issuer
        client_id = self._settings.oidc_client_id
        authorization_endpoint = self._settings.oidc_authorization_endpoint
        token_endpoint = self._settings.oidc_token_endpoint
        jwks_uri = self._settings.oidc_jwks_uri
        assert issuer is not None
        assert client_id is not None
        assert authorization_endpoint is not None
        assert token_endpoint is not None
        assert jwks_uri is not None
        return issuer, client_id, authorization_endpoint, token_endpoint, jwks_uri
