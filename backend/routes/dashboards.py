"""
API routing for dashboard configuration management.

The endpoints in this module coordinate dashboard registration and live
execution. Registration performs schema-aware validation before storage, while
retrieval reads current schema rows and delegates computation to the dashboard
engine.
"""

from fastapi import APIRouter, HTTPException

from dashboard_engine import generate_dashboard
from dashboard_store import dashboard_store, DuplicateDashboardError
from dashboard_validation import validate_dashboard
from data_store import data_store
from models import DashboardRegisterRequest
from schema_registry import schema_registry


router = APIRouter()


@router.get("/dashboard/{name}")
def get_dashboard(name: str) -> dict:
    """
    Compute a registered dashboard from its schema's current stored rows.

    Dashboard results are generated on every request rather than persisted, so
    newly ingested rows are reflected immediately.

    Args:
        name (str): Unique identifier of the dashboard to execute.

    Returns:
        dict: Success status, dashboard name, and computed views in configured
        order.

    Raises:
        HTTPException: HTTP 404 when the requested dashboard does not exist.
    """
    dashboard = dashboard_store.get(name)
    if dashboard is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard '{name}' not found",
        )

    rows = data_store.get_rows(dashboard.schema_name)
    return {
        "success": True,
        "dashboard": name,
        "views": generate_dashboard(dashboard, rows),
    }


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
