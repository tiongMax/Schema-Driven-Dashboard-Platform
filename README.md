# Configurable Data Ingestion & Dashboard API

A lightweight FastAPI application for registering data schemas, validating and ingesting records against those schemas, and generating configurable dashboards over the ingested data.

---

## Tech Stack

- **Backend:** Python, FastAPI, Pydantic
- **Frontend:** React + Vite
- **Storage:** in-memory Python objects only

---

## Core Workflow

The application supports three workflows:

1. Register a schema.
2. Ingest data that conforms to that schema.
3. Register and generate dashboards over the ingested data.

The central invariant is:

> **Anything stored in `DataStore` has already been validated against its registered schema.**

This allows the dashboard layer to trust stored records instead of repeatedly re-validating them during aggregation.

---

## Architecture

```text
Frontend (React)
      │
      ▼
FastAPI Routes
      │
      ├───────────────┐
      ▼               ▼
Schema / Ingest   Dashboard Config
Validation        Validation
      │               │
      ▼               ▼
SchemaRegistry   DashboardStore
      │               │
      └──────┐   ┌────┘
             ▼   ▼
            DataStore
               │
               ▼
        DashboardEngine
```

Backend structure:

```text
backend/
├── app/
│   ├── main.py                  # FastAPI application assembly
│   ├── api/
│   │   └── routes/              # HTTP endpoints and response handling
│   ├── repositories/            # In-memory persistence implementations
│   ├── schemas/                 # Pydantic models grouped by API domain
│   │   ├── schema.py            # Schema and field definitions
│   │   ├── ingest.py            # Ingestion request model
│   │   └── dashboard.py         # Dashboard and view models
│   └── services/                # Validation and dashboard business logic
├── tests/                       # Backend test suite
├── pyproject.toml               # Dependencies and Python tool configuration
└── uv.lock                      # Reproducible dependency lockfile
```

Responsibilities:

- **Pydantic models** validate fixed request structure.
- **SchemaRegistry** stores registered schemas.
- **Validation engine** validates dynamic rows against registered schemas.
- **DataStore** stores validated records only.
- **DashboardStore** stores validated dashboard configurations.
- **DashboardEngine** computes summary and table views.
- **FastAPI routes** handle HTTP concerns and coordinate the components.

Routes do not manipulate raw storage dictionaries directly.

---

# API Overview

## `POST /schema`

Registers a schema.

Example:

```json
{
  "name": "trade",
  "fields": [
    {
      "name": "tradeId",
      "type": "string",
      "required": true
    },
    {
      "name": "amount",
      "type": "number",
      "required": true,
      "aggregation": "sum"
    },
    {
      "name": "status",
      "type": "string",
      "required": false
    }
  ]
}
```

Status codes:

```text
201 Created
409 Conflict             duplicate schema name
422 Unprocessable Entity invalid request/schema definition
```

## `GET /schema`

Returns all registered schemas.

## `GET /schema/{name}`

Returns one registered schema.

```text
200 OK
404 Not Found
```

---

# Schema Design & Validation

Supported field types:

```text
string
number
boolean
```

Supported aggregation metadata:

```text
sum
avg
count
min
max
```

Schema registration validates:

- non-empty schema name,
- at least one field,
- non-empty field names,
- supported field types,
- boolean `required`,
- supported aggregation metadata,
- no duplicate field names.

Duplicate schema names are rejected with `409 Conflict`.

---

# Data Ingestion

## `POST /ingest`

Example:

```json
{
  "schema": "trade",
  "rows": [
    {
      "tradeId": "T001",
      "amount": 125.5,
      "status": "completed"
    },
    {
      "tradeId": "T002",
      "amount": 90
    }
  ]
}
```

Example success response:

```json
{
  "success": true,
  "schema": "trade",
  "rows_ingested": 2
}
```

### Validation rules

- Required fields must be present.
- Unknown fields are rejected.
- Types must match exactly.
- No implicit type coercion is performed.
- `number` accepts integers and floats, but not booleans.
- Optional fields may be omitted.
- Optional does not imply nullable.
- All rows are validated before storage.
- Any invalid row rejects the entire batch.

Example: this fails if `amount` is a number field:

```json
{
  "amount": "100"
}
```

Python-specific numeric validation also excludes booleans even though:

```python
isinstance(True, int)  # True
```

### Batch semantics

Ingestion is all-or-nothing:

```text
100 rows submitted
99 valid
1 invalid
↓
0 rows stored
```

This avoids ambiguous partial writes and keeps retries predictable.

