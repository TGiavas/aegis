"""
Analytics Service - processes events and creates alerts.

This service:
1. Consumes events from RabbitMQ
2. Evaluates alert rules
3. Creates alerts when conditions are met

It also exposes a simple health check endpoint.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.consumer import start_consumer


# =============================================================================
# LIFESPAN
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown."""
    print("🚀 Starting Analytics Service...")
    
    # Start the consumer as a background task
    consumer_task = asyncio.create_task(start_consumer())
    
    yield
    
    # Shutdown
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    
    print("👋 Analytics Service stopped")


# =============================================================================
# APP
# =============================================================================


app = FastAPI(
    title="Aegis Analytics Service",
    description="Event analysis and alert generation",
    version="0.1.0",
    lifespan=lifespan,
)


# =============================================================================
# ENDPOINTS
# =============================================================================


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"], include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "analytics_service"}

