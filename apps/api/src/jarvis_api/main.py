from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from jarvis.core.security import TokenSecurity
from jarvis.core.serialization import CursorCodec
from jarvis.core.settings import Settings, get_settings
from jarvis.db.session import create_database_engine, create_session_factory
from sqlalchemy import Engine
from starlette.responses import Response as StarletteResponse

from jarvis_api.dependencies import ApplicationServices
from jarvis_api.problems import ProblemDetails, install_problem_handlers
from jarvis_api.routers import auth, identity, meta, platform, resources


def create_app(settings: Settings | None = None, *, engine: Engine | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    database_engine = engine or create_database_engine(resolved_settings.database_url)
    app = FastAPI(
        title="JARVIS API",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url=None,
        description="Platform foundation API. Finance-domain features are intentionally absent.",
        responses={
            401: {"model": ProblemDetails, "description": "Authentication required"},
            403: {"model": ProblemDetails, "description": "Access denied"},
            404: {"model": ProblemDetails, "description": "Resource not found"},
            409: {"model": ProblemDetails, "description": "Resource conflict"},
            412: {"model": ProblemDetails, "description": "Precondition failed"},
            422: {"model": ProblemDetails, "description": "Validation failed"},
        },
    )
    app.state.engine = database_engine
    app.state.session_factory = create_session_factory(database_engine)
    app.state.services = ApplicationServices(
        settings=resolved_settings,
        security=TokenSecurity(resolved_settings),
        cursor_codec=CursorCodec(resolved_settings.session_hmac_key),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "If-Match", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["ETag", "X-Request-ID", "Content-Disposition"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[StarletteResponse]],
    ) -> StarletteResponse:
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and resolved_settings.effective_session_cookie_name in request.cookies
            and request.headers.get("Origin") != resolved_settings.web_origin
        ):
            return JSONResponse(
                status_code=403,
                media_type="application/problem+json",
                content={
                    "type": "https://docs.jarvis.local/problems/authorization-origin",
                    "title": "Access denied",
                    "status": 403,
                    "detail": "The request Origin is missing or invalid.",
                    "instance": request.url.path,
                    "code": "authorization.origin",
                    "requestId": request.state.request_id,
                },
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    install_problem_handlers(app)
    for router in (meta.router, auth.router, identity.router, resources.router, platform.router):
        app.include_router(router, prefix="/api/v1")
    _install_openapi_contract(app)
    return app


def _install_openapi_contract(app: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        paths = cast(dict[str, object], schema["paths"])
        for operations_value in paths.values():
            if not isinstance(operations_value, dict):
                continue
            operations = cast(dict[str, object], operations_value)
            for operation_value in operations.values():
                if not isinstance(operation_value, dict):
                    continue
                operation = cast(dict[str, object], operation_value)
                responses_value = operation.get("responses", {})
                if not isinstance(responses_value, dict):
                    continue
                responses = cast(dict[str, object], responses_value)
                for status_code in ("401", "403", "404", "409", "412", "422"):
                    response = responses.get(status_code)
                    if not isinstance(response, dict):
                        continue
                    response_object = cast(dict[str, object], response)
                    content = response_object.get("content")
                    if isinstance(content, dict) and "application/json" in content:
                        content_object = cast(dict[str, object], content)
                        content_object["application/problem+json"] = content_object.pop(
                            "application/json"
                        )
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi


app = create_app()
