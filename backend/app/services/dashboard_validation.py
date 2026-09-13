"""
Business validation for dashboard configurations.

Structural request validation is handled by Pydantic models. This module checks
schema-dependent rules such as field existence and aggregation compatibility.
"""

from typing import Any

from app.schemas.dashboard import DashboardRegisterRequest

ALLOWED_AGGREGATIONS: dict[str, set[str]] = {
    "number": {"sum", "avg", "count", "min", "max"},
    "string": {"count"},
    "boolean": {"count"},
}


def validate_dashboard(
    dashboard: DashboardRegisterRequest,
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Validate every dashboard view against its referenced schema.

    Validation is exhaustive: all unknown fields and unsupported aggregations
    are returned together instead of stopping at the first error.

    Args:
        dashboard (DashboardRegisterRequest): Structurally valid dashboard request.
        schema (dict[str, Any]): Serialized registered schema definition.

    Returns:
        list[dict[str, Any]]: Structured errors containing the view index, field
        name, and message. An empty list indicates a valid configuration.
    """
    errors: list[dict[str, Any]] = []
    fields = {field["name"]: field for field in schema["fields"]}

    for view_index, view in enumerate(dashboard.views):
        if view.type == "summary":
            field = fields.get(view.field)
            if field is None:
                errors.append(
                    {
                        "view_index": view_index,
                        "field": view.field,
                        "message": "Unknown field",
                    }
                )
                continue

            if view.aggregation not in ALLOWED_AGGREGATIONS[field["type"]]:
                errors.append(
                    {
                        "view_index": view_index,
                        "field": view.field,
                        "message": (
                            f"Aggregation '{view.aggregation}' is not supported "
                            f"for field type '{field['type']}'"
                        ),
                    }
                )
        else:
            for column in view.columns:
                if column not in fields:
                    errors.append(
                        {
                            "view_index": view_index,
                            "field": column,
                            "message": "Unknown field",
                        }
                    )

    return errors
