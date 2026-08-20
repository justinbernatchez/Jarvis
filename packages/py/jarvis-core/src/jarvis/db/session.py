from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    return create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def assume_application_role(session: Session) -> None:
    session.execute(text("SET LOCAL ROLE jarvis_app"))


def set_actor_context(session: Session, user_id: UUID, session_id: UUID | None = None) -> None:
    session.execute(
        text("SELECT set_config('app.user_id', :value, true)"),
        {"value": str(user_id)},
    )
    session.execute(
        text("SELECT set_config('app.session_id', :value, true)"),
        {"value": str(session_id) if session_id else ""},
    )


def set_workspace_context(session: Session, workspace_id: UUID) -> None:
    session.execute(
        text("SELECT set_config('app.workspace_id', :value, true)"),
        {"value": str(workspace_id)},
    )


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Generator[Session]:
    session = factory()
    try:
        with session.begin():
            yield session
    finally:
        session.close()
