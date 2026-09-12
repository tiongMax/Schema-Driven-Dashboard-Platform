"""
Data models and validation schemas using Pydantic.

This module contains the basic models used for registering and validating
schema definitions for our dashboard components.
"""

from typing import Annotated, Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class FieldDefinition(BaseModel):
    """
    Represents a single field definition within a schema.
    
    Attributes:
        name (str): The name of the field. Must be at least 1 character.
        type (Literal["string", "number", "boolean"]): The data type of the field.
        required (bool): Whether this field is mandatory. Defaults to False.
        aggregation (Optional[Literal["sum", "avg", "count", "min", "max"]]): 
            Optional aggregation method for numeric fields.
    """
    name: str = Field(min_length=1)
    type: Literal["string", "number", "boolean"]
    required: bool = False
    aggregation: Optional[Literal["sum", "avg", "count", "min", "max"]] = None


class SchemaRegisterRequest(BaseModel):
    """
    Request model for registering a new data schema.
    
    Attributes:
        name (str): The name of the schema. Must be at least 1 character.
        fields (List[FieldDefinition]): A list of FieldDefinitions comprising the schema.
    """
    name: str = Field(min_length=1)
    fields: List[FieldDefinition] = Field(min_length=1)

    @field_validator("fields")
    @classmethod
    def unique_field_names(cls, fields: List[FieldDefinition]) -> List[FieldDefinition]:
        """
        Validates that all field names within a schema are unique.
        
        Args:
            fields (List[FieldDefinition]): The list of fields defined in the schema.
        Returns:
            List[FieldDefinition]: The validated list of fields.
        Raises:
            ValueError: If there are duplicate field names in the schema.
        """
        names = [f.name for f in fields]
        if len(names) != len(set(names)):
            raise ValueError("duplicate field names in schema")
        return fields


class IngestRequest(BaseModel):
    """
    Request model for ingesting dynamic rows against a registered schema.
    
    Attributes:
        schema_name (str): The registered schema identifier this batch targets. 
                           Aliased to `schema` for JSON payloads.
        rows (list[dict[str, Any]]): The list of arbitrary dynamic data rows.
    """
    schema_name: str = Field(alias="schema")
    rows: list[dict[str, Any]]


class SummaryView(BaseModel):
    """
    Represents a summary view that aggregates one schema field.

    Attributes:
        type (Literal["summary"]): Discriminator identifying the view as a summary.
        field (str): Name of the schema field to aggregate.
        aggregation (Literal["sum", "avg", "count", "min", "max"]):
            Aggregation operation requested by the dashboard.
    """

    type: Literal["summary"]
    field: str = Field(min_length=1)
    aggregation: Literal["sum", "avg", "count", "min", "max"]


class TableView(BaseModel):
    """
    Represents a table view that projects selected schema fields.

    Attributes:
        type (Literal["table"]): Discriminator identifying the view as a table.
        columns (list[str]): Ordered, non-empty list of schema fields to display.
    """

    type: Literal["table"]
    columns: list[str] = Field(min_length=1)

    @field_validator("columns")
    @classmethod
    def unique_columns(cls, columns: list[str]) -> list[str]:
        """
        Ensure that a table does not request the same column more than once.

        Args:
            columns (list[str]): Ordered column names supplied by the client.

        Returns:
            list[str]: The validated column names without modification.

        Raises:
            ValueError: If one or more column names are duplicated.
        """
        if len(columns) != len(set(columns)):
            raise ValueError("duplicate columns in table view")
        return columns


DashboardView = Annotated[
    SummaryView | TableView,
    Field(discriminator="type"),
]


class DashboardRegisterRequest(BaseModel):
    """
    Request model for registering a schema-backed dashboard configuration.

    Attributes:
        name (str): Unique dashboard identifier.
        schema_name (str): Referenced schema identifier, accepted as ``schema``
            in JSON request bodies.
        views (list[DashboardView]): Non-empty collection of summary or table
            view definitions.
    """

    name: str = Field(min_length=1)
    schema_name: str = Field(alias="schema", min_length=1)
    views: list[DashboardView] = Field(min_length=1)
