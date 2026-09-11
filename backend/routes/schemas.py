"""
API routing for schema management endpoints.

This module defines the endpoints used for interacting with the SchemaRegistry,
including creating new schemas and retrieving existing ones.
"""

from fastapi import APIRouter, HTTPException
from models import SchemaRegisterRequest
from schema_registry import schema_registry, DuplicateSchemaError


router = APIRouter()

@router.post("/schema", status_code=201)
def register_schema(payload: SchemaRegisterRequest) -> dict:
    """
    Register a newly defined schema with the system.
    
    This endpoint takes a SchemaRegisterRequest definition, checks for uniqueness, 
    and adds it to the global schema registry.
    
    Args:
        payload (SchemaRegisterRequest): The JSON payload containing the schema definition.
    Returns:
        dict: A dictionary containing the success status and the registered schema data.
    Raises:
        HTTPException: HTTP 409 Conflict if a schema with the same name already exists.
    """
    try:
        schema = schema_registry.register(payload)
    except DuplicateSchemaError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"success": True, "schema": schema}