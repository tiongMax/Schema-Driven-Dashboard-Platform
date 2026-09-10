# Backend

This is a FastAPI backend project managed by [uv](https://github.com/astral-sh/uv).

## Setup

If you haven't already, the dependencies will be automatically installed when you use `uv run`. 

## Running the API

You can start the development server by running:

```bash
uv run python main.py
```

Alternatively, you can run uvicorn directly:

```bash
uv run uvicorn main:app --reload
```

The API will be available at `http://127.0.0.0:8000` (or `http://localhost:8000`), with standard FastAPI interactive Swagger documentation at `http://localhost:8000/docs`.
