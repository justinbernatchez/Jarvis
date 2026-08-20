from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from jarvis.core.errors import AuthenticationError
from jarvis.core.security import TokenSecurity
from jarvis.core.settings import Settings
from jarvis.db.session import session_scope
from jarvis.identity.models import UserSession, WorkspaceMembership
from jarvis.identity.oidc import OIDCService
from jarvis.identity.service import issue_session
from jarvis_api.main import create_app
from jarvis_api.routers.auth import ensure_personal_workspace
from joserfc import jwt
from joserfc.jwk import RSAKey
from pydantic import ValidationError
from sqlalchemy import select

from tests.conftest import authenticate_client


def test_server_session_csrf_origin_and_revocation(
    client,
    settings,
    create_user_context,
) -> None:
    context = create_user_context("Session User")
    headers = authenticate_client(client, settings, context)

    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is True
    assert session.json()["csrfToken"] == context.csrf_token

    missing_origin = client.post(
        "/api/v1/workspaces",
        headers={"X-CSRF-Token": context.csrf_token},
        json={"name": "Blocked", "slug": "blocked", "kind": "personal"},
    )
    assert missing_origin.status_code == 403
    assert missing_origin.json()["code"] == "authorization.origin"

    missing_csrf = client.post(
        "/api/v1/workspaces",
        headers={"Origin": settings.web_origin},
        json={"name": "Blocked", "slug": "blocked-two", "kind": "personal"},
    )
    assert missing_csrf.status_code == 422

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204
    client.cookies.set(
        settings.effective_session_cookie_name,
        context.raw_session_token,
    )
    assert client.get("/api/v1/auth/session").status_code == 401


def test_oidc_login_fails_closed_when_not_configured(client) -> None:
    response = client.get("/api/v1/auth/login", follow_redirects=False)
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "configuration.invalid"


def test_security_settings_reject_invalid_keys_and_open_oidc_registration() -> None:
    with pytest.raises(ValidationError):
        Settings(token_encryption_key="not-valid-base64")

    encryption_key = base64.urlsafe_b64encode(b"x" * 32).decode("ascii")
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            session_hmac_key="production-session-hmac-key-that-is-long-enough",
            token_encryption_key=encryption_key,
            web_origin="https://jarvis.example",
            oidc_issuer="https://issuer.example",
            oidc_client_id="jarvis-client",
            oidc_authorization_endpoint="https://issuer.example/authorize",
            oidc_token_endpoint="https://issuer.example/token",
            oidc_jwks_uri="https://issuer.example/jwks",
            oidc_owner_subject=None,
        )


def test_production_oidc_binding_cookie_security_flags(database) -> None:
    settings = Settings(
        environment="production",
        database_url=database.url,
        migration_database_url=database.owner_url,
        session_hmac_key="production-cookie-hmac-key-that-is-long-enough",
        token_encryption_key=base64.urlsafe_b64encode(b"x" * 32).decode("ascii"),
        web_origin="https://jarvis.example",
        oidc_issuer="https://issuer.example",
        oidc_client_id="jarvis-client",
        oidc_client_secret="client-secret",
        oidc_authorization_endpoint="https://issuer.example/authorize",
        oidc_token_endpoint="https://issuer.example/token",
        oidc_jwks_uri="https://issuer.example/jwks",
        oidc_redirect_uri="https://jarvis.example/api/v1/auth/callback",
        oidc_owner_subject="subject-owner",
    )
    app = create_app(settings, engine=database.engine)
    with TestClient(app, base_url="https://jarvis.example") as production_client:
        response = production_client.get(
            "/api/v1/auth/login",
            follow_redirects=False,
        )
    assert response.status_code == 302
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("__Host-jarvis_oidc_binding=")
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie


