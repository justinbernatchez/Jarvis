from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any, cast

from itsdangerous import BadData, URLSafeSerializer
from pydantic import BaseModel, ConfigDict, PlainSerializer, WithJsonSchema

DecimalString = Annotated[
    Decimal,
    PlainSerializer(lambda value: format(value, "f"), return_type=str),
    WithJsonSchema({"type": "string", "format": "decimal"}),
]


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class PageInfo(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: _to_camel(value), populate_by_name=True)

    next_cursor: str | None = None
    has_more: bool


class CursorPage[T](BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: _to_camel(value), populate_by_name=True)

    items: list[T]
    page: PageInfo


class CursorCodec:
    def __init__(self, secret: str, *, salt: str = "jarvis-cursor-v1") -> None:
        self._serializer = URLSafeSerializer(secret, salt=salt)

    def encode(self, payload: dict[str, Any]) -> str:
        return self._serializer.dumps(payload)

    def decode(self, cursor: str) -> dict[str, Any]:
        try:
            value = self._serializer.loads(cursor)
        except BadData as exc:
            raise ValueError("Invalid cursor") from exc
        if not isinstance(value, dict):
            raise ValueError("Invalid cursor")
        return cast(dict[str, Any], value)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        from_attributes=True,
        extra="forbid",
    )
