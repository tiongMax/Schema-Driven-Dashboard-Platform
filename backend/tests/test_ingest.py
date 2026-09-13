import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.data_store import data_store
from app.repositories.schema_registry import schema_registry

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    """Clear the schema registry and data store before each test."""
    schema_registry._schemas.clear()
    data_store.clear()


def test_ingest_schema_not_found():
    """Test 404 is thrown when ingesting to an unregistered schema."""
    response = client.post("/ingest", json={"schema": "unknown", "rows": []})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_ingest_success_and_storage():
    """Test fully valid batch is successfully ingested and stored."""
    # Register schema
    client.post(
        "/schema",
        json={
            "name": "trade",
            "fields": [
                {"name": "symbol", "type": "string", "required": True},
                {"name": "price", "type": "number", "required": False},
            ],
        },
    )

    payload = {
        "schema": "trade",
        "rows": [{"symbol": "AAPL", "price": 10.5}, {"symbol": "NVDA"}],
    }

    # Ingest rows
    response = client.post("/ingest", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert data["rows_ingested"] == 2

    # Verify data successfully reached the DataStore
    stored = data_store.get_rows("trade")
    assert len(stored) == 2
    assert stored[0]["symbol"] == "AAPL"


def test_repeated_rows_are_not_stored_twice():
    """Submitting the same data twice should not duplicate dashboard rows."""
    client.post(
        "/schema",
        json={
            "name": "trade",
            "fields": [
                {"name": "tradeId", "type": "string", "required": True},
                {"name": "amount", "type": "number", "required": True},
            ],
        },
    )
    payload = {
        "schema": "trade",
        "rows": [
            {"tradeId": "ORD-101", "amount": 1240},
            {"tradeId": "ORD-102", "amount": 860},
        ],
    }

    first = client.post("/ingest", json=payload)
    second = client.post("/ingest", json=payload)

    assert first.json()["rows_ingested"] == 2
    assert first.json()["duplicates_skipped"] == 0
    assert second.json()["rows_ingested"] == 0
    assert second.json()["duplicates_skipped"] == 2
    assert data_store.get_rows("trade") == payload["rows"]


def test_rows_with_the_same_shape_remain_isolated_by_schema():
    """Two schemas may contain the same rows without combining their datasets."""
    fields = [{"name": "tradeId", "type": "string", "required": True}]
    client.post("/schema", json={"name": "trades-a", "fields": fields})
    client.post("/schema", json={"name": "trades-b", "fields": fields})
    rows = [{"tradeId": "ORD-101"}, {"tradeId": "ORD-102"}]

    client.post("/ingest", json={"schema": "trades-a", "rows": rows})
    client.post("/ingest", json={"schema": "trades-b", "rows": rows})

    assert data_store.get_rows("trades-a") == rows
    assert data_store.get_rows("trades-b") == rows


def test_ingest_failure_nothing_stored():
    """Test atomic batch ingestion: if one fails, nothing is stored."""
    # Register schema
    client.post(
        "/schema",
        json={
            "name": "trade",
            "fields": [
                {"name": "symbol", "type": "string", "required": True},
            ],
        },
    )

    payload = {
        "schema": "trade",
        "rows": [
            {"symbol": "AAPL"},  # valid
            {"price": 10.5},  # invalid (missing symbol, unknown field)
        ],
    }

    # Ingest
    response = client.post("/ingest", json=payload)
    assert response.status_code == 422

    # Verify structural HTTP response detail
    detail = response.json()["detail"]
    assert detail["message"] == "Batch validation failed"
    assert len(detail["row_errors"]) == 1
    assert detail["row_errors"][0]["row_index"] == 1

    # Data Store should be inherently empty despite row 0 being valid
    stored = data_store.get_rows("trade")
    assert len(stored) == 0


def test_data_store_mutation_guard():
    """Test DataStore safely deep/shallow copies to prevent upstream changes mutating storage."""
    client.post(
        "/schema",
        json={"name": "trade", "fields": [{"name": "symbol", "type": "string"}]},
    )

    # Original list of references
    rows = [{"symbol": "AAPL"}]
    payload = {"schema": "trade", "rows": rows}

    client.post("/ingest", json=payload)

    # Attempt to mutate the upstream object structure
    rows[0]["symbol"] = "MUTATED"

    # Storage should be inherently protected
    stored = data_store.get_rows("trade")
    assert stored[0]["symbol"] == "AAPL"

    # Attempt to mutate the downstream retrieved object structure
    stored[0]["symbol"] = "DOWNSTREAM_MUTATION"

    # Storage should still be protected across continuous pulls
    stored_again = data_store.get_rows("trade")
    assert stored_again[0]["symbol"] == "AAPL"
