"""
Health check endpoints
"""

from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Expert Interviewers"
    }


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check - verify all dependencies are available"""
    checks = {
        "api": "healthy",
        # Add checks for:
        # - Database connection
        # - Redis connection
        # - External API availability (Deepgram, ElevenLabs, Claude)
    }

    all_healthy = all(status == "healthy" for status in checks.values())

    return {
        "ready": all_healthy,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Liveness check"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
