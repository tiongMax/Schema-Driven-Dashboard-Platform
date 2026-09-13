"""Request models for dashboard configuration."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


class SummaryView(BaseModel):
    """Represent a view that aggregates one schema field."""

    type: Literal["summary"]
    field: str = Field(min_length=1)
    aggregation: Literal["sum", "avg", "count", "min", "max"]


class TableView(BaseModel):
    """Represent a view that projects selected schema fields."""

    type: Literal["table"]
    columns: list[str] = Field(min_length=1)

    @field_validator("columns")
    @classmethod
    def unique_columns(cls, columns: list[str]) -> list[str]:
        """Reject table configurations containing duplicate columns."""
        if len(columns) != len(set(columns)):
            raise ValueError("duplicate columns in table view")
        return columns


DashboardView = Annotated[
    SummaryView | TableView,
    Field(discriminator="type"),
]


class DashboardRegisterRequest(BaseModel):
    """Represent a named dashboard for a registered schema."""

    name: str = Field(min_length=1)
    schema_name: str = Field(alias="schema", min_length=1)
    views: list[DashboardView] = Field(min_length=1)
