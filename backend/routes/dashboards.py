"""
API routing for dashboard configuration management.

The endpoint in this module coordinates structural request parsing, referenced
schema lookup, business validation, and persistent in-memory registration.
"""

from fastapi import APIRouter, HTTPException

from dashboard_store import dashboard_store, DuplicateDashboardError
from dashboard_validation import validate_dashboard
from models import DashboardRegisterRequest
from schema_registry import schema_registry


router = APIRouter()


@router.post("/dashboard", status_code=201)
def register_dashboard(request: DashboardRegisterRequest) -> dict:
    """
    Validate and register a dashboard against an existing schema.

    Args:
        request (DashboardRegisterRequest): Dashboard name, referenced schema,
            and view definitions supplied by the client.

    Returns:
        dict: Success status and the registered dashboard configuration.

    Raises:
        HTTPException: HTTP 404 when the referenced schema does not exist.
        HTTPException: HTTP 422 when a view is incompatible with the schema.
        HTTPException: HTTP 409 when the dashboard name is already registered.
    """
    schema = schema_registry.get(request.schema_name)
    if schema is None:
        raise HTTPException(
            status_code=404,
            detail=f"Schema '{request.schema_name}' not found",
        )

    errors = validate_dashboard(request, schema.model_dump())
    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid dashboard configuration",
                "errors": errors,
            },
        )

    try:
        dashboard = dashboard_store.register(request)
    except DuplicateDashboardError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {
        "success": True,
        "dashboard": dashboard,
    }
