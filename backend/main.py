"""
Main application module for the Schema-Driven Dashboard API.

This module initializes the FastAPI application instance and includes
all the standard routers needed for the backend services.
"""

from fastapi import FastAPI
from routes.schemas import router as schema_router


app = FastAPI(
    title="Schema-Driven Dashboard API",
    description="An API to register and manage schemas for the dashboard",
    version="1.0.0",
)
app.include_router(schema_router)