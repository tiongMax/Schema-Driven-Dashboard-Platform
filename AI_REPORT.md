# AI Usage Report

## AI Tools Used

I used **ChatGPT / Codex** as a development copilot during the assignment. I mainly used it to accelerate design discussions, identify edge cases, compare implementation trade-offs, and review whether the solution aligned with the evaluation criteria.

I used it to surface alternatives quickly, then made the final design decisions based on the assignment specification, implementation scope, and expected behaviour.

## Example Prompts

Representative prompts included:

- “Discuss the trade-offs between strict type validation and implicit coercion, and between all-or-nothing batch ingestion and partial ingestion.”
- “How should the dashboard configuration identify which ingested dataset it operates on if the configuration format is flexible?”
- “How should `sum`, `avg`, `count`, `min`, and `max` behave when optional values are missing or the dataset is empty?”
- “Review the implementation against the evaluation criteria: Schema Design & Validation, Dashboard Generation Logic, API Design, and Code Quality.”

These prompts helped reduce time spent exploring design alternatives manually and made it easier to focus implementation effort on the assignment’s core requirements.

## One AI Suggestion I Accepted

One suggestion I accepted was to include an explicit `schema` field in each dashboard configuration.

The assignment example shows the dashboard name and views, but the configuration format is flexible. Without an explicit schema reference, the backend would need to infer which ingested dataset the dashboard should use.

I accepted the suggestion because it makes the dependency explicit:

```text
Dashboard → Schema → Ingested Data
```

It also allows invalid field references to be detected when the dashboard is registered instead of failing later during dashboard generation.

## One AI Suggestion I Rejected

I considered introducing a dedicated `IngestionService` layer to coordinate schema lookup, row validation, and storage.

I rejected this for the assignment because the application is intentionally small and time-boxed. The route already delegates validation and storage to focused modules, so an additional service layer would add abstraction without providing enough benefit.

For a larger production application with multiple ingestion entry points, retries, authorization, transactions, or asynchronous processing, I would reconsider introducing such a service boundary.

## How I Validated the Solution

I validated the solution by checking the implementation against the assignment specification rather than relying on AI-generated assumptions.

I also considered both normal and edge cases, including:

- duplicate schemas and duplicate field definitions,
- missing required fields,
- unknown fields,
- strict type mismatches,
- Python’s `bool`/`int` edge case for numeric validation,
- invalid dashboard field references,
- incompatible aggregations,
- missing optional values,
- empty datasets,
- and all-or-nothing batch ingestion.

For API behaviour, I verified that resource creation, missing resources, duplicates, and invalid inputs use consistent HTTP semantics (`201`, `404`, `409`, and `422`).

The main principle I followed was to use AI to **accelerate exploration and review**, while keeping the final decisions and validation grounded in the specification and observable application behaviour.
