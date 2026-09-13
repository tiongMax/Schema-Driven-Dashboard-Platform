"""Request models for data ingestion."""

from typing import Any

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Represent a batch of dynamic rows targeting a registered schema."""

    schema_name: str = Field(alias="schema")
    rows: list[dict[str, Any]]
