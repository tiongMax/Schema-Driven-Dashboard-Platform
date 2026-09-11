import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from dashboard_store import dashboard_store
from main import app
from schema_registry import schema_registry


client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    schema_registry._schemas.clear()
    dashboard_store.clear()


def register_trade_schema():
    return client.post("/schema", json={
        "name": "trade",
        "fields": [
            {"name": "tradeId", "type": "string"},
            {"name": "amount", "type": "number"},
            {"name": "status", "type": "string"},
            {"name": "settled", "type": "boolean"},
        ],
    })


def valid_dashboard():
    return {
        "name": "trade-dashboard",
        "schema": "trade",
        "views": [
            {"type": "summary", "field": "amount", "aggregation": "sum"},
            {"type": "table", "columns": ["tradeId", "amount", "status"]},
        ],
    }


def test_register_dashboard_success():
    register_trade_schema()
    response = client.post("/dashboard", json=valid_dashboard())

    assert response.status_code == 201
    assert response.json()["dashboard"] == valid_dashboard()
    assert dashboard_store.exists("trade-dashboard")


def test_dashboard_requires_existing_schema():
    response = client.post("/dashboard", json=valid_dashboard())

    assert response.status_code == 404
    assert response.json()["detail"] == "Schema 'trade' not found"
    assert not dashboard_store.exists("trade-dashboard")


def test_dashboard_reports_all_unknown_fields_and_is_not_stored():
    register_trade_schema()
    payload = valid_dashboard()
    payload["views"] = [
        {"type": "summary", "field": "banana", "aggregation": "sum"},
        {"type": "table", "columns": ["tradeId", "foobar"]},
    ]

    response = client.post("/dashboard", json=payload)

    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    assert errors == [
        {"view_index": 0, "field": "banana", "message": "Unknown field"},
        {"view_index": 1, "field": "foobar", "message": "Unknown field"},
    ]
    assert not dashboard_store.exists("trade-dashboard")


@pytest.mark.parametrize("field", ["status", "settled"])
def test_only_count_is_allowed_for_non_numeric_summaries(field):
    register_trade_schema()
    payload = valid_dashboard()
    payload["views"] = [{"type": "summary", "field": field, "aggregation": "sum"}]

    response = client.post("/dashboard", json=payload)

    assert response.status_code == 422
    assert "not supported" in response.json()["detail"]["errors"][0]["message"]


def test_count_is_allowed_for_non_numeric_summary():
    register_trade_schema()
    payload = valid_dashboard()
    payload["views"] = [{"type": "summary", "field": "status", "aggregation": "count"}]

    assert client.post("/dashboard", json=payload).status_code == 201


def test_duplicate_dashboard_returns_conflict():
    register_trade_schema()
    assert client.post("/dashboard", json=valid_dashboard()).status_code == 201
    response = client.post("/dashboard", json=valid_dashboard())

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_duplicate_table_columns_are_rejected_structurally():
    register_trade_schema()
    payload = valid_dashboard()
    payload["views"] = [{"type": "table", "columns": ["amount", "amount"]}]

    response = client.post("/dashboard", json=payload)

    assert response.status_code == 422
    assert "duplicate columns in table view" in response.text


@pytest.mark.parametrize("view", [
    {"type": "chart", "field": "amount"},
    {"type": "summary", "field": "amount", "aggregation": "median"},
])
def test_invalid_view_shapes_are_rejected(view):
    register_trade_schema()
    payload = valid_dashboard()
    payload["views"] = [view]

    assert client.post("/dashboard", json=payload).status_code == 422


def test_dashboard_requires_at_least_one_view():
    register_trade_schema()
    payload = valid_dashboard()
    payload["views"] = []

    assert client.post("/dashboard", json=payload).status_code == 422
