import sys
import os

# Add the parent directory (backend root) to the python path so we can import 'main'
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
import pytest

from main import app
from schema_registry import schema_registry
from data_store import data_store

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
    client.post("/schema", json={
        "name": "trade",
        "fields": [
            {"name": "symbol", "type": "string", "required": True},
            {"name": "price", "type": "number", "required": False},
        ]
    })
    
    payload = {
        "schema": "trade",
        "rows": [
            {"symbol": "AAPL", "price": 10.5},
            {"symbol": "NVDA"}
        ]
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


def test_ingest_failure_nothing_stored():
    """Test atomic batch ingestion: if one fails, nothing is stored."""
    # Register schema
    client.post("/schema", json={
        "name": "trade",
        "fields": [
            {"name": "symbol", "type": "string", "required": True},
        ]
    })
    
    payload = {
        "schema": "trade",
        "rows": [
            {"symbol": "AAPL"}, # valid
            {"price": 10.5},    # invalid (missing symbol, unknown field)
        ]
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
    client.post("/schema", json={
        "name": "trade",
        "fields": [{"name": "symbol", "type": "string"}]
    })
    
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
