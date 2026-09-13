"""Request models for registering data schemas."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FieldDefinition(BaseModel):
    """Define the name, type, requirement, and aggregation of one field."""

    name: str = Field(min_length=1)
    type: Literal["string", "number", "boolean"]
    required: bool = False
    aggregation: Literal["sum", "avg", "count", "min", "max"] | None = None


class SchemaRegisterRequest(BaseModel):
    """Represent a named, non-empty collection of field definitions."""

    name: str = Field(min_length=1)
    fields: list[FieldDefinition] = Field(min_length=1)

    @field_validator("fields")
    @classmethod
    def unique_field_names(
        cls,
        fields: list[FieldDefinition],
    ) -> list[FieldDefinition]:
        """Reject schemas containing duplicate field names."""
        names = [field.name for field in fields]
        if len(names) != len(set(names)):
            raise ValueError("duplicate field names in schema")
        return fields
