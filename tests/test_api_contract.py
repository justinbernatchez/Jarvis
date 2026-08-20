from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Barrier
from uuid import UUID

from jarvis.core.errors import PreconditionFailedError
from jarvis.db.session import (
    assume_application_role,
    set_actor_context,
    set_workspace_context,
)
from jarvis.knowledge.schemas import ResourceUpdate
from jarvis.knowledge.service import update_resource
from jarvis_api.openapi import generate_openapi

from tests.conftest import DatabaseHarness, authenticate_client

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def test_v1_openapi_and_scalar_conventions(client, app, tmp_path: Path) -> None:
    openapi_response = client.get("/api/v1/openapi.json")
    assert openapi_response.status_code == 200
    document = openapi_response.json()
    assert all(path.startswith("/api/v1") for path in document["paths"])
    assert "ProblemDetails" in document["components"]["schemas"]
    assert document["components"]["securitySchemes"]["APIKeyCookie"]["in"] == "cookie"
    assert "302" in document["paths"]["/api/v1/auth/login"]["get"]["responses"]
    patch_operation = document["paths"][
        "/api/v1/workspaces/{workspace_id}/resources/{resource_id}"
    ]["patch"]
    if_match = next(item for item in patch_operation["parameters"] if item["name"] == "If-Match")
    assert if_match["required"] is True
    assert "ETag" in patch_operation["responses"]["200"]["headers"]
    assert "application/problem+json" in patch_operation["responses"]["412"]["content"]

    proof = client.get("/api/v1/meta/contract")
    assert proof.status_code == 200
    body = proof.json()
    assert UUID_PATTERN.match(body["exampleId"])
    assert body["decimalExample"] == "0.05000"
    parsed = datetime.fromisoformat(body["generatedAt"].replace("Z", "+00:00"))
    assert parsed.tzinfo is not None

    generated_path = generate_openapi(tmp_path / "openapi.json")
    generated = json.loads(generated_path.read_text(encoding="utf-8"))
    assert generated["info"]["version"] == app.openapi()["info"]["version"]


def test_authentication_and_rfc_9457_problem_contract(client) -> None:
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = response.json()
    assert problem["type"].startswith("https://docs.jarvis.local/problems/")
    assert problem["status"] == 401
    assert problem["code"] == "authentication.required"
    assert UUID_PATTERN.match(problem["requestId"])


def test_cursor_pagination_and_optimistic_locking(
    client,
    settings,
    create_user_context,
) -> None:
    context = create_user_context("Contract User")
    headers = authenticate_client(client, settings, context)
    created: list[dict[str, object]] = []
    for index in range(3):
        response = client.post(
            f"/api/v1/workspaces/{context.workspace_id}/resources",
            headers=headers,
            json={
                "typeKey": "foundation_record",
                "slug": f"contract-{index}",
                "title": f"Contract {index}",
                "payload": {"index": index},
                "confidence": "0.75000",
            },
        )
        assert response.status_code == 201
        assert UUID_PATTERN.match(response.json()["id"])
        created.append(response.json())

    first_page = client.get(f"/api/v1/workspaces/{context.workspace_id}/resources?limit=2")
    assert first_page.status_code == 200
    page = first_page.json()
    assert len(page["items"]) == 2
    assert page["page"]["hasMore"] is True
    assert page["page"]["nextCursor"]
    second_page = client.get(
        f"/api/v1/workspaces/{context.workspace_id}/resources"
        f"?limit=2&cursor={page['page']['nextCursor']}"
    )
    assert second_page.status_code == 200
    assert second_page.json()["page"]["hasMore"] is False
    assert {
        item["id"] for item in first_page.json()["items"] + second_page.json()["items"]
    }.issuperset({item["id"] for item in created})

    resource = created[0]
    update = client.patch(
        f"/api/v1/workspaces/{context.workspace_id}/resources/{resource['id']}",
        headers={**headers, "If-Match": f'"{resource["lockVersion"]}"'},
        json={"title": "Updated contract"},
    )
    assert update.status_code == 200
    assert update.json()["lockVersion"] == resource["lockVersion"] + 1
    stale = client.patch(
        f"/api/v1/workspaces/{context.workspace_id}/resources/{resource['id']}",
        headers={**headers, "If-Match": f'"{resource["lockVersion"]}"'},
        json={"title": "Stale update"},
    )
    assert stale.status_code == 412
    assert stale.headers["content-type"].startswith("application/problem+json")
    assert stale.json()["code"] == "conflict.stale_version"


def test_generated_typescript_client_is_committed() -> None:
    schema = Path("packages/ts/api-client/src/schema.ts")
    client = Path("packages/ts/api-client/src/index.ts")
    assert schema.exists()
    assert '"/api/v1/workspaces/{workspace_id}/resources"' in schema.read_text(encoding="utf-8")
    assert "export class JarvisApiClient" in client.read_text(encoding="utf-8")


def test_resource_optimistic_lock_is_atomic_under_concurrency(
    client,
    settings,
    database: DatabaseHarness,
    create_user_context,
) -> None:
    context = create_user_context("Concurrent User")
    headers = authenticate_client(client, settings, context)
    created = client.post(
        f"/api/v1/workspaces/{context.workspace_id}/resources",
        headers=headers,
        json={
            "typeKey": "foundation_record",
            "slug": "concurrent-resource",
            "title": "Original",
            "payload": {},
        },
    ).json()
    resource_id = UUID(created["id"])
    expected_version = created["lockVersion"]
    barrier = Barrier(2)

    def update_title(title: str) -> bool:
        try:
            with database.factory() as session, session.begin():
                assume_application_role(session)
                set_actor_context(session, context.user_id, context.session_id)
                set_workspace_context(session, context.workspace_id)
                barrier.wait()
                update_resource(
                    session,
                    resource_id=resource_id,
                    expected_lock_version=expected_version,
                    data=ResourceUpdate(title=title),
                )
            return True
        except PreconditionFailedError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(update_title, ["Writer A", "Writer B"]))
    assert sorted(results) == [False, True]
