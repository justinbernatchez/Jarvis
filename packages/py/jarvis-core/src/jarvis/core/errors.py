from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApplicationError(Exception):
    code: str
    title: str
    status: int
    detail: str
    action: str | None = None
    context: dict[str, Any] | None = None


class NotFoundError(ApplicationError):
    def __init__(self, detail: str = "The requested resource was not found.") -> None:
        super().__init__(
            code="resource.not_found",
            title="Resource not found",
            status=404,
            detail=detail,
        )


class AuthorizationError(ApplicationError):
    def __init__(self, detail: str = "You are not allowed to perform this action.") -> None:
        super().__init__(
            code="authorization.denied",
            title="Access denied",
            status=403,
            detail=detail,
        )


class AuthenticationError(ApplicationError):
    def __init__(self, detail: str = "Authentication is required.") -> None:
        super().__init__(
            code="authentication.required",
            title="Authentication required",
            status=401,
            detail=detail,
            action="Sign in and try again.",
        )


class ConflictError(ApplicationError):
    def __init__(self, detail: str, *, code: str = "conflict.resource_state") -> None:
        super().__init__(
            code=code,
            title="Resource conflict",
            status=409,
            detail=detail,
        )


class PreconditionFailedError(ApplicationError):
    def __init__(self, detail: str = "The resource has changed since it was read.") -> None:
        super().__init__(
            code="conflict.stale_version",
            title="Precondition failed",
            status=412,
            detail=detail,
            action="Reload the resource and retry the change.",
        )


class ConfigurationError(ApplicationError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            code="configuration.invalid",
            title="Configuration is invalid",
            status=422,
            detail=detail,
        )
