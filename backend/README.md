# Schema-Driven Dashboard API

A FastAPI service for registering data schemas, ingesting validated rows, and
registering dashboard configurations against those schemas.

The application currently uses in-memory storage. Restarting the server clears
all registered schemas, ingested rows, and dashboards.

## Requirements and setup

- Python 3.14 or newer
- [uv](https://docs.astral.sh/uv/)

Run commands from the `backend` directory. `uv` installs the project dependencies
automatically when a command is first executed.

## Running the API

```bash
uv run uvicorn main:app --reload
```

The API is available at `http://localhost:8000`. Interactive documentation is
available through Swagger UI at `http://localhost:8000/docs` and ReDoc at
`http://localhost:8000/redoc`.

## API workflow

```text
Register schema
      |
      +----> Ingest rows validated against the schema
      |
      +----> Register dashboards validated against the schema
```

A dashboard explicitly references its schema. The API does not infer this
relationship from the dashboard name or selected fields.

## Register a schema

### `POST /schema`

Registers the field names and primitive types accepted by a dataset.

```json
{
  "name": "trade",
  "fields": [
    {"name": "tradeId", "type": "string", "required": true},
    {"name": "amount", "type": "number", "required": true, "aggregation": "sum"},
    {"name": "status", "type": "string"},
    {"name": "settled", "type": "boolean"}
  ]
}
```

Supported field types are `string`, `number`, and `boolean`.

Successful response (`201 Created`):

```json
{
  "success": true,
  "schema": {
    "name": "trade",
    "fields": [
      {
        "name": "tradeId",
        "type": "string",
        "required": true,
        "aggregation": null
      }
    ]
  }
}
```

Schema names must be unique. Registering the same name twice returns
`409 Conflict`. Duplicate field names or structurally invalid definitions return
`422 Unprocessable Entity`.

## Ingest rows

### `POST /ingest`

Validates and stores a batch of rows for a registered schema.

```json
{
  "schema": "trade",
  "rows": [
    {"tradeId": "T-1001", "amount": 1250.5, "status": "open", "settled": false},
    {"tradeId": "T-1002", "amount": 500, "status": "closed", "settled": true}
  ]
}
```

Successful response (`201 Created`):

```json
{
  "success": true,
  "schema": "trade",
  "rows_ingested": 2
}
```

Ingestion is atomic. If any row is invalid, no rows from the batch are stored.
Validation rejects unknown fields, missing required fields, primitive type
mismatches, and boolean values supplied for number fields.

Exact duplicate rows within the same schema are ignored, so retrying the same
batch does not duplicate dashboard results. Rows remain isolated by schema.

All invalid rows are reported in one `422` response:

```json
{
  "detail": {
    "message": "Batch validation failed",
    "row_errors": [
      {
        "row_index": 1,
        "errors": [
          {"field": "amount", "message": "Expected number, got str"}
        ]
      }
    ]
  }
}
```

An unknown schema returns `404 Not Found`.

## Register a dashboard

### `POST /dashboard`

Registers a dashboard configuration against an existing schema.

```json
{
  "name": "trade-dashboard",
  "schema": "trade",
  "views": [
    {
      "type": "summary",
      "field": "amount",
      "aggregation": "sum"
    },
    {
      "type": "table",
      "columns": ["tradeId", "amount", "status"]
    }
  ]
}
```

A dashboard must contain at least one view. Supported views are:

- `summary`: describes one aggregation over one field
- `table`: selects one or more fields as columns

Supported summary aggregations depend on the field type:

| Field type | Supported aggregations |
| --- | --- |
| `number` | `sum`, `avg`, `count`, `min`, `max` |
| `string` | `count` |
| `boolean` | `count` |

The optional aggregation stored on a schema field is metadata. The dashboard
configuration owns the aggregation it requests, subject to the compatibility
rules above.

Successful response (`201 Created`):

```json
{
  "success": true,
  "dashboard": {
    "name": "trade-dashboard",
    "schema": "trade",
    "views": [
      {"type": "summary", "field": "amount", "aggregation": "sum"},
      {"type": "table", "columns": ["tradeId", "amount", "status"]}
    ]
  }
}
```

Dashboard registration performs two levels of validation:

1. Pydantic validates the request shape, view type, required properties, and
   supported aggregation names.
2. Business validation checks that the schema exists, referenced fields exist,
   and each summary aggregation is valid for its field type.

Unknown fields across every view are reported together:

```json
{
  "detail": {
    "message": "Invalid dashboard configuration",
    "errors": [
      {"view_index": 0, "field": "banana", "message": "Unknown field"},
      {"view_index": 1, "field": "foobar", "message": "Unknown field"}
    ]
  }
}
```

Additional dashboard rules:

- Unknown schemas return `404 Not Found`.
- Invalid configurations return `422 Unprocessable Entity`.
- Duplicate dashboard names return `409 Conflict`.
- Duplicate columns within the same table view are rejected.
- Multiple summary views over the same field are allowed.
- A dashboard is stored only after the entire configuration passes validation.

Dashboard registration stores configuration only. Dashboard execution and a
`GET /dashboard/{name}` computes each configured view from the schema's current
stored rows. Missing optional fields are ignored by summaries and returned as
`null` in table projections. Empty `sum` and `count` results are `0`; empty
`avg`, `min`, and `max` results are `null`.

## Project structure

```text
backend/
|-- main.py                     FastAPI application and router registration
|-- models.py                   Pydantic request and configuration models
|-- schema_registry.py          In-memory schema registry
|-- data_store.py               In-memory storage for validated rows
|-- dashboard_store.py          In-memory dashboard configuration store
|-- validation.py               Row and batch validation
|-- dashboard_validation.py     Schema-aware dashboard validation
|-- routes/
|   |-- schemas.py              POST /schema
|   |-- ingest.py               POST /ingest
|   `-- dashboards.py           POST /dashboard
`-- tests/                      API and unit tests
```

## Running tests

```bash
uv run pytest -q
```

The test suite covers schema registration, duplicate detection, row and batch
validation, atomic ingestion, dashboard structure, field references,
aggregation compatibility, and dashboard storage.
