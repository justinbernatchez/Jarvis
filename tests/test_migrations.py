from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql


def test_complete_migration_chain_is_safe_to_rerun(postgres_server) -> None:
    database_name = f"jarvis_migration_{uuid4().hex}"
    admin_uri = postgres_server.get_uri()
    with psycopg.connect(admin_uri, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    database_uri = admin_uri.rsplit("/", 1)[0] + f"/{database_name}"
    sqlalchemy_url = database_uri.replace("postgresql://", "postgresql+psycopg://")
    config = Config(str(Path("alembic.ini").resolve()))
    config.set_main_option("sqlalchemy.url", sqlalchemy_url)

    command.upgrade(config, "head")
    command.upgrade(config, "head")
    command.check(config)

    with psycopg.connect(database_uri) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        assert revision == ("1c3ae813911b",)
        schemas = {
            row[0]
            for row in connection.execute(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name IN ('identity', 'platform', 'knowledge', 'governance')
                """
            )
        }
        assert schemas == {"identity", "platform", "knowledge", "governance"}
        forced_rls = connection.execute(
            """
            SELECT count(*)
            FROM pg_class table_class
            JOIN pg_namespace namespace ON namespace.oid = table_class.relnamespace
            WHERE namespace.nspname IN ('identity', 'platform', 'knowledge', 'governance')
              AND table_class.relrowsecurity
              AND table_class.relforcerowsecurity
            """
        ).fetchone()
        assert forced_rls is not None
        assert forced_rls[0] >= 15
        app_role = connection.execute(
            "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'jarvis_app'"
        ).fetchone()
        assert app_role == ("jarvis_app", False, False)
        definer_roles = connection.execute(
            """
            SELECT rolname, rolcanlogin, rolbypassrls
            FROM pg_roles
            WHERE rolname IN ('jarvis_rls_definer', 'jarvis_auth_definer')
            ORDER BY rolname
            """
        ).fetchall()
        assert definer_roles == [
            ("jarvis_auth_definer", False, True),
            ("jarvis_rls_definer", False, True),
        ]
        app_members = connection.execute(
            """
            SELECT member.rolname
            FROM pg_auth_members membership
            JOIN pg_roles granted_role ON granted_role.oid = membership.roleid
            JOIN pg_roles member ON member.oid = membership.member
            WHERE granted_role.rolname = 'jarvis_app'
            """
        ).fetchall()
        assert ("postgres",) not in app_members
        function_owners = connection.execute(
            """
            SELECT routine.proname, owner.rolname
            FROM pg_proc routine
            JOIN pg_namespace namespace ON namespace.oid = routine.pronamespace
            JOIN pg_roles owner ON owner.oid = routine.proowner
            WHERE namespace.nspname = 'identity'
              AND routine.proname IN (
                'has_workspace_membership',
                'resolve_session',
                'provision_oidc_user'
              )
            ORDER BY routine.proname
            """
        ).fetchall()
        assert function_owners == [
            ("has_workspace_membership", "jarvis_rls_definer"),
            ("provision_oidc_user", "jarvis_auth_definer"),
            ("resolve_session", "jarvis_rls_definer"),
        ]
        semver_results = connection.execute(
            """
            SELECT
                platform.semver_satisfies('0.1.0', '>=0.1.0,<1.0.0'),
                platform.semver_satisfies('2.0.0', '>=0.1.0,<1.0.0')
            """
        ).fetchone()
        assert semver_results == (True, False)

    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.check(config)

    with psycopg.connect(admin_uri, autocommit=True) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
        )
