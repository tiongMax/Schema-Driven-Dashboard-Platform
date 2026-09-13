"""
Core validation logic for dynamic rows.

This module is responsible for executing business-level validation of dynamically
structured rows against a registered schema definition. It ensures that standard
rules regarding types, missing fields, and unknown fields are strictly applied.
"""

from typing import Any


def matches_type(value: Any, expected_type: str) -> bool:
    """
    Check if a value matches a requested schema type.

    Args:
        value (Any): The arbitrary value to check.
        expected_type (str): The expected primitive type (e.g., 'string', 'number', 'boolean').

    Returns:
        bool: True if the value's type strictly matches the expected_type, False otherwise.
    """
    if expected_type == "string":
        return isinstance(value, str)

    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    if expected_type == "boolean":
        return isinstance(value, bool)

    return False


def validate_row(
    row: dict[str, Any],
    schema: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Validate a single row against a corresponding registered schema.

    Args:
        row (dict[str, Any]): A single row of data from the ingestion payload.
        schema (dict[str, Any]): The full definition of the schema.

    Returns:
        list[dict[str, str]]: A list of field-specific error dictionaries if validation
                              fails. Returns an empty list if the row is perfectly valid.
    """
    errors: list[dict[str, str]] = []

    field_defs = {field["name"]: field for field in schema["fields"]}

    # Reject unknown fields
    for field_name in row:
        if field_name not in field_defs:
            errors.append(
                {
                    "field": field_name,
                    "message": "Unknown field",
                }
            )

    # Check required fields and types
    for field_name, definition in field_defs.items():
        if field_name not in row:
            if definition.get("required", False):
                errors.append(
                    {
                        "field": field_name,
                        "message": "Required field is missing",
                    }
                )
            continue

        value = row[field_name]

        if not matches_type(value, definition["type"]):
            errors.append(
                {
                    "field": field_name,
                    "message": (
                        f"Expected {definition['type']}, got {type(value).__name__}"
                    ),
                }
            )

    return errors


def validate_batch(
    rows: list[dict[str, Any]],
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Validate a complete batch of rows against a schema.

    This function processes all rows and collects errors into a structured format
    indexed by row position, allowing the API response to return the state of the
    entire batch at once.

    Args:
        rows (list[dict[str, Any]]): The entire list of dynamically structured data.
        schema (dict[str, Any]): The full definition of the schema.

    Returns:
        list[dict[str, Any]]: A list of row-indexed error dictionaries. Returns an
                              empty list if the entire batch passes validation.
    """
    row_errors: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        errors = validate_row(row, schema)

        if errors:
            row_errors.append(
                {
                    "row_index": index,
                    "errors": errors,
                }
            )

    return row_errors
