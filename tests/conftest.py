from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

import pgembed
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from jarvis.bootstrap import bootstrap_foundation
from jarvis.core.security import TokenSecurity
from jarvis.core.settings import Settings
from jarvis.db.session import create_database_engine, create_session_factory, session_scope
from jarvis.identity.schemas import WorkspaceCreate
from jarvis.identity.service import (
    create_user_with_identity,
    create_workspace,
    issue_session,
)
from jarvis.knowledge.service import create_workspace_namespace
from jarvis.platform.models import WorkspacePreferences
from jarvis_api.main import create_app
from psycopg import sql
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True, slots=True)
class DatabaseHarness:
    url: str
    owner_url: str
    engine: Engine
    owner_engine: Engine
    factory: sessionmaker[Session]
    owner_factory: sessionmaker[Session]
    runtime_role: str


@dataclass(frozen=True, slots=True)
class UserContext:
    user_id: UUID
    workspace_id: UUID
    raw_session_token: str
    session_id: UUID
    csrf_token: str


@dataclass(frozen=True, slots=True)
class ExternalPostgresServer:
    uri: str

    def get_uri(self) -> str:
        return self.uri


@pytest.fixture(scope="session")
def postgres_server(tmp_path_factory: pytest.TempPathFactory):
    external_uri = os.getenv("JARVIS_TEST_DATABASE_URL")
    if external_uri:
        yield ExternalPostgresServer(external_uri)
        return
    pgdata = tmp_path_factory.mktemp("pgembed") / "data"
    server = pgembed.get_server(pgdata, cleanup_mode="delete")
    server.ensure_postgres_running()
    yield server
    server.cleanup()


@pytest.fixture
def database(postgres_server) -> Iterator[DatabaseHarness]:
    database_name = f"jarvis_test_{uuid4().hex}"
    admin_uri = postgres_server.get_uri()
    with psycopg.connect(admin_uri, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    database_uri = admin_uri.rsplit("/", 1)[0] + f"/{database_name}"
    owner_url = database_uri.replace("postgresql://", "postgresql+psycopg://")
    alembic_config = Config(str(Path("alembic.ini").resolve()))
    alembic_config.set_main_option("sqlalchemy.url", owner_url)
    command.upgrade(alembic_config, "head")

    runtime_role = f"jarvis_test_runtime_{uuid4().hex}"
    runtime_password = uuid4().hex
    with psycopg.connect(database_uri, autocommit=True) as connection:
        connection.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                "NOCREATEROLE NOINHERIT NOBYPASSRLS"
            ).format(
                sql.Identifier(runtime_role),
                sql.Literal(runtime_password),
            )
        )
        connection.execute(sql.SQL("GRANT jarvis_app TO {}").format(sql.Identifier(runtime_role)))

    parsed = urlsplit(database_uri)
    runtime_uri = urlunsplit(
        (
            parsed.scheme,
            f"{runtime_role}:{runtime_password}@{parsed.hostname}:{parsed.port}",
            parsed.path,
            "",
            "",
        )
    )
    runtime_url = runtime_uri.replace("postgresql://", "postgresql+psycopg://")
    owner_engine = create_database_engine(owner_url)
    owner_factory = create_session_factory(owner_engine)
    with session_scope(owner_factory) as session:
        bootstrap_foundation(session)

    engine = create_database_engine(runtime_url)
    factory = create_session_factory(engine)
    harness = DatabaseHarness(
        url=runtime_url,
        owner_url=owner_url,
        engine=engine,
        owner_engine=owner_engine,
        factory=factory,
        owner_factory=owner_factory,
        runtime_role=runtime_role,
    )
    yield harness

    engine.dispose()
    owner_engine.dispose()
    with psycopg.connect(admin_uri, autocommit=True) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
        )
        connection.execute(
            sql.SQL("REVOKE jarvis_app FROM {}").format(sql.Identifier(runtime_role))
        )
        connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(runtime_role)))


@pytest.fixture
def settings(database: DatabaseHarness) -> Settings:
    return Settings(
        environment="test",
        database_url=database.url,
        session_hmac_key="test-session-hmac-key-that-is-long-enough",
        session_hmac_key_version="test-v1",
        web_origin="http://testserver",
    )


@pytest.fixture
def app(database: DatabaseHarness, settings: Settings):
    return create_app(settings, engine=database.engine)


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client


@pytest.fixture
def create_user_context(database: DatabaseHarness, settings: Settings):
    security = TokenSecurity(settings)

    def factory(name: str) -> UserContext:
        slug = name.lower().replace(" ", "-")
        with session_scope(database.owner_factory) as session:
            user = create_user_with_identity(
                session,
                issuer="https://issuer.test",
                subject=f"subject-{slug}",
                email=f"{slug}@example.test",
                display_name=name,
            )
            workspace = create_workspace(
                session,
                actor_id=user.id,
                data=WorkspaceCreate(
                    name=f"{name} Workspace",
                    slug=f"{slug}-{uuid4().hex[:8]}",
                    kind="personal",
                ),
            )
            create_workspace_namespace(
                session,
                workspace_id=workspace.id,
                workspace_slug=workspace.slug,
                workspace_name=workspace.name,
            )
            session.add(WorkspacePreferences(workspace_id=workspace.id, values={}, lock_version=1))
            user_session, raw_token = issue_session(
                session,
                user_id=user.id,
                settings=settings,
                security=security,
            )
            session.flush()
            return UserContext(
                user_id=user.id,
                workspace_id=workspace.id,
                raw_session_token=raw_token,
                session_id=user_session.id,
                csrf_token=security.csrf_token(user_session.id),
            )

    return factory


def authenticate_client(
    client: TestClient,
    settings: Settings,
    context: UserContext,
) -> dict[str, str]:
    client.cookies.set(
        settings.effective_session_cookie_name,
        context.raw_session_token,
    )
    return {
        "Origin": settings.web_origin,
        "X-CSRF-Token": context.csrf_token,
    }
