"""
Quality monitoring and alerting
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class QualityAlert:
    """Quality alert"""
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime
    interview_id: Optional[str] = None
    call_guide_id: Optional[str] = None


class QualityThresholds:
    """Quality thresholds for monitoring"""

    # Interview completion
    MIN_COMPLETION_RATE = 0.7  # 70%
    MIN_ENGAGEMENT_SCORE = 0.5  # 50%

    # Response quality
    MIN_INFORMATION_DENSITY = 0.3  # 30%
    MAX_CLARIFICATION_RATE = 0.4  # 40%

    # Technical quality
    MAX_STT_ERROR_RATE = 0.05  # 5%
    MAX_RESPONSE_LATENCY = 3.0  # 3 seconds
    MIN_STT_CONFIDENCE = 0.8  # 80%

    # Follow-up effectiveness
    MIN_FOLLOW_UP_VALUE = 0.5  # 50%

    # Overall quality
    MIN_DATA_QUALITY_SCORE = 0.6  # 60%


class QualityMonitor:
    """
    Monitors interview quality in real-time and generates alerts
    """

    def __init__(self, thresholds: Optional[QualityThresholds] = None):
        """
        Initialize quality monitor

        Args:
            thresholds: Quality thresholds (uses defaults if None)
        """
        self.thresholds = thresholds or QualityThresholds()
        self.alerts: List[QualityAlert] = []
        logger.info("QualityMonitor initialized")

    def check_interview_quality(self, interview_data: Dict[str, Any]) -> List[QualityAlert]:
        """
        Check overall interview quality

        Args:
            interview_data: Interview metrics and data

        Returns:
            List of quality alerts
        """
        alerts = []

        # Check completion rate
        completion_rate = interview_data.get("completion_rate", 0)
        if completion_rate < self.thresholds.MIN_COMPLETION_RATE:
            alerts.append(QualityAlert(
                severity=AlertSeverity.WARNING,
                title="Low Completion Rate",
                description=f"Interview completion rate ({completion_rate:.1%}) is below threshold ({self.thresholds.MIN_COMPLETION_RATE:.1%})",
                metric_name="completion_rate",
                current_value=completion_rate,
                threshold=self.thresholds.MIN_COMPLETION_RATE,
                timestamp=datetime.utcnow(),
                interview_id=interview_data.get("interview_id")
            ))

        # Check engagement score
        engagement_score = interview_data.get("engagement_score", 0)
        if engagement_score < self.thresholds.MIN_ENGAGEMENT_SCORE:
            alerts.append(QualityAlert(
                severity=AlertSeverity.WARNING,
                title="Low Engagement",
                description=f"Respondent engagement ({engagement_score:.2f}) is below threshold ({self.thresholds.MIN_ENGAGEMENT_SCORE:.2f})",
                metric_name="engagement_score",
                current_value=engagement_score,
                threshold=self.thresholds.MIN_ENGAGEMENT_SCORE,
                timestamp=datetime.utcnow(),
                interview_id=interview_data.get("interview_id")
            ))

        # Check data quality
        data_quality = interview_data.get("data_quality_score", 0)
        if data_quality < self.thresholds.MIN_DATA_QUALITY_SCORE:
            alerts.append(QualityAlert(
                severity=AlertSeverity.ERROR,
                title="Low Data Quality",
                description=f"Data quality score ({data_quality:.2f}) is below threshold ({self.thresholds.MIN_DATA_QUALITY_SCORE:.2f})",
                metric_name="data_quality_score",
                current_value=data_quality,
                threshold=self.thresholds.MIN_DATA_QUALITY_SCORE,
                timestamp=datetime.utcnow(),
                interview_id=interview_data.get("interview_id")
            ))

        self.alerts.extend(alerts)
        return alerts

    def check_response_quality(self, response_data: Dict[str, Any]) -> List[QualityAlert]:
        """
        Check response quality

        Args:
            response_data: Response metrics and data

        Returns:
            List of quality alerts
        """
        alerts = []

        # Check information density
        info_density = response_data.get("information_density", 0)
        if info_density < self.thresholds.MIN_INFORMATION_DENSITY:
            alerts.append(QualityAlert(
                severity=AlertSeverity.INFO,
                title="Low Information Density",
                description=f"Response information density ({info_density:.2f}) is low",
                metric_name="information_density",
                current_value=info_density,
                threshold=self.thresholds.MIN_INFORMATION_DENSITY,
                timestamp=datetime.utcnow(),
                interview_id=response_data.get("interview_id")
            ))

        # Check STT confidence
        stt_confidence = response_data.get("stt_confidence", 1.0)
        if stt_confidence < self.thresholds.MIN_STT_CONFIDENCE:
            alerts.append(QualityAlert(
                severity=AlertSeverity.WARNING,
                title="Low STT Confidence",
                description=f"Speech recognition confidence ({stt_confidence:.2f}) is below threshold",
                metric_name="stt_confidence",
                current_value=stt_confidence,
                threshold=self.thresholds.MIN_STT_CONFIDENCE,
                timestamp=datetime.utcnow(),
                interview_id=response_data.get("interview_id")
            ))

        self.alerts.extend(alerts)
        return alerts

    def check_technical_quality(self, technical_data: Dict[str, Any]) -> List[QualityAlert]:
        """
        Check technical quality metrics

        Args:
            technical_data: Technical metrics

        Returns:
            List of quality alerts
        """
        alerts = []

        # Check response latency
        latency = technical_data.get("response_latency", 0)
        if latency > self.thresholds.MAX_RESPONSE_LATENCY:
            alerts.append(QualityAlert(
                severity=AlertSeverity.WARNING,
                title="High Response Latency",
                description=f"Response latency ({latency:.2f}s) exceeds threshold ({self.thresholds.MAX_RESPONSE_LATENCY}s)",
                metric_name="response_latency",
                current_value=latency,
                threshold=self.thresholds.MAX_RESPONSE_LATENCY,
                timestamp=datetime.utcnow()
            ))

        # Check STT error rate
        stt_error_rate = technical_data.get("stt_error_rate", 0)
        if stt_error_rate > self.thresholds.MAX_STT_ERROR_RATE:
            alerts.append(QualityAlert(
                severity=AlertSeverity.ERROR,
                title="High STT Error Rate",
                description=f"STT error rate ({stt_error_rate:.1%}) exceeds threshold ({self.thresholds.MAX_STT_ERROR_RATE:.1%})",
                metric_name="stt_error_rate",
                current_value=stt_error_rate,
                threshold=self.thresholds.MAX_STT_ERROR_RATE,
                timestamp=datetime.utcnow()
            ))

        self.alerts.extend(alerts)
        return alerts

    def should_escalate(self, interview_data: Dict[str, Any]) -> bool:
        """
        Determine if interview should be escalated to human

        Args:
            interview_data: Interview data and metrics

        Returns:
            True if should escalate
        """
        # Escalate if critical quality issues
        recent_alerts = [
            a for a in self.alerts
            if a.timestamp > datetime.utcnow() - timedelta(minutes=5)
            and a.interview_id == interview_data.get("interview_id")
        ]

        critical_alerts = [a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL]
        error_alerts = [a for a in recent_alerts if a.severity == AlertSeverity.ERROR]

        # Escalate if any critical alerts or multiple errors
        if critical_alerts or len(error_alerts) >= 3:
            logger.warning(f"Escalating interview {interview_data.get('interview_id')}: {len(critical_alerts)} critical, {len(error_alerts)} errors")
            return True

        # Escalate if completion very low
        if interview_data.get("completion_rate", 1.0) < 0.3:
            logger.warning(f"Escalating interview {interview_data.get('interview_id')}: very low completion")
            return True

        # Escalate if quality extremely poor
        if interview_data.get("data_quality_score", 1.0) < 0.3:
            logger.warning(f"Escalating interview {interview_data.get('interview_id')}: very low quality")
            return True

        return False

    def get_quality_summary(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Get quality summary for recent period

        Args:
            time_window_hours: Hours to look back

        Returns:
            Dict with quality summary
        """
        cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_alerts = [a for a in self.alerts if a.timestamp > cutoff]

        summary = {
            "time_window_hours": time_window_hours,
            "total_alerts": len(recent_alerts),
            "by_severity": {
                "critical": len([a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL]),
                "error": len([a for a in recent_alerts if a.severity == AlertSeverity.ERROR]),
                "warning": len([a for a in recent_alerts if a.severity == AlertSeverity.WARNING]),
                "info": len([a for a in recent_alerts if a.severity == AlertSeverity.INFO]),
            },
            "by_metric": {},
            "top_issues": []
        }

        # Count by metric
        for alert in recent_alerts:
            metric = alert.metric_name
            summary["by_metric"][metric] = summary["by_metric"].get(metric, 0) + 1

        # Get top issues
        if summary["by_metric"]:
            top_metrics = sorted(
                summary["by_metric"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            summary["top_issues"] = [
                {"metric": metric, "count": count}
                for metric, count in top_metrics
            ]

        return summary

    def clear_old_alerts(self, hours: int = 72):
        """Clear alerts older than specified hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        original_count = len(self.alerts)
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff]
        removed = original_count - len(self.alerts)
        if removed > 0:
            logger.info(f"Cleared {removed} old alerts")
