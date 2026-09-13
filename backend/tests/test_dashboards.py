import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.dashboard_store import dashboard_store
from app.repositories.data_store import data_store
from app.repositories.schema_registry import schema_registry

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    schema_registry._schemas.clear()
    dashboard_store.clear()
    data_store.clear()


def register_trade_schema():
    return client.post(
        "/schema",
        json={
            "name": "trade",
            "fields": [
                {"name": "tradeId", "type": "string"},
                {"name": "amount", "type": "number"},
                {"name": "status", "type": "string"},
                {"name": "settled", "type": "boolean"},
            ],
        },
    )


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


@pytest.mark.parametrize(
    "view",
    [
        {"type": "chart", "field": "amount"},
        {"type": "summary", "field": "amount", "aggregation": "median"},
    ],
)
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


def test_get_dashboard_not_found():
    response = client.get("/dashboard/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dashboard 'missing' not found"


def test_get_dashboard_computes_views_and_normalizes_missing_values():
    register_trade_schema()
    payload = valid_dashboard()
    payload["views"] = [
        {"type": "summary", "field": "amount", "aggregation": aggregation}
        for aggregation in ["sum", "avg", "count", "min", "max"]
    ] + [{"type": "table", "columns": ["tradeId", "amount", "status"]}]
    assert client.post("/dashboard", json=payload).status_code == 201
    assert (
        client.post(
            "/ingest",
            json={
                "schema": "trade",
                "rows": [
                    {"tradeId": "T1", "amount": 100, "status": "done"},
                    {"tradeId": "T2", "status": "pending"},
                    {"tradeId": "T3", "amount": 50, "status": "done"},
                ],
            },
        ).status_code
        == 201
    )

    response = client.get("/dashboard/trade-dashboard")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "dashboard": "trade-dashboard",
        "views": [
            {"type": "summary", "field": "amount", "aggregation": "sum", "value": 150},
            {"type": "summary", "field": "amount", "aggregation": "avg", "value": 75},
            {"type": "summary", "field": "amount", "aggregation": "count", "value": 2},
            {"type": "summary", "field": "amount", "aggregation": "min", "value": 50},
            {"type": "summary", "field": "amount", "aggregation": "max", "value": 100},
            {
                "type": "table",
                "columns": ["tradeId", "amount", "status"],
                "rows": [
                    {"tradeId": "T1", "amount": 100, "status": "done"},
                    {"tradeId": "T2", "amount": None, "status": "pending"},
                    {"tradeId": "T3", "amount": 50, "status": "done"},
                ],
            },
        ],
    }


def test_get_dashboard_empty_aggregation_semantics():
    register_trade_schema()
    payload = valid_dashboard()
    payload["views"] = [
        {"type": "summary", "field": "amount", "aggregation": aggregation}
        for aggregation in ["sum", "count", "avg", "min", "max"]
    ] + [{"type": "table", "columns": ["tradeId", "amount"]}]
    client.post("/dashboard", json=payload)

    views = client.get("/dashboard/trade-dashboard").json()["views"]

    assert [view.get("value") for view in views[:5]] == [0, 0, None, None, None]
    assert views[5]["rows"] == []


def test_get_dashboard_reads_current_rows_on_every_request():
    register_trade_schema()
    client.post("/dashboard", json=valid_dashboard())
    assert client.get("/dashboard/trade-dashboard").json()["views"][0]["value"] == 0

    client.post("/ingest", json={"schema": "trade", "rows": [{"amount": 12.5}]})

    assert client.get("/dashboard/trade-dashboard").json()["views"][0]["value"] == 12.5
