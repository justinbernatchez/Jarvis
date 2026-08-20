from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jarvis.core.security import TokenSecurity
from jarvis.db.session import (
    assume_application_role,
    session_scope,
    set_actor_context,
    set_workspace_context,
)
from jarvis.identity.models import Role, WorkspaceMembership
from jarvis.identity.service import create_user_with_identity, issue_session
from jarvis.knowledge.models import Resource, ResourceNamespace, ResourceType
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from tests.conftest import DatabaseHarness, UserContext, authenticate_client


def _create_resource(
    client: TestClient,
    headers: dict[str, str],
    context: UserContext,
    slug: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{context.workspace_id}/resources",
        headers=headers,
        json={
            "typeKey": "foundation_record",
            "slug": slug,
            "title": f"{slug} title",
            "payload": {"boundary": "private"},
            "confidence": "0.90000",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_two_workspace_api_and_rls_isolation(
    client: TestClient,
    settings,
    database: DatabaseHarness,
    create_user_context,
) -> None:
    user_a = create_user_context("User A")
    user_b = create_user_context("User B")

    headers_a = authenticate_client(client, settings, user_a)
    resource_a = _create_resource(client, headers_a, user_a, "private-a")

    headers_b = authenticate_client(client, settings, user_b)
    resource_b = _create_resource(client, headers_b, user_b, "private-b")

    cross_workspace_api = client.get(
        f"/api/v1/workspaces/{user_b.workspace_id}/resources/{resource_a['id']}",
        headers=headers_b,
    )
    assert cross_workspace_api.status_code == 404

    authenticate_client(client, settings, user_a)
    unauthorized_workspace = client.get(
        f"/api/v1/workspaces/{user_b.workspace_id}/resources",
        headers={"Origin": settings.web_origin},
    )
    assert unauthorized_workspace.status_code == 403
    assert unauthorized_workspace.headers["content-type"].startswith("application/problem+json")
    cross_workspace_write = client.post(
        f"/api/v1/workspaces/{user_b.workspace_id}/resources",
        headers=headers_a,
        json={
            "typeKey": "foundation_record",
            "slug": "forbidden-cross-write",
            "title": "Forbidden",
            "payload": {},
        },
    )
    assert cross_workspace_write.status_code == 403
    cross_workspace_export = client.get(
        f"/api/v1/workspaces/{user_b.workspace_id}/configuration/export"
    )
    assert cross_workspace_export.status_code == 403

    with database.factory() as session, session.begin():
        assume_application_role(session)
        set_actor_context(session, user_a.user_id, user_a.session_id)
        set_workspace_context(session, user_a.workspace_id)
        visible_ids = set(session.scalars(select(Resource.id)))
        assert resource_a["id"] in {str(value) for value in visible_ids}
        assert resource_b["id"] not in {str(value) for value in visible_ids}


def test_system_catalog_is_shared_but_private_resources_are_workspace_owned(
    client: TestClient,
    settings,
    create_user_context,
) -> None:
    user_a = create_user_context("Catalog A")
    user_b = create_user_context("Catalog B")

    headers_a = authenticate_client(client, settings, user_a)
    private = _create_resource(client, headers_a, user_a, "catalog-private-a")
    catalog_a = client.get("/api/v1/catalog/resources")
    assert catalog_a.status_code == 200
    assert any(item["scope"] == "system" for item in catalog_a.json()["items"])

    authenticate_client(client, settings, user_b)
    catalog_b = client.get("/api/v1/catalog/resources")
    assert catalog_b.status_code == 200
    ids_b = {item["id"] for item in catalog_b.json()["items"]}
    assert private["id"] not in ids_b
    assert any(item["scope"] == "system" for item in catalog_b.json()["items"])
    assert private["workspaceId"] == str(user_a.workspace_id)


def test_workspace_role_permission_matrix(
    client: TestClient,
    settings,
    database: DatabaseHarness,
    create_user_context,
) -> None:
    owner = create_user_context("Role Owner")
    owner_headers = authenticate_client(client, settings, owner)
    _create_resource(client, owner_headers, owner, "role-readable")

    security = TokenSecurity(settings)
    with session_scope(database.owner_factory) as session:
        viewer = create_user_with_identity(
            session,
            issuer="https://issuer.test",
            subject="role-viewer",
            email="role-viewer@example.test",
            display_name="Role Viewer",
        )
        viewer_role = session.scalar(select(Role).where(Role.key == "viewer"))
        assert viewer_role is not None
        session.add(
            WorkspaceMembership(
                workspace_id=owner.workspace_id,
                user_id=viewer.id,
                role_id=viewer_role.id,
                status="active",
                joined_at=datetime.now(UTC),
            )
        )
        viewer_session, raw_token = issue_session(
            session,
            user_id=viewer.id,
            settings=settings,
            security=security,
        )
        session.flush()
        viewer_context = UserContext(
            user_id=viewer.id,
            workspace_id=owner.workspace_id,
            raw_session_token=raw_token,
            session_id=viewer_session.id,
            csrf_token=security.csrf_token(viewer_session.id),
        )

    viewer_headers = authenticate_client(client, settings, viewer_context)
    readable = client.get(f"/api/v1/workspaces/{owner.workspace_id}/resources")
    assert readable.status_code == 200
    forbidden_write = client.post(
        f"/api/v1/workspaces/{owner.workspace_id}/resources",
        headers=viewer_headers,
        json={
            "typeKey": "foundation_record",
            "slug": "viewer-cannot-write",
            "title": "Forbidden",
            "payload": {},
        },
    )
    assert forbidden_write.status_code == 403
    forbidden_module = client.post(
        f"/api/v1/workspaces/{owner.workspace_id}/modules/jarvis.example",
        headers=viewer_headers,
        json={"semanticVersion": "0.1.0", "configuration": {}},
    )
    assert forbidden_module.status_code == 403
    assert (
        client.get(f"/api/v1/workspaces/{owner.workspace_id}/configuration/export").status_code
        == 200
    )


def test_runtime_role_requires_explicit_app_role_and_context(
    database: DatabaseHarness,
    create_user_context,
) -> None:
    context = create_user_context("Context User")
    with database.owner_factory() as session:
        runtime_role = session.execute(
            text(
                """
                SELECT rolname, rolsuper, rolbypassrls
                FROM pg_roles
                WHERE rolname = :role_name
                """
            ),
            {"role_name": database.runtime_role},
        ).one()
        assert runtime_role == (database.runtime_role, False, False)
        table_owner = session.scalar(
            text(
                """
                SELECT pg_get_userbyid(table_class.relowner)
                FROM pg_class table_class
                JOIN pg_namespace namespace ON namespace.oid = table_class.relnamespace
                WHERE namespace.nspname = 'knowledge'
                  AND table_class.relname = 'resources'
                """
            )
        )
        assert table_owner != database.runtime_role
        definers = session.execute(
            text(
                """
                SELECT rolname, rolcanlogin, rolbypassrls
                FROM pg_roles
                WHERE rolname IN ('jarvis_rls_definer', 'jarvis_auth_definer')
                ORDER BY rolname
                """
            )
        ).all()
        assert definers == [
            ("jarvis_auth_definer", False, True),
            ("jarvis_rls_definer", False, True),
        ]
    with database.owner_factory() as session, session.begin():
        namespace = session.scalar(
            select(ResourceNamespace).where(
                ResourceNamespace.workspace_id == context.workspace_id,
                ResourceNamespace.is_default.is_(True),
            )
        )
        resource_type = session.scalar(
            select(ResourceType).where(ResourceType.key == "foundation_record")
        )
        assert namespace is not None
        assert resource_type is not None
        private = Resource(
            resource_type_id=resource_type.id,
            namespace_id=namespace.id,
            scope="workspace",
            workspace_id=context.workspace_id,
            slug="context-private",
            title="Context private",
            lifecycle_status="active",
            lock_version=1,
            created_by_user_id=context.user_id,
        )
        session.add(private)
        session.flush()
        private_id = private.id

    with pytest.raises(ProgrammingError), database.factory() as session, session.begin():
        session.scalar(select(Resource.id))

    with database.factory() as session, session.begin():
        assume_application_role(session)
        assert (
            session.scalar(select(Resource.id).where(Resource.workspace_id == context.workspace_id))
            is None
        )
        assert session.scalar(select(Resource.id).where(Resource.scope == "system")) is not None

    with database.factory() as session, session.begin():
        assume_application_role(session)
        set_actor_context(session, uuid4(), uuid4())
        set_workspace_context(session, context.workspace_id)
        assert (
            session.scalar(select(Resource.id).where(Resource.workspace_id == context.workspace_id))
            is None
        )
        assert session.scalar(select(Resource.id).where(Resource.scope == "system")) is not None
        assert session.get(Resource, private_id) is None


def test_composite_foreign_key_rejects_cross_workspace_revision(
    database: DatabaseHarness,
    create_user_context,
) -> None:
    user_a = create_user_context("Foreign Key A")
    user_b = create_user_context("Foreign Key B")

    with database.owner_factory() as session, session.begin():
        private_resource = session.scalar(
            select(Resource).where(Resource.workspace_id == user_a.workspace_id)
        )
        assert private_resource is None

    # Insert a private resource as the owner so this test targets the database
    # composite FK independently from the API/RLS layer.
    with database.owner_factory() as session, session.begin():
        resource_type_id = session.scalar(
            text("SELECT id FROM knowledge.resource_types WHERE key = 'foundation_record'")
        )
        namespace_id = session.scalar(
            text(
                "SELECT id FROM knowledge.resource_namespaces "
                "WHERE workspace_id = :workspace_id AND is_default"
            ),
            {"workspace_id": user_a.workspace_id},
        )
        resource_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO knowledge.resources (
                    id, resource_type_id, namespace_id, scope, workspace_id,
                    slug, title, lifecycle_status, lock_version,
                    created_by_user_id, created_at, updated_at
                ) VALUES (
                    :id, :type_id, :namespace_id, 'workspace', :workspace_id,
                    'fk-proof', 'FK proof', 'active', 1,
                    :actor_id, now(), now()
                )
                """
            ),
            {
                "id": resource_id,
                "type_id": resource_type_id,
                "namespace_id": namespace_id,
                "workspace_id": user_a.workspace_id,
                "actor_id": user_a.user_id,
            },
        )

    with (
        pytest.raises(IntegrityError),
        database.owner_factory() as session,
        session.begin(),
    ):
        session.execute(
            text(
                """
                    INSERT INTO knowledge.resource_revisions (
                        id, resource_id, workspace_id, scope, revision_number,
                        content_hash, payload, authority, source_status,
                        created_by_user_id, created_at, published_at
                    ) VALUES (
                        :id, :resource_id, :wrong_workspace, 'workspace', 1,
                        :content_hash, '{}'::jsonb, 'user', 'user',
                        :actor_id, :now, :now
                    )
                    """
            ),
            {
                "id": uuid4(),
                "resource_id": resource_id,
                "wrong_workspace": user_b.workspace_id,
                "content_hash": "f" * 64,
                "actor_id": user_a.user_id,
                "now": datetime.now(UTC),
            },
        )

    with (
        pytest.raises(IntegrityError),
        database.owner_factory() as session,
        session.begin(),
    ):
        session.execute(
            text(
                """
                INSERT INTO knowledge.resource_revisions (
                    id, resource_id, workspace_id, scope, revision_number,
                    content_hash, payload, authority, source_status,
                    created_by_user_id, created_at, published_at
                ) VALUES (
                    :id, :resource_id, NULL, 'system', 2,
                    :content_hash, '{}'::jsonb, 'system', 'system',
                    NULL, :now, :now
                )
                """
            ),
            {
                "id": uuid4(),
                "resource_id": resource_id,
                "content_hash": "e" * 64,
                "now": datetime.now(UTC),
            },
        )

    with (
        pytest.raises(IntegrityError),
        database.owner_factory() as session,
        session.begin(),
    ):
        session.execute(
            text(
                """
                INSERT INTO knowledge.resources (
                    id, resource_type_id, namespace_id, scope, workspace_id,
                    slug, title, lifecycle_status, lock_version,
                    created_at, updated_at
                ) VALUES (
                    :id, :type_id, :namespace_id, 'system', NULL,
                    'invalid-system-scope', 'Invalid', 'active', 1,
                    now(), now()
                )
                """
            ),
            {
                "id": uuid4(),
                "type_id": resource_type_id,
                "namespace_id": namespace_id,
            },
        )
