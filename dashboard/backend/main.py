"""LLM Serve Dashboard - FastAPI Application Entrypoint."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(
    title="LLM Serve Dashboard",
    description="Centralized control plane for LLM cluster management",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Mount static files if the directory exists (production mode)
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
