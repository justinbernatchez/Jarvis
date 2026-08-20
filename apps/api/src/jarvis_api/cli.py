from __future__ import annotations

import uvicorn
from jarvis.bootstrap import bootstrap_foundation
from jarvis.core.settings import get_settings
from jarvis.db.session import create_database_engine, create_session_factory, session_scope


def serve() -> None:
    uvicorn.run(
        "jarvis_api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=get_settings().environment == "development",
    )


def bootstrap() -> None:
    engine = create_database_engine(get_settings().migration_database_url)
    factory = create_session_factory(engine)
    with session_scope(factory) as session:
        bootstrap_foundation(session)
    print("JARVIS foundation bootstrap complete.")
