"""
FastAPI application - Main API entry point
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from ..config import settings
from .routers import interviews, call_guides, analytics, health, quality_dashboard

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    logger.info("Starting Expert Interviewers API")
    logger.info(f"Environment: {settings.app_env}")
    yield
    logger.info("Shutting down Expert Interviewers API")


# Create FastAPI app
app = FastAPI(
    title="Expert Interviewers API",
    description="Autonomous Voice Research Interview System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(call_guides.router, prefix="/api/call-guides", tags=["Call Guides"])
app.include_router(interviews.router, prefix="/api/interviews", tags=["Interviews"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(quality_dashboard.router, prefix="/api", tags=["Quality Dashboard"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Expert Interviewers",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
