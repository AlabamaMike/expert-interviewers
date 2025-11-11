"""
Quality Dashboard API Router
Endpoints for quality monitoring and dashboard
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from ...monitoring.quality_monitor import (
    QualityMonitor,
    QualityAlert,
    QualityReport,
    QualityThreshold,
    MetricSnapshot,
    AlertSeverity,
    MetricStatus
)

router = APIRouter(prefix="/quality", tags=["quality-dashboard"])

# Global quality monitor instance (in production, this should be properly managed)
_quality_monitor: Optional[QualityMonitor] = None


def get_quality_monitor() -> QualityMonitor:
    """Get or create quality monitor instance"""
    global _quality_monitor
    if _quality_monitor is None:
        _quality_monitor = QualityMonitor()
    return _quality_monitor


# Request/Response Models

class QualityReportResponse(BaseModel):
    """Quality report response"""
    report_id: str
    generated_at: datetime
    time_window_hours: float
    overall_status: MetricStatus
    health_score: float
    total_interviews: int
    completed_interviews: int
    failed_interviews: int
    avg_completion_rate: float
    avg_engagement_score: float
    avg_response_quality: float
    active_alerts_count: int
    issues_detected: List[str]
    recommendations: List[str]
    trends: dict


class MetricSnapshotResponse(BaseModel):
    """Metric snapshot response"""
    metric_name: str
    value: float
    timestamp: datetime
    status: MetricStatus
    interview_id: Optional[str] = None


class AlertResponse(BaseModel):
    """Alert response"""
    alert_id: str
    severity: AlertSeverity
    metric_name: str
    message: str
    current_value: float
    threshold_value: float
    interview_id: Optional[str] = None
    timestamp: datetime
    acknowledged: bool
    resolved: bool


class ThresholdConfigRequest(BaseModel):
    """Threshold configuration request"""
    metric_name: str
    warning_threshold: float
    error_threshold: float
    critical_threshold: float
    comparison: str = "greater_than"
    window_size: int = 10
    enabled: bool = True


class AlertAcknowledgeRequest(BaseModel):
    """Alert acknowledge request"""
    acknowledged_by: str


class AlertResolveRequest(BaseModel):
    """Alert resolve request"""
    resolved_by: str


# Endpoints

@router.get("/dashboard", response_model=QualityReportResponse)
async def get_quality_dashboard(
    hours: int = Query(default=1, ge=1, le=168, description="Time window in hours"),
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    Get quality dashboard overview

    Returns comprehensive quality metrics for the specified time window.
    """
    try:
        time_window = timedelta(hours=hours)
        report = await monitor.generate_report(time_window)

        return QualityReportResponse(
            report_id=report.report_id,
            generated_at=report.generated_at,
            time_window_hours=hours,
            overall_status=report.overall_status,
            health_score=report.health_score,
            total_interviews=report.total_interviews,
            completed_interviews=report.completed_interviews,
            failed_interviews=report.failed_interviews,
            avg_completion_rate=report.avg_completion_rate,
            avg_engagement_score=report.avg_engagement_score,
            avg_response_quality=report.avg_response_quality,
            active_alerts_count=len(report.active_alerts),
            issues_detected=report.issues_detected,
            recommendations=report.recommendations,
            trends=report.trends
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard: {str(e)}")


@router.get("/metrics/{metric_name}", response_model=List[MetricSnapshotResponse])
async def get_metric_history(
    metric_name: str,
    limit: Optional[int] = Query(default=100, ge=1, le=1000),
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    Get history for a specific metric

    Returns time-series data for the requested metric.
    """
    try:
        history = monitor.get_metric_history(metric_name, limit)

        return [
            MetricSnapshotResponse(
                metric_name=snapshot.metric_name,
                value=snapshot.value,
                timestamp=snapshot.timestamp,
                status=snapshot.status,
                interview_id=snapshot.interview_id
            )
            for snapshot in history
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metric history: {str(e)}")


@router.get("/metrics", response_model=List[str])
async def list_available_metrics(
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    List all available metrics being tracked
    """
    return list(monitor.metric_history.keys())


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    severity: Optional[AlertSeverity] = Query(default=None),
    include_resolved: bool = Query(default=False),
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    Get active alerts, optionally filtered by severity
    """
    try:
        if include_resolved:
            alerts = list(monitor.alert_history)
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
        else:
            alerts = monitor.get_active_alerts(severity)

        return [
            AlertResponse(
                alert_id=alert.alert_id,
                severity=alert.severity,
                metric_name=alert.metric_name,
                message=alert.message,
                current_value=alert.current_value,
                threshold_value=alert.threshold_value,
                interview_id=alert.interview_id,
                timestamp=alert.timestamp,
                acknowledged=alert.acknowledged,
                resolved=alert.resolved
            )
            for alert in alerts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    request: AlertAcknowledgeRequest,
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    Acknowledge an alert
    """
    try:
        monitor.acknowledge_alert(alert_id, request.acknowledged_by)
        return {"status": "acknowledged", "alert_id": alert_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    request: AlertResolveRequest,
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    Resolve an alert
    """
    try:
        monitor.resolve_alert(alert_id, request.resolved_by)
        return {"status": "resolved", "alert_id": alert_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving alert: {str(e)}")


@router.get("/thresholds", response_model=List[dict])
async def get_thresholds(
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    Get current quality thresholds
    """
    return [
        {
            "metric_name": t.metric_name,
            "warning_threshold": t.warning_threshold,
            "error_threshold": t.error_threshold,
            "critical_threshold": t.critical_threshold,
            "comparison": t.comparison,
            "window_size": t.window_size,
            "enabled": t.enabled
        }
        for t in monitor.thresholds
    ]


@router.put("/thresholds/{metric_name}")
async def update_threshold(
    metric_name: str,
    request: ThresholdConfigRequest,
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    Update threshold configuration for a metric
    """
    try:
        # Find and update threshold
        for threshold in monitor.thresholds:
            if threshold.metric_name == metric_name:
                threshold.warning_threshold = request.warning_threshold
                threshold.error_threshold = request.error_threshold
                threshold.critical_threshold = request.critical_threshold
                threshold.comparison = request.comparison
                threshold.window_size = request.window_size
                threshold.enabled = request.enabled
                return {"status": "updated", "metric_name": metric_name}

        # If not found, add new threshold
        new_threshold = QualityThreshold(
            metric_name=request.metric_name,
            warning_threshold=request.warning_threshold,
            error_threshold=request.error_threshold,
            critical_threshold=request.critical_threshold,
            comparison=request.comparison,
            window_size=request.window_size,
            enabled=request.enabled
        )
        monitor.thresholds.append(new_threshold)

        # Initialize metric history for new threshold
        if metric_name not in monitor.metric_history:
            from collections import deque
            monitor.metric_history[metric_name] = deque(maxlen=new_threshold.window_size)

        return {"status": "created", "metric_name": metric_name}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating threshold: {str(e)}")


@router.get("/health")
async def get_system_health(
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    Get current system health status

    Quick endpoint for health checks and monitoring systems.
    """
    try:
        report = await monitor.generate_report(timedelta(minutes=15))

        return {
            "status": report.overall_status.value,
            "health_score": report.health_score,
            "timestamp": datetime.utcnow().isoformat(),
            "active_critical_alerts": len([
                a for a in report.active_alerts
                if a.severity == AlertSeverity.CRITICAL and not a.resolved
            ]),
            "interviews_in_progress": len(monitor.interviews_in_progress),
            "recent_completed": report.completed_interviews
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/statistics")
async def get_statistics(
    hours: int = Query(default=24, ge=1, le=168),
    monitor: QualityMonitor = Depends(get_quality_monitor)
):
    """
    Get detailed statistics for the time window
    """
    try:
        time_window = timedelta(hours=hours)
        cutoff_time = datetime.utcnow() - time_window

        # Filter recent completed interviews
        recent_interviews = [
            i for i in monitor.completed_interviews
            if i.completed_at and i.completed_at > cutoff_time
        ]

        if not recent_interviews:
            return {
                "time_window_hours": hours,
                "total_interviews": 0,
                "message": "No interviews in time window"
            }

        # Calculate detailed statistics
        durations = [i.duration_seconds / 60 for i in recent_interviews]
        engagement_scores = [i.engagement_metrics.overall_engagement for i in recent_interviews]
        completion_rates = [i.quality_metrics.completion_percentage for i in recent_interviews]

        import statistics

        return {
            "time_window_hours": hours,
            "total_interviews": len(recent_interviews),
            "duration_stats": {
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
                "min": min(durations),
                "max": max(durations)
            },
            "engagement_stats": {
                "mean": statistics.mean(engagement_scores),
                "median": statistics.median(engagement_scores),
                "stdev": statistics.stdev(engagement_scores) if len(engagement_scores) > 1 else 0,
                "min": min(engagement_scores),
                "max": max(engagement_scores)
            },
            "completion_stats": {
                "mean": statistics.mean(completion_rates),
                "median": statistics.median(completion_rates),
                "stdev": statistics.stdev(completion_rates) if len(completion_rates) > 1 else 0,
                "min": min(completion_rates),
                "max": max(completion_rates)
            },
            "status_distribution": {
                "completed": len([i for i in recent_interviews if i.status == "completed"]),
                "failed": len([i for i in recent_interviews if i.status == "failed"]),
                "partial": len([i for i in recent_interviews if i.status not in ["completed", "failed"]])
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating statistics: {str(e)}")
