from __future__ import annotations

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add core modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

# Import core modules
from main import initialize_components  # type: ignore
import main as core  # type: ignore

# Import route modules
from .routes import search, batch, costs, status, export_routes
from .websocket import websocket_manager, websocket_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources."""
    # Startup
    success = initialize_components()
    if not success:
        raise RuntimeError("Failed to initialize core components")
    
    # Store core components in app state
    app.state.config = core.config
    app.state.db = core.db
    app.state.scraper = core.scraper
    app.state.enricher = core.enricher
    app.state.exporter = core.exporter
    app.state.hubspot = core.hubspot
    app.state.rate_limiter = core.rate_limiter
    app.state.proxy_manager = core.proxy_manager
    
    print("✅ GMaps Lead Generator API started successfully")
    yield
    
    # Shutdown
    print("🔄 Shutting down GMaps Lead Generator API...")


# Create FastAPI app
app = FastAPI(
    title="GMaps Lead Generator API",
    description="API for Google Maps lead generation and enrichment",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for Electron frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "app://.", "tauri://localhost"],  # Vite, CRA, Electron, Tauri
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route modules
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(batch.router, prefix="/api/batch", tags=["batch"])
app.include_router(costs.router, prefix="/api/costs", tags=["costs"])
app.include_router(status.router, prefix="/api/status", tags=["status"])
app.include_router(export_routes.router, prefix="/api/export", tags=["export"])

# WebSocket endpoint
app.add_websocket_route("/ws", websocket_endpoint)

# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "GMaps Lead Generator API is running"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "GMaps Lead Generator API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )