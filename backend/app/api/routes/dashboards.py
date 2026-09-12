"""
API routing for dashboard configuration management.

The endpoints in this module coordinate dashboard registration and live
execution. Registration performs schema-aware validation before storage, while
retrieval reads current schema rows and delegates computation to the dashboard
engine.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.repositories.dashboard_store import DuplicateDashboardError, dashboard_store
from app.repositories.data_store import data_store
from app.repositories.schema_registry import schema_registry
from app.schemas.models import DashboardRegisterRequest
from app.services.dashboard_engine import generate_dashboard
from app.services.dashboard_validation import validate_dashboard


router = APIRouter()
logger = logging.getLogger(__name__)

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
        HTTPException: HTTP 500 when rows cannot be read or views cannot be
            computed.
    """
    dashboard = dashboard_store.get(name)
    if dashboard is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard '{name}' not found",
        )

    rows = data_store.get_rows(dashboard.schema_name)

    try:
        views = generate_dashboard(dashboard, rows)
    except Exception as error:
        logger.exception("Failed to generate dashboard '%s'", name)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate dashboard views",
        ) from error

    return {
        "success": True,
        "dashboard": name,
        "views": views,
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

    logger.info(
        "Registered dashboard '%s' schema='%s' view_count=%d",
        dashboard.name,
        dashboard.schema_name,
        len(dashboard.views),
    )

    return {
        "success": True,
        "dashboard": dashboard,
    }
