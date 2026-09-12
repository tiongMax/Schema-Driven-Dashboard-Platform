"""
In-memory dashboard configuration storage.

This module stores dashboard definitions only after route-level validation has
confirmed that they are compatible with their referenced schemas. It does not
execute views or read ingested data.
"""

from app.schemas.models import DashboardRegisterRequest


class DuplicateDashboardError(Exception):
    """
    Exception raised when a dashboard name has already been registered.

    Attributes:
        name (str): Name of the dashboard that caused the conflict.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize a duplicate-dashboard error.

        Args:
            name (str): Name of the dashboard that already exists.
        """
        self.name = name
        super().__init__(f"dashboard '{name}' already exists")


class DashboardStore:
    """In-memory registry for validated dashboard configurations."""

    def __init__(self) -> None:
        """Initialize an empty dashboard registry."""
        self._dashboards: dict[str, DashboardRegisterRequest] = {}

    def register(
        self,
        dashboard: DashboardRegisterRequest,
    ) -> DashboardRegisterRequest:
        """
        Register a dashboard under its unique name.

        A deep copy is stored and returned so callers cannot mutate internal
        state through nested view data.

        Args:
            dashboard (DashboardRegisterRequest): Validated configuration to store.

        Returns:
            DashboardRegisterRequest: An independent copy of the stored dashboard.

        Raises:
            DuplicateDashboardError: If the dashboard name is already registered.
        """
        if dashboard.name in self._dashboards:
            raise DuplicateDashboardError(dashboard.name)

        stored = dashboard.model_copy(deep=True)
        self._dashboards[dashboard.name] = stored
        return stored.model_copy(deep=True)

    def get(self, name: str) -> DashboardRegisterRequest | None:
        """
        Retrieve a dashboard by name.

        Args:
            name (str): Dashboard identifier to retrieve.

        Returns:
            DashboardRegisterRequest | None: A deep copy of the dashboard when
            found, otherwise ``None``.
        """
        dashboard = self._dashboards.get(name)
        return dashboard.model_copy(deep=True) if dashboard is not None else None

    def exists(self, name: str) -> bool:
        """
        Check whether a dashboard is registered.

        Args:
            name (str): Dashboard identifier to check.

        Returns:
            bool: ``True`` when the dashboard exists, otherwise ``False``.
        """
        return name in self._dashboards

    def clear(self) -> None:
        """Remove every registered dashboard, primarily for test isolation."""
        self._dashboards.clear()


dashboard_store = DashboardStore()
