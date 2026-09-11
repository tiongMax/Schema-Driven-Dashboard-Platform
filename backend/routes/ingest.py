"""
Ingestion routing module.

This module exposes the main API endpoint for ingesting new dynamic rows. It orchestrates
structural mapping, deep business validation, and ultimate storage execution. 
"""

from fastapi import APIRouter, HTTPException
from models import IngestRequest
from schema_registry import schema_registry
from validation import validate_batch
from data_store import data_store

router = APIRouter()

@router.post("/ingest", status_code=201)
def ingest(request: IngestRequest):
    """
    Ingest a batch of dynamic rows against a registered dashboard schema.

    This route performs structural request shaping via Pydantic (`IngestRequest`) and
    subsequently delegates business validation to the core validator. If one or more rows
    do not conform to the schema's field definitions, it completely rejects the entire batch
    returning a granular 422 HTTP exception.
    
    Args:
        request (IngestRequest): The fully shaped ingestion payload, including standard 
                                 schema attribution and arbitrary tabular data rows.
                                 
    Returns:
        dict: A successful ingestion confirmation payload.
        
    Raises:
        HTTPException: 404 if the specified schema identifier is unregistered.
        HTTPException: 422 if business validation fails for any rows in the batch, yielding
                       comprehensive index-mapped error objects.
    """
    schema = schema_registry.get(request.schema_name)

    if schema is None:
        raise HTTPException(
            status_code=404,
            detail=f"Schema '{request.schema_name}' not found",
        )

    errors = validate_batch(
        request.rows,
        schema.model_dump(),
    )

    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Batch validation failed",
                "row_errors": errors,
            },
        )

    rows_ingested = data_store.insert_batch(
        request.schema_name,
        request.rows,
    )

    return {
        "success": True,
        "schema": request.schema_name,
        "rows_ingested": rows_ingested,
        "duplicates_skipped": len(request.rows) - rows_ingested,
    }
