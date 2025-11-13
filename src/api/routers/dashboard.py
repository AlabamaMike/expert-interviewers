"""
Dashboard and monitoring endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta

from ...data.connection import get_db
from ...data.database import (
    InterviewModel, InterviewResponseModel, MetricsModel,
    InterviewStatusEnum, CallGuideModel
)
from ...monitoring.quality_monitor import QualityMonitor

router = APIRouter()

# Global quality monitor
quality_monitor = QualityMonitor()


@router.get("/overview")
async def get_dashboard_overview(
    hours: int = Query(default=24, description="Time window in hours"),
    db: Session = Depends(get_db)
):
    """Get dashboard overview with key metrics"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Total interviews by status
    interview_counts = db.query(
        InterviewModel.status,
        func.count(InterviewModel.id).label("count")
    ).filter(
        InterviewModel.created_at >= cutoff
    ).group_by(
        InterviewModel.status
    ).all()

    status_counts = {status.value: 0 for status in InterviewStatusEnum}
    for status, count in interview_counts:
        status_counts[status.value] = count

    # Completed interviews metrics
    completed_interviews = db.query(InterviewModel).filter(
        and_(
            InterviewModel.status == InterviewStatusEnum.COMPLETED,
            InterviewModel.completed_at >= cutoff
        )
    ).all()

    avg_duration = 0
    avg_completion_rate = 0
    avg_engagement = 0

    if completed_interviews:
        durations = [i.duration_seconds for i in completed_interviews if i.duration_seconds]
        if durations:
            avg_duration = sum(durations) / len(durations)

        completion_rates = [
            i.quality_metrics.get("completion_percentage", 0)
            for i in completed_interviews
            if i.quality_metrics
        ]
        if completion_rates:
            avg_completion_rate = sum(completion_rates) / len(completion_rates)

        engagement_scores = [
            i.engagement_metrics.get("overall_engagement", 0)
            for i in completed_interviews
            if i.engagement_metrics
        ]
        if engagement_scores:
            avg_engagement = sum(engagement_scores) / len(engagement_scores)

    # Response counts
    response_count = db.query(func.count(InterviewResponseModel.id)).filter(
        InterviewResponseModel.created_at >= cutoff
    ).scalar()

    # Quality summary
    quality_summary = quality_monitor.get_quality_summary(time_window_hours=hours)

    return {
        "time_window_hours": hours,
        "interviews": {
            "total": sum(status_counts.values()),
            "by_status": status_counts
        },
        "performance": {
            "avg_duration_seconds": round(avg_duration, 1),
            "avg_completion_rate": round(avg_completion_rate, 3),
            "avg_engagement_score": round(avg_engagement, 3),
            "total_responses": response_count
        },
        "quality": quality_summary,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/call-guides/performance")
async def get_call_guide_performance(
    hours: int = Query(default=168, description="Time window in hours (default: 7 days)"),
    db: Session = Depends(get_db)
):
    """Get performance metrics by call guide"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Get all call guides with their interview stats
    call_guides = db.query(CallGuideModel).all()

    performance_data = []

    for guide in call_guides:
        interviews = db.query(InterviewModel).filter(
            and_(
                InterviewModel.call_guide_id == guide.id,
                InterviewModel.created_at >= cutoff
            )
        ).all()

        if not interviews:
            continue

        total_count = len(interviews)
        completed = [i for i in interviews if i.status == InterviewStatusEnum.COMPLETED]
        completed_count = len(completed)

        # Calculate averages for completed interviews
        avg_duration = 0
        avg_completion = 0
        avg_engagement = 0
        avg_quality = 0

        if completed:
            durations = [i.duration_seconds for i in completed if i.duration_seconds]
            if durations:
                avg_duration = sum(durations) / len(durations)

            completions = [
                i.quality_metrics.get("completion_percentage", 0)
                for i in completed
                if i.quality_metrics
            ]
            if completions:
                avg_completion = sum(completions) / len(completions)

            engagements = [
                i.engagement_metrics.get("overall_engagement", 0)
                for i in completed
                if i.engagement_metrics
            ]
            if engagements:
                avg_engagement = sum(engagements) / len(engagements)

        performance_data.append({
            "call_guide_id": str(guide.id),
            "call_guide_name": guide.name,
            "interviews": {
                "total": total_count,
                "completed": completed_count,
                "completion_rate": completed_count / total_count if total_count > 0 else 0
            },
            "metrics": {
                "avg_duration_seconds": round(avg_duration, 1),
                "avg_completion_percentage": round(avg_completion, 3),
                "avg_engagement_score": round(avg_engagement, 3)
            }
        })

    return {
        "time_window_hours": hours,
        "call_guides": performance_data,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/sentiment-trends")
async def get_sentiment_trends(
    call_guide_id: Optional[str] = None,
    hours: int = Query(default=168, description="Time window in hours"),
    db: Session = Depends(get_db)
):
    """Get sentiment trends over time"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    query = db.query(InterviewResponseModel).filter(
        InterviewResponseModel.created_at >= cutoff
    )

    if call_guide_id:
        query = query.join(InterviewModel).filter(
            InterviewModel.call_guide_id == call_guide_id
        )

    responses = query.all()

    # Group by time buckets (hourly)
    sentiment_by_hour = {}

    for response in responses:
        if not response.sentiment or not response.created_at:
            continue

        # Round to hour
        hour_key = response.created_at.replace(minute=0, second=0, microsecond=0)
        hour_str = hour_key.isoformat()

        if hour_str not in sentiment_by_hour:
            sentiment_by_hour[hour_str] = {
                "very_positive": 0,
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "very_negative": 0,
                "total": 0
            }

        sentiment_by_hour[hour_str][response.sentiment.value] += 1
        sentiment_by_hour[hour_str]["total"] += 1

    # Convert to time series
    time_series = []
    for hour_str, counts in sorted(sentiment_by_hour.items()):
        time_series.append({
            "timestamp": hour_str,
            "sentiments": counts
        })

    return {
        "time_window_hours": hours,
        "call_guide_id": call_guide_id,
        "time_series": time_series,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/quality-alerts")
async def get_quality_alerts(
    severity: Optional[str] = None,
    hours: int = Query(default=24, description="Time window in hours")
):
    """Get recent quality alerts"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    recent_alerts = [
        a for a in quality_monitor.alerts
        if a.timestamp > cutoff
    ]

    if severity:
        recent_alerts = [a for a in recent_alerts if a.severity.value == severity.lower()]

    return {
        "time_window_hours": hours,
        "total_alerts": len(recent_alerts),
        "alerts": [
            {
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp.isoformat(),
                "interview_id": str(alert.interview_id) if alert.interview_id else None
            }
            for alert in sorted(recent_alerts, key=lambda x: x.timestamp, reverse=True)
        ],
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/themes")
async def get_common_themes(
    call_guide_id: Optional[str] = None,
    hours: int = Query(default=168, description="Time window in hours"),
    limit: int = Query(default=20, description="Number of themes to return"),
    db: Session = Depends(get_db)
):
    """Get common themes from interviews"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    query = db.query(InterviewResponseModel).filter(
        InterviewResponseModel.created_at >= cutoff
    )

    if call_guide_id:
        query = query.join(InterviewModel).filter(
            InterviewModel.call_guide_id == call_guide_id
        )

    responses = query.all()

    # Count theme occurrences
    theme_counts = {}
    for response in responses:
        if not response.themes:
            continue
        for theme in response.themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

    # Sort by frequency
    sorted_themes = sorted(
        theme_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]

    return {
        "time_window_hours": hours,
        "call_guide_id": call_guide_id,
        "total_unique_themes": len(theme_counts),
        "themes": [
            {"theme": theme, "frequency": count}
            for theme, count in sorted_themes
        ],
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/response-quality")
async def get_response_quality_distribution(
    hours: int = Query(default=168, description="Time window in hours"),
    db: Session = Depends(get_db)
):
    """Get distribution of response quality metrics"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    responses = db.query(InterviewResponseModel).filter(
        InterviewResponseModel.created_at >= cutoff
    ).all()

    # Bucket information density scores
    density_buckets = {
        "0.0-0.2": 0,
        "0.2-0.4": 0,
        "0.4-0.6": 0,
        "0.6-0.8": 0,
        "0.8-1.0": 0
    }

    confidence_buckets = {
        "0.0-0.2": 0,
        "0.2-0.4": 0,
        "0.4-0.6": 0,
        "0.6-0.8": 0,
        "0.8-1.0": 0
    }

    for response in responses:
        # Information density
        if response.information_density is not None:
            density = response.information_density
            if density < 0.2:
                density_buckets["0.0-0.2"] += 1
            elif density < 0.4:
                density_buckets["0.2-0.4"] += 1
            elif density < 0.6:
                density_buckets["0.4-0.6"] += 1
            elif density < 0.8:
                density_buckets["0.6-0.8"] += 1
            else:
                density_buckets["0.8-1.0"] += 1

        # Confidence score
        if response.confidence_score is not None:
            confidence = response.confidence_score
            if confidence < 0.2:
                confidence_buckets["0.0-0.2"] += 1
            elif confidence < 0.4:
                confidence_buckets["0.2-0.4"] += 1
            elif confidence < 0.6:
                confidence_buckets["0.4-0.6"] += 1
            elif confidence < 0.8:
                confidence_buckets["0.6-0.8"] += 1
            else:
                confidence_buckets["0.8-1.0"] += 1

    return {
        "time_window_hours": hours,
        "total_responses": len(responses),
        "information_density_distribution": density_buckets,
        "confidence_score_distribution": confidence_buckets,
        "generated_at": datetime.utcnow().isoformat()
    }
