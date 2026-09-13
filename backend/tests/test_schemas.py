import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.schema_registry import schema_registry

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the schema registry before each test to ensure isolation."""
    # Reset internal dictionary
    schema_registry._schemas.clear()


def test_register_schema_success():
    """Test successful schema registration."""
    response = client.post(
        "/schema",
        json={
            "name": "sales",
            "fields": [
                {
                    "name": "revenue",
                    "type": "number",
                    "required": True,
                    "aggregation": "sum",
                }
            ],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["schema"]["name"] == "sales"
    assert data["schema"]["fields"][0]["name"] == "revenue"


def test_register_duplicate_schema():
    """Test registering a schema with an existing name raises a 409 conflict."""
    payload = {
        "name": "users",
        "fields": [{"name": "id", "type": "number", "required": True}],
    }

    # Register first time
    response1 = client.post("/schema", json=payload)
    assert response1.status_code == 201

    # Attempt to register again
    response2 = client.post("/schema", json=payload)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]


def test_duplicate_field_names_within_schema():
    """Test schema validation fails if field names are not unique."""
    response = client.post(
        "/schema",
        json={
            "name": "invalid_schema",
            "fields": [
                {"name": "id", "type": "number"},
                {"name": "id", "type": "string"},  # Duplicate field name
            ],
        },
    )

    # 422 Unprocessable Entity - Pydantic validation error
    assert response.status_code == 422
    assert "duplicate field names in schema" in response.text
