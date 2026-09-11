"""
In-memory schema registry management module.

This module provides an in-memory store for registered schemas and ensures
that schemas are uniquely named and retrievable.
"""

from typing import Dict, Optional
from models import SchemaRegisterRequest


class DuplicateSchemaError(Exception):
    """
    Exception raised when attempting to register a schema with a name that already exists.
    
    Attributes:
        name (str): The name of the duplicate schema that caused the error.
    """
    def __init__(self, name: str):
        """
        Initialize the DuplicateSchemaError.

        Args:
            name (str): The duplicate schema name.
        """
        self.name = name
        super().__init__(f"schema '{name}' already exists")


class SchemaRegistry:
    """
    In-memory registry to store and manage schema definitions.
    """
    def __init__(self):
        """Initialize an empty schema registry."""
        self._schemas: Dict[str, SchemaRegisterRequest] = {}

    def register(self, schema: SchemaRegisterRequest) -> SchemaRegisterRequest:
        """
        Register a new schema in the registry.
        
        Args:
            schema (SchemaRegisterRequest): The schema object to register.
        Returns:
            SchemaRegisterRequest: The successfully registered schema. 
        Raises:
            DuplicateSchemaError: If a schema with the same name already exists.
        """
        if schema.name in self._schemas:
            raise DuplicateSchemaError(schema.name)
        self._schemas[schema.name] = schema
        return schema

    def get(self, name: str) -> Optional[SchemaRegisterRequest]:
        """
        Retrieve a schema by its registered name.
        
        Args:
            name (str): The name of the schema to fetch.
        Returns:
            Optional[SchemaRegisterRequest]: The schema if found, else None.
        """
        return self._schemas.get(name)

    def exists(self, name: str) -> bool:
        """
        Check if a schema exists in the registry.
        
        Args:
            name (str): The name of the schema to check.
        Returns:
            bool: True if the schema exists, False otherwise.
        """
        return name in self._schemas


# Module-level singleton — imported directly by route modules
schema_registry = SchemaRegistry()