"""
Data models and validation schemas using Pydantic.

This module contains the basic models used for registering and validating
schema definitions for our dashboard components.
"""

from typing import List, Literal, Optional
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