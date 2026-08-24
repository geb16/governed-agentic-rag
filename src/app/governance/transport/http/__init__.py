"""Expose the authenticated FastAPI router for governed workflow operations."""

from app.governance.transport.http.routes import router

__all__ = ["router"]