def test_oidc_pkce_state_claims_and_single_use_transaction(database) -> None:
    settings = Settings(
        environment="test",
        database_url=database.url,
        session_hmac_key="oidc-session-hmac-key-that-is-long-enough",
        oidc_issuer="https://issuer.example",
        oidc_client_id="jarvis-client",
        oidc_client_secret="client-secret",
        oidc_authorization_endpoint="https://issuer.example/authorize",
        oidc_token_endpoint="https://issuer.example/token",
        oidc_jwks_uri="https://issuer.example/jwks",
        oidc_redirect_uri="http://testserver/api/v1/auth/callback",
        oidc_owner_subject="subject-owner",
    )
    security = TokenSecurity(settings)
    service = OIDCService(settings, security)
    with pytest.raises(AuthenticationError), session_scope(database.owner_factory) as session:
        service.start_login(session, return_path="/%09/evil.example")
    with session_scope(database.owner_factory) as session:
        started = service.start_login(session, return_path="/")
    query = parse_qs(urlparse(started.authorization_url).query)
    state = query["state"][0]
    nonce = query["nonce"][0]
    assert query["code_challenge_method"] == ["S256"]

    key = RSAKey.generate_key(2048)
    public_key = key.as_dict(private=False)
    public_key.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
    now = datetime.now(UTC)
    id_token = jwt.encode(
        {"alg": "RS256", "kid": "test-key"},
        {
            "iss": settings.oidc_issuer,
            "aud": settings.oidc_client_id,
            "sub": settings.oidc_owner_subject,
            "email": "owner@example.test",
            "name": "Owner",
            "nonce": nonce,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "auth_time": int(now.timestamp()),
            "amr": ["pwd", "mfa"],
        },
        key,
    )

    def oidc_transport(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(200, json={"id_token": id_token})
        if request.url.path == "/jwks":
            return httpx.Response(200, json={"keys": [public_key]})
        return httpx.Response(404)

    with pytest.raises(AuthenticationError), session_scope(database.owner_factory) as session:
        service.consume_login(
            session,
            state=state,
            binding_token="binding-from-another-browser",
        )

    with httpx.Client(transport=httpx.MockTransport(oidc_transport)) as http_client:
        with session_scope(database.owner_factory) as session:
            consumed = service.consume_login(
                session,
                state=state,
                binding_token=started.binding_token,
            )
        identity = service.validate_login(
            consumed=consumed,
            code="authorization-code",
            client=http_client,
        )
        with session_scope(database.owner_factory) as session:
            result = service.finish_login(
                session,
                identity=identity,
            )
            assert result.raw_session_token
            assert result.return_path == "/"
            ensure_personal_workspace(
                session,
                user_id=result.user_id,
                request_id="oidc-test",
            )

        with session_scope(database.owner_factory) as session:
            workspace_id = session.scalar(
                select(WorkspaceMembership.workspace_id).where(
                    WorkspaceMembership.user_id == result.user_id
                )
            )
            assert workspace_id is not None
            rotated_session, _ = issue_session(
                session,
                user_id=result.user_id,
                settings=settings,
                security=security,
                rotate_existing=True,
            )
            session.flush()
            prior_session = session.get(UserSession, result.session_id)
            assert prior_session is not None
            assert prior_session.revoked_at is not None
            assert rotated_session.revoked_at is None

        with pytest.raises(AuthenticationError), session_scope(database.owner_factory) as session:
            service.consume_login(
                session,
                state=state,
                binding_token=started.binding_token,
            )

    with session_scope(database.owner_factory) as session:
        retry_started = service.start_login(session, return_path="/")
    retry_state = parse_qs(urlparse(retry_started.authorization_url).query)["state"][0]
    with session_scope(database.owner_factory) as session:
        retry_consumed = service.consume_login(
            session,
            state=retry_state,
            binding_token=retry_started.binding_token,
        )
    failing_client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(503))
    )
    with (
        failing_client,
        pytest.raises(AuthenticationError),
    ):
        service.validate_login(
            consumed=retry_consumed,
            code="failed-code",
            client=failing_client,
        )
    with pytest.raises(AuthenticationError), session_scope(database.owner_factory) as session:
        service.consume_login(
            session,
            state=retry_state,
            binding_token=retry_started.binding_token,
        )

    with session_scope(database.owner_factory) as session:
        concurrent_started = service.start_login(session, return_path="/")
    concurrent_state = parse_qs(urlparse(concurrent_started.authorization_url).query)["state"][0]
    barrier = Barrier(2)

    def consume_concurrently() -> bool:
        barrier.wait()
        try:
            with session_scope(database.owner_factory) as session:
                service.consume_login(
                    session,
                    state=concurrent_state,
                    binding_token=concurrent_started.binding_token,
                )
            return True
        except AuthenticationError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: consume_concurrently(), range(2)))
    assert sorted(results) == [False, True]

    with session_scope(database.owner_factory) as session:
        mfa_started = service.start_login(session, return_path="/")
    mfa_query = parse_qs(urlparse(mfa_started.authorization_url).query)
    mfa_token = jwt.encode(
        {"alg": "RS256", "kid": "test-key"},
        {
            "iss": settings.oidc_issuer,
            "aud": settings.oidc_client_id,
            "sub": settings.oidc_owner_subject,
            "email": "owner@example.test",
            "name": "Owner",
            "nonce": mfa_query["nonce"][0],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "auth_time": int(now.timestamp()),
            "amr": ["pwd"],
        },
        key,
    )

    def missing_mfa_transport(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(200, json={"id_token": mfa_token})
        return httpx.Response(200, json={"keys": [public_key]})

    with session_scope(database.owner_factory) as session:
        mfa_consumed = service.consume_login(
            session,
            state=mfa_query["state"][0],
            binding_token=mfa_started.binding_token,
        )
    with (
        httpx.Client(transport=httpx.MockTransport(missing_mfa_transport)) as missing_mfa_client,
        pytest.raises(AuthenticationError),
    ):
        service.validate_login(
            consumed=mfa_consumed,
            code="authorization-code",
            client=missing_mfa_client,
        )


@pytest.mark.parametrize(
    "claim_overrides",
    [
        {"sub": "uninvited-subject"},
        {"iss": "https://wrong-issuer.example"},
        {"aud": "wrong-client"},
        {"nonce": "wrong-nonce"},
        {"auth_time": 0},
        {"auth_time": 4_102_444_800},
        {"aud": ["jarvis-client", "another-client"]},
        {
            "aud": ["jarvis-client", "another-client"],
            "azp": "another-client",
        },
    ],
)
def test_oidc_rejects_invalid_identity_claims(database, claim_overrides) -> None:
    settings = Settings(
        environment="test",
        database_url=database.url,
        session_hmac_key="oidc-negative-hmac-key-that-is-long-enough",
        oidc_issuer="https://issuer.example",
        oidc_client_id="jarvis-client",
        oidc_client_secret="client-secret",
        oidc_authorization_endpoint="https://issuer.example/authorize",
        oidc_token_endpoint="https://issuer.example/token",
        oidc_jwks_uri="https://issuer.example/jwks",
        oidc_redirect_uri="http://testserver/api/v1/auth/callback",
        oidc_owner_subject="subject-owner",
    )
    service = OIDCService(settings, TokenSecurity(settings))
    with session_scope(database.owner_factory) as session:
        started = service.start_login(session, return_path="/")
    query = parse_qs(urlparse(started.authorization_url).query)
    now = datetime.now(UTC)
    claims = {
        "iss": settings.oidc_issuer,
        "aud": settings.oidc_client_id,
        "sub": settings.oidc_owner_subject,
        "email": "owner@example.test",
        "name": "Owner",
        "nonce": query["nonce"][0],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "auth_time": int(now.timestamp()),
        "amr": ["pwd", "mfa"],
    }
    claims.update(claim_overrides)
    key = RSAKey.generate_key(2048)
    public_key = key.as_dict(private=False)
    public_key.update({"kid": "negative-key", "alg": "RS256", "use": "sig"})
    id_token = jwt.encode(
        {"alg": "RS256", "kid": "negative-key"},
        claims,
        key,
    )

    def transport(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(200, json={"id_token": id_token})
        return httpx.Response(200, json={"keys": [public_key]})

    with session_scope(database.owner_factory) as session:
        consumed = service.consume_login(
            session,
            state=query["state"][0],
            binding_token=started.binding_token,
        )
    with (
        httpx.Client(transport=httpx.MockTransport(transport)) as client,
        pytest.raises(AuthenticationError),
    ):
        service.validate_login(
            consumed=consumed,
            code="authorization-code",
            client=client,
        )