### Validation errors

Semantic failures return row-indexed errors:

```json
{
  "detail": {
    "message": "Batch validation failed",
    "row_errors": [
      {
        "row_index": 1,
        "errors": [
          {
            "field": "amount",
            "message": "Expected number, got string"
          }
        ]
      }
    ]
  }
}
```

Status codes:

```text
201 Created
404 Not Found             referenced schema does not exist
422 Unprocessable Entity  validation failed
```

---

# Dashboard Configuration

## `POST /dashboard`

The assignment allows a flexible configuration format. This implementation explicitly includes the schema the dashboard operates on:

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
      "columns": [
        "tradeId",
        "amount",
        "status"
      ]
    }
  ]
}
```

The explicit `schema` reference avoids ambiguous inference and makes the dashboard's data dependency clear.

Supported view types:

```text
summary
table
```

Recommended aggregation compatibility:

```text
number  → sum, avg, count, min, max
string  → count
boolean → count
```

Dashboard configuration is validated when registered:

- referenced schema must exist,
- at least one view is required,
- view type must be supported,
- summary field must exist,
- table columns must exist,
- aggregation must be compatible with field type,
- duplicate table columns are rejected,
- duplicate dashboard names are rejected.

Multiple summaries over the same field are valid when the aggregation differs.

The key invariant is:

> **Every configuration in `DashboardStore` was valid against its referenced schema when registered.**

---

# Dashboard Generation

## `GET /dashboard/{name}`

The dashboard is computed live from the latest ingested data.

Example response:

```json
{
  "success": true,
  "dashboard": "trade-dashboard",
  "views": [
    {
      "type": "summary",
      "field": "amount",
      "aggregation": "sum",
      "value": 215.5
    },
    {
      "type": "table",
      "columns": [
        "tradeId",
        "amount",
        "status"
      ],
      "rows": [
        {
          "tradeId": "T001",
          "amount": 125.5,
          "status": "completed"
        },
        {
          "tradeId": "T002",
          "amount": 90,
          "status": null
        }
      ]
    }
  ]
}
```

## Aggregation semantics

Missing optional values are ignored.

Given:

```json
[
  {"amount": 100},
  {},
  {"amount": 50}
]
```

results are:

```text
sum(amount)   = 150
avg(amount)   = 75
count(amount) = 2
min(amount)   = 50
max(amount)   = 100
```

Empty-result behaviour:

```text
sum([])   → 0
count([]) → 0
avg([])   → null
min([])   → null
max([])   → null
```

This preserves the distinction between an actual zero and an undefined aggregation.

## Table semantics

A table returns exactly the configured columns.

If an optional field is absent, the response normalizes it to `null`:

```json
{
  "tradeId": "T002",
  "amount": 90,
  "status": null
}
```

Configured column order is preserved. Rows remain in current storage/ingestion order.

Pagination, sorting, filtering, and grouping are intentionally outside scope.

---

# API Design

The API uses a small, consistent status-code model:

```text
200 successful retrieval
201 successful creation
404 named/referenced resource does not exist
409 duplicate resource name
422 malformed or semantically invalid input
500 unexpected internal failure
```

Successful responses use a lightweight wrapper:

```json
{
  "success": true
}
```

Errors use FastAPI's standard `detail` shape. Expected client errors retain their
specific messages, while unexpected failures return a generic `Internal server
error` response so implementation details are not exposed. The backend logs
request method, route, and stack trace for unexpected failures; request bodies
are intentionally excluded. Set `LOG_LEVEL` (for example, `DEBUG` or `WARNING`)
to override the default `INFO` level.

---

# Code Quality Decisions

The implementation favors:

```text
small focused modules
explicit validation
thin route handlers
clear ownership of responsibilities
independently testable business logic
```

It intentionally avoids unnecessary assignment-level complexity such as:

```text
database repositories
dependency-injection frameworks
dynamic Pydantic model generation
authentication infrastructure
message queues
caching
schema migration frameworks
generic query languages
```

Module-level singleton stores are appropriate here because the application is explicitly small and in-memory.

---

# Testing Strategy

Important evaluator-visible behaviours should be covered.

## Schema

```text
valid schema registration
duplicate schema → 409
invalid field type → 422
duplicate field names → 422
missing schema → 404
```

## Ingest

```text
valid batch stored
required field missing
unknown field rejected
wrong type rejected
boolean rejected as number
optional field omitted successfully
null rejected for typed optional field
one invalid row rejects whole batch
multiple invalid rows return multiple errors
missing schema → 404
```

## Dashboard configuration

```text
valid dashboard registration
unknown schema
unknown summary field
unknown table column
unsupported aggregation/type combination
duplicate table column
duplicate dashboard → 409
```

## Dashboard generation

```text
sum
avg
count
min
max
missing optional values
empty dataset semantics
table projection
missing optional table fields become null
view order preserved
```

---

# Running the Backend

Run backend commands from the `backend` directory:

```bash
cd backend
```

Install dependencies with uv (recommended):

```bash
uv sync
```

Run FastAPI:

```bash
uvicorn app.main:app --reload
```

API:

```text
http://localhost:8000
```

Interactive documentation:

```text
http://localhost:8000/docs
```

---

# Running Tests

```bash
uv run pytest
```

If the dependencies are already active in your environment:

```bash
pytest -v
```

---

# Running the Frontend

From the frontend directory:

```bash
npm install
npm run dev
```

The frontend is deliberately minimal and exists primarily to demonstrate the backend workflow.

---

# Key Trade-offs

The implementation deliberately favors:

```text
strict validation
over implicit coercion

