from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jarvis.core.errors import ApplicationError
from pydantic import BaseModel, ConfigDict


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ProblemDetails(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    request_id: str
    action: str | None = None
    errors: list[dict[str, Any]] | None = None


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        return _response(
            request,
            status=exc.status,
            title=exc.title,
            detail=exc.detail,
            code=exc.code,
            action=exc.action,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = [
            {
                "location": [str(part) for part in error["loc"]],
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return _response(
            request,
            status=422,
            title="Request validation failed",
            detail="One or more request values are invalid.",
            code="validation.request",
            errors=errors,
        )


def _response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
    code: str,
    action: str | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    problem = ProblemDetails(
        type=f"https://docs.jarvis.local/problems/{code.replace('.', '-')}",
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        code=code,
        request_id=request.state.request_id,
        action=action,
        errors=errors,
    )
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(mode="json", by_alias=True, exclude_none=True),
        media_type="application/problem+json",
        headers={"X-Request-ID": request.state.request_id},
    )
