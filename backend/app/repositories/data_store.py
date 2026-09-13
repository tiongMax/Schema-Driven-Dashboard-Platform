"""
In-memory data store for validated rows.

This module provides a simple, structured storage layer for tracking data ingested
against registered schemas. It inherently relies on the upstream validation layer
to guarantee data integrity, remaining intentionally simple and performing strictly
shallow-copies to avoid accidental state mutation.
"""

from typing import Any


class DataStore:
    """
    In-memory storage registry to collect validated dynamically shaped data rows.
    """

    def __init__(self) -> None:
        """Initialize an empty data store."""
        self._data: dict[str, list[dict[str, Any]]] = {}

    def insert_batch(
        self,
        schema_name: str,
        rows: list[dict[str, Any]],
    ) -> int:
        """
        Store a fully validated batch of rows.

        Args:
            schema_name (str): The string identifier matching a registered schema.
            rows (list[dict[str, Any]]): The list of validated row dictionaries to store.
        """
        stored_rows = self._data.setdefault(schema_name, [])
        rows_inserted = 0

        for row in rows:
            # Re-submitting the same batch from the UI should be idempotent.
            # Data remains isolated by schema name, and only exact duplicates
            # within that schema are skipped.
            if row in stored_rows:
                continue
            stored_rows.append(row.copy())
            rows_inserted += 1

        return rows_inserted

    def get_rows(
        self,
        schema_name: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all stored data rows for a specified schema.

        Args:
            schema_name (str): The desired schema's string identifier.

        Returns:
            list[dict[str, Any]]: A shallow-copy list of all stored rows. If
                                  no rows exist for the schema, an empty list
                                  is returned.
        """
        return [row.copy() for row in self._data.get(schema_name, [])]

    def clear(self) -> None:
        """Clear all stored data (primarily for testing purposes)."""
        self._data.clear()


data_store = DataStore()
