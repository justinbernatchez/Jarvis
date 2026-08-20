from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter
from jarvis.core.serialization import ApiModel, DecimalString

router = APIRouter(tags=["meta"])


class HealthResponse(ApiModel):
    status: str
    api_version: str


class ContractProofResponse(ApiModel):
    api_version: str
    example_id: UUID
    generated_at: datetime
    decimal_example: DecimalString


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", api_version="v1")


@router.get("/meta/contract", response_model=ContractProofResponse)
def contract_proof() -> ContractProofResponse:
    return ContractProofResponse(
        api_version="v1",
        example_id=UUID("00000000-0000-4000-8000-000000000001"),
        generated_at=datetime.now(UTC),
        decimal_example=Decimal("0.05000"),
    )