all-or-nothing ingestion
over partial writes

explicit schema references
over inference

early dashboard validation
over deferred runtime failures

live dashboard computation
over cached/materialized results

simple in-memory storage
over production infrastructure
```

These choices make the application predictable and easy to reason about within the assignment scope.

---

# Productionisation

The current application is intentionally not production-ready.

If productionising it, the same logical boundaries could remain while the infrastructure evolves.

## Persistence

Replace in-memory dictionaries with durable storage such as PostgreSQL. Flexible dashboard configuration could be stored as JSON/JSONB alongside relational metadata.

## Schema versioning

Introduce explicit schema versions:

```text
trade:v1
trade:v2
```

Dashboards should either pin to a version or be revalidated during schema evolution.

## Idempotent ingestion

Support idempotency keys or record-level deduplication so client retries cannot accidentally duplicate data.

## Transactions and consistency

Back all-or-nothing ingestion with real database transactions. Use snapshot/transaction semantics where consistent dashboard reads are required.

## Numeric precision

For financial workloads, use exact decimal types or integer minor units rather than binary floating-point.

## Large batch processing

For large ingestion workloads, move processing behind a queue/stream and worker model, potentially returning `202 Accepted` with a job ID.

## Pagination and sorting

Production table views should support server-side limits, explicit sorting, and pagination, preferably cursor-based for large/changing datasets.

## Filtering and grouping

Add formal support for filters, grouping, time ranges, top-N, sorting, and derived metrics rather than ad-hoc conditionals.

## Caching and precomputation

Cache expensive dashboard results or materialize aggregations when scale requires it. Cache keys should include dashboard/config version and dataset version.

## Authentication and authorization

Add authentication, ownership, tenant/workspace isolation, dataset permissions, and role-based read/write controls.

## Observability

Add structured logging, request IDs, metrics, tracing, dashboard execution latency, rows scanned, cache metrics, validation-failure metrics, and alerting.

## Error contracts

Production clients would benefit from machine-readable error codes and precise validation paths.

---

# Out of Scope

The following are intentionally excluded:

```text
authentication
authorization
database persistence
production deployment
schema migration
advanced visualization
chart/filter builders
LLM integration
distributed processing
caching
message queues
multi-tenant support
```

These are deliberate scope decisions, not missing core requirements.

---

# Evaluation Criteria Mapping

## Schema Design & Validation

Covered by:

- typed schema definitions,
- duplicate detection,
- strict row validation,
- unknown-field rejection,
- required-field validation,
- batch-level atomicity,
- structured validation errors.

## Dashboard Generation Logic

Covered by:

- validated dashboard configuration,
- live execution,
- summary aggregations,
- explicit missing-value semantics,
- empty-dataset handling,
- stable table projection.

## API Design

Covered by:

- small endpoint surface,
- predictable HTTP status codes,
- consistent success/error behaviour,
- early validation,
- explicit resource relationships.

## Code Quality

Covered by:

- separation of concerns,
- thin routes,
- focused store/validator/engine modules,
- type hints,
- independently testable business logic,
- deliberate avoidance of unnecessary complexity.

---

# Summary

The project is intentionally small but built around strong invariants:

> **Schemas define valid data.**

> **Ingestion guarantees stored rows conform to those schemas.**

> **Dashboard registration guarantees stored configurations reference valid fields.**

> **Dashboard generation can therefore focus only on computation.**

The design is optimized for the assignment requirements while preserving clear extension points for a production implementation.
