"""
Dashboard view computation.

This module transforms validated dashboard configurations and ingested rows
into response-ready summary and table views. It performs computation only and
does not handle HTTP concerns, configuration validation, or storage access.
"""

from typing import Any

from app.schemas.dashboard import DashboardRegisterRequest, SummaryView, TableView


def compute_summary(
    rows: list[dict[str, Any]],
    field: str,
    aggregation: str,
) -> Any:
    """
    Aggregate the present values of one field across a collection of rows.

    Rows in which the field is absent are ignored. Empty ``sum`` and ``count``
    aggregations return ``0``; empty ``avg``, ``min``, and ``max`` aggregations
    return ``None``.

    Args:
        rows (list[dict[str, Any]]): Validated rows to aggregate.
        field (str): Field whose present values should be aggregated.
        aggregation (str): Aggregation operation to apply.

    Returns:
        Any: The computed numeric result, count, or ``None`` when the requested
        aggregation is undefined for an empty value set.

    Raises:
        ValueError: If the aggregation operation is unsupported.
    """
    values = [row[field] for row in rows if field in row]
    if not values:
        return 0 if aggregation in {"sum", "count"} else None
    
    if aggregation == "count":
        return len(values)
    if aggregation == "sum":
        return sum(values)
    if aggregation == "avg":
        return sum(values) / len(values)
    if aggregation == "min":
        return min(values)
    if aggregation == "max":
        return max(values)

    raise ValueError(f"Unsupported aggregation: {aggregation}")


def compute_table(
    rows: list[dict[str, Any]],
    columns: list[str],
) -> list[dict[str, Any]]:
    """
    Project stored rows onto an ordered collection of table columns.

    Every returned row contains every configured column. An absent optional
    value is represented by ``None``, which FastAPI serializes as JSON ``null``.

    Args:
        rows (list[dict[str, Any]]): Validated rows to project.
        columns (list[str]): Ordered field names to include in each result row.

    Returns:
        list[dict[str, Any]]: Projected rows with a consistent column shape.
    """
    return [
        {column: row.get(column) for column in columns}
        for row in rows
    ]


def compute_view(
    view: SummaryView | TableView,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compute one validated summary or table view.

    Args:
        view (SummaryView | TableView): Validated view configuration.
        rows (list[dict[str, Any]]): Current rows for the dashboard schema.

    Returns:
        dict[str, Any]: A response-ready view containing either an aggregated
        value or projected table rows.

    Raises:
        ValueError: If the supplied view type is unsupported.
    """
    if isinstance(view, SummaryView):
        return {
            "type": "summary",
            "field": view.field,
            "aggregation": view.aggregation,
            "value": compute_summary(rows, view.field, view.aggregation),
        }

    if isinstance(view, TableView):
        return {
            "type": "table",
            "columns": view.columns,
            "rows": compute_table(rows, view.columns),
        }

    raise ValueError(f"Unsupported view type: {view.type}")


def generate_dashboard(
    config: DashboardRegisterRequest,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Compute every view in a validated dashboard configuration.

    Views are returned in the same order in which they were registered.

    Args:
        config (DashboardRegisterRequest): Validated dashboard configuration.
        rows (list[dict[str, Any]]): Current rows for the referenced schema.

    Returns:
        list[dict[str, Any]]: Response-ready computed dashboard views.
    """
    return [compute_view(view, rows) for view in config.views]
