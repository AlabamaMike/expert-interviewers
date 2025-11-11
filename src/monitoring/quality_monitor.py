"""
Quality Monitoring System
Real-time quality metrics tracking and alerting
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
from collections import deque
import asyncio

from ..models.interview import Interview, InterviewResponse
from ..models.analytics import TrendAnalysis

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricStatus(str, Enum):
    """Status of a metric"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class QualityThreshold:
    """Threshold configuration for a metric"""
    metric_name: str
    warning_threshold: float
    error_threshold: float
    critical_threshold: float
    comparison: str = "greater_than"  # greater_than, less_than
    window_size: int = 10  # Number of data points to consider
    enabled: bool = True


@dataclass
class QualityAlert:
    """Quality alert"""
    alert_id: str
    severity: AlertSeverity
    metric_name: str
    message: str
    current_value: float
    threshold_value: float
    interview_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSnapshot:
    """Snapshot of a metric at a point in time"""
    metric_name: str
    value: float
    timestamp: datetime
    interview_id: Optional[str] = None
    status: MetricStatus = MetricStatus.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    """Quality monitoring report"""
    report_id: str
    generated_at: datetime
    time_window: timedelta

    # Overall health
    overall_status: MetricStatus
    health_score: float  # 0.0 to 1.0

    # Metrics
    metric_snapshots: List[MetricSnapshot]

    # Alerts
    active_alerts: List[QualityAlert]

    # Statistics
    total_interviews: int
    completed_interviews: int
    failed_interviews: int
    avg_completion_rate: float
    avg_engagement_score: float
    avg_response_quality: float

    # Trends
    trends: Dict[str, str]  # metric_name -> trend_direction

    # Issues
    issues_detected: List[str]
    recommendations: List[str]


class QualityMonitor:
    """Real-time quality monitoring system"""

    def __init__(
        self,
        thresholds: Optional[List[QualityThreshold]] = None,
        alert_callback: Optional[Callable[[QualityAlert], None]] = None
    ):
        """
        Initialize quality monitor

        Args:
            thresholds: List of quality thresholds to monitor
            alert_callback: Optional callback function for alerts
        """
        self.thresholds = thresholds or self._default_thresholds()
        self.alert_callback = alert_callback

        # Storage for metrics and alerts
        self.metric_history: Dict[str, deque] = {}
        self.active_alerts: List[QualityAlert] = []
        self.alert_history: deque = deque(maxlen=1000)

        # Interview tracking
        self.interviews_in_progress: Dict[str, Interview] = {}
        self.completed_interviews: deque = deque(maxlen=100)

        # Initialize metric history
        for threshold in self.thresholds:
            self.metric_history[threshold.metric_name] = deque(
                maxlen=threshold.window_size
            )

        logger.info("Initialized QualityMonitor")

    def _default_thresholds(self) -> List[QualityThreshold]:
        """Default quality thresholds"""
        return [
            # Engagement thresholds
            QualityThreshold(
                metric_name="engagement_score",
                warning_threshold=0.5,
                error_threshold=0.3,
                critical_threshold=0.2,
                comparison="less_than"
            ),
            # Completion rate thresholds
            QualityThreshold(
                metric_name="completion_rate",
                warning_threshold=0.7,
                error_threshold=0.5,
                critical_threshold=0.3,
                comparison="less_than"
            ),
            # Response quality thresholds
            QualityThreshold(
                metric_name="response_quality",
                warning_threshold=0.6,
                error_threshold=0.4,
                critical_threshold=0.2,
                comparison="less_than"
            ),
            # Error rate thresholds
            QualityThreshold(
                metric_name="error_rate",
                warning_threshold=0.1,
                error_threshold=0.2,
                critical_threshold=0.3,
                comparison="greater_than"
            ),
            # STT accuracy thresholds
            QualityThreshold(
                metric_name="stt_accuracy",
                warning_threshold=0.9,
                error_threshold=0.85,
                critical_threshold=0.8,
                comparison="less_than"
            ),
            # Response latency thresholds (seconds)
            QualityThreshold(
                metric_name="response_latency",
                warning_threshold=3.0,
                error_threshold=5.0,
                critical_threshold=8.0,
                comparison="greater_than"
            ),
        ]

    async def track_interview_start(self, interview: Interview):
        """
        Track when an interview starts

        Args:
            interview: Interview that started
        """
        self.interviews_in_progress[interview.interview_id] = interview
        logger.info(f"Tracking interview {interview.interview_id}")

    async def track_response(
        self,
        interview_id: str,
        response: InterviewResponse,
        metrics: Dict[str, float]
    ):
        """
        Track a single response and its metrics

        Args:
            interview_id: Interview ID
            response: Response object
            metrics: Additional metrics to track
        """
        try:
            # Record metrics
            for metric_name, value in metrics.items():
                snapshot = MetricSnapshot(
                    metric_name=metric_name,
                    value=value,
                    timestamp=datetime.utcnow(),
                    interview_id=interview_id,
                    metadata={"response_id": response.response_id}
                )

                # Add to history
                if metric_name not in self.metric_history:
                    self.metric_history[metric_name] = deque(maxlen=100)
                self.metric_history[metric_name].append(snapshot)

                # Check thresholds
                await self._check_threshold(snapshot)

        except Exception as e:
            logger.error(f"Error tracking response: {e}")

    async def track_interview_completion(self, interview: Interview):
        """
        Track when an interview completes

        Args:
            interview: Completed interview
        """
        try:
            # Remove from in-progress
            if interview.interview_id in self.interviews_in_progress:
                del self.interviews_in_progress[interview.interview_id]

            # Add to completed
            self.completed_interviews.append(interview)

            # Calculate and track final metrics
            metrics = self._extract_interview_metrics(interview)
            for metric_name, value in metrics.items():
                snapshot = MetricSnapshot(
                    metric_name=metric_name,
                    value=value,
                    timestamp=datetime.utcnow(),
                    interview_id=interview.interview_id,
                    status=self._determine_status(metric_name, value)
                )

                if metric_name not in self.metric_history:
                    self.metric_history[metric_name] = deque(maxlen=100)
                self.metric_history[metric_name].append(snapshot)

                await self._check_threshold(snapshot)

            logger.info(f"Completed tracking for interview {interview.interview_id}")

        except Exception as e:
            logger.error(f"Error tracking interview completion: {e}")

    def _extract_interview_metrics(self, interview: Interview) -> Dict[str, float]:
        """Extract metrics from completed interview"""
        metrics = {
            "completion_rate": interview.quality_metrics.completion_percentage,
            "engagement_score": interview.engagement_metrics.overall_engagement,
            "response_quality": interview.quality_metrics.response_quality_average,
            "duration_minutes": interview.duration_seconds / 60.0,
            "response_count": len(interview.responses),
        }

        # Calculate average information density
        if interview.responses:
            avg_density = sum(
                r.analysis_metadata.get("information_density", 0.5)
                for r in interview.responses
            ) / len(interview.responses)
            metrics["information_density"] = avg_density

        return metrics

    async def _check_threshold(self, snapshot: MetricSnapshot):
        """Check if metric violates threshold"""
        try:
            # Find threshold for this metric
            threshold = next(
                (t for t in self.thresholds if t.metric_name == snapshot.metric_name),
                None
            )

            if not threshold or not threshold.enabled:
                return

            # Determine severity
            severity = self._determine_severity(snapshot.value, threshold)

            if severity:
                # Create alert
                alert = QualityAlert(
                    alert_id=f"{snapshot.metric_name}_{snapshot.timestamp.isoformat()}",
                    severity=severity,
                    metric_name=snapshot.metric_name,
                    message=self._format_alert_message(snapshot, threshold, severity),
                    current_value=snapshot.value,
                    threshold_value=self._get_threshold_value(threshold, severity),
                    interview_id=snapshot.interview_id,
                    timestamp=snapshot.timestamp,
                    metadata=snapshot.metadata
                )

                # Check if we should raise this alert (avoid duplicates)
                if self._should_raise_alert(alert):
                    await self._raise_alert(alert)

        except Exception as e:
            logger.error(f"Error checking threshold: {e}")

    def _determine_severity(
        self,
        value: float,
        threshold: QualityThreshold
    ) -> Optional[AlertSeverity]:
        """Determine alert severity based on value and threshold"""
        if threshold.comparison == "less_than":
            if value < threshold.critical_threshold:
                return AlertSeverity.CRITICAL
            elif value < threshold.error_threshold:
                return AlertSeverity.ERROR
            elif value < threshold.warning_threshold:
                return AlertSeverity.WARNING
        else:  # greater_than
            if value > threshold.critical_threshold:
                return AlertSeverity.CRITICAL
            elif value > threshold.error_threshold:
                return AlertSeverity.ERROR
            elif value > threshold.warning_threshold:
                return AlertSeverity.WARNING

        return None

    def _get_threshold_value(
        self,
        threshold: QualityThreshold,
        severity: AlertSeverity
    ) -> float:
        """Get threshold value for severity level"""
        if severity == AlertSeverity.CRITICAL:
            return threshold.critical_threshold
        elif severity == AlertSeverity.ERROR:
            return threshold.error_threshold
        else:
            return threshold.warning_threshold

    def _format_alert_message(
        self,
        snapshot: MetricSnapshot,
        threshold: QualityThreshold,
        severity: AlertSeverity
    ) -> str:
        """Format alert message"""
        comparison = "below" if threshold.comparison == "less_than" else "above"
        threshold_val = self._get_threshold_value(threshold, severity)

        return (
            f"{threshold.metric_name} is {comparison} {severity.value} threshold: "
            f"{snapshot.value:.3f} (threshold: {threshold_val:.3f})"
        )

    def _should_raise_alert(self, alert: QualityAlert) -> bool:
        """Check if alert should be raised (avoid duplicates)"""
        # Check if similar alert exists in last 5 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)

        for existing_alert in self.active_alerts:
            if (existing_alert.metric_name == alert.metric_name and
                existing_alert.severity == alert.severity and
                existing_alert.timestamp > cutoff_time and
                not existing_alert.resolved):
                return False

        return True

    async def _raise_alert(self, alert: QualityAlert):
        """Raise a quality alert"""
        self.active_alerts.append(alert)
        self.alert_history.append(alert)

        logger.warning(f"Quality Alert [{alert.severity.value}]: {alert.message}")

        # Call alert callback if configured
        if self.alert_callback:
            try:
                if asyncio.iscoroutinefunction(self.alert_callback):
                    await self.alert_callback(alert)
                else:
                    self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def _determine_status(self, metric_name: str, value: float) -> MetricStatus:
        """Determine status for a metric value"""
        threshold = next(
            (t for t in self.thresholds if t.metric_name == metric_name),
            None
        )

        if not threshold:
            return MetricStatus.UNKNOWN

        if threshold.comparison == "less_than":
            if value < threshold.error_threshold:
                return MetricStatus.UNHEALTHY
            elif value < threshold.warning_threshold:
                return MetricStatus.DEGRADED
            else:
                return MetricStatus.HEALTHY
        else:  # greater_than
            if value > threshold.error_threshold:
                return MetricStatus.UNHEALTHY
            elif value > threshold.warning_threshold:
                return MetricStatus.DEGRADED
            else:
                return MetricStatus.HEALTHY

    async def generate_report(
        self,
        time_window: Optional[timedelta] = None
    ) -> QualityReport:
        """
        Generate quality monitoring report

        Args:
            time_window: Time window to analyze (default: last hour)

        Returns:
            QualityReport with current state
        """
        if time_window is None:
            time_window = timedelta(hours=1)

        cutoff_time = datetime.utcnow() - time_window

        # Filter recent completed interviews
        recent_interviews = [
            i for i in self.completed_interviews
            if i.completed_at and i.completed_at > cutoff_time
        ]

        # Calculate statistics
        total = len(recent_interviews)
        completed = len([i for i in recent_interviews if i.status == "completed"])
        failed = len([i for i in recent_interviews if i.status == "failed"])

        avg_completion = (
            sum(i.quality_metrics.completion_percentage for i in recent_interviews) / total
            if total > 0 else 0.0
        )

        avg_engagement = (
            sum(i.engagement_metrics.overall_engagement for i in recent_interviews) / total
            if total > 0 else 0.0
        )

        avg_quality = (
            sum(i.quality_metrics.response_quality_average for i in recent_interviews) / total
            if total > 0 else 0.0
        )

        # Get current metric snapshots
        snapshots = []
        for metric_name, history in self.metric_history.items():
            if history:
                latest = history[-1]
                if latest.timestamp > cutoff_time:
                    snapshots.append(latest)

        # Calculate trends
        trends = self._calculate_trends()

        # Determine overall status
        overall_status = self._calculate_overall_status(snapshots)

        # Calculate health score
        health_score = self._calculate_health_score(snapshots)

        # Identify issues
        issues = self._identify_issues(recent_interviews, snapshots)

        # Generate recommendations
        recommendations = self._generate_recommendations(issues, trends)

        # Filter active alerts in time window
        active_alerts = [
            a for a in self.active_alerts
            if a.timestamp > cutoff_time and not a.resolved
        ]

        report = QualityReport(
            report_id=f"qr_{datetime.utcnow().isoformat()}",
            generated_at=datetime.utcnow(),
            time_window=time_window,
            overall_status=overall_status,
            health_score=health_score,
            metric_snapshots=snapshots,
            active_alerts=active_alerts,
            total_interviews=total,
            completed_interviews=completed,
            failed_interviews=failed,
            avg_completion_rate=avg_completion,
            avg_engagement_score=avg_engagement,
            avg_response_quality=avg_quality,
            trends=trends,
            issues_detected=issues,
            recommendations=recommendations
        )

        return report

    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate trends for all metrics"""
        trends = {}

        for metric_name, history in self.metric_history.items():
            if len(history) >= 3:
                values = [s.value for s in history]

                # Simple trend calculation
                recent_avg = sum(values[-3:]) / 3
                older_avg = sum(values[:3]) / 3

                diff = recent_avg - older_avg
                threshold = older_avg * 0.1  # 10% change

                if abs(diff) < threshold:
                    trends[metric_name] = "stable"
                elif diff > 0:
                    trends[metric_name] = "increasing"
                else:
                    trends[metric_name] = "decreasing"
            else:
                trends[metric_name] = "insufficient_data"

        return trends

    def _calculate_overall_status(
        self,
        snapshots: List[MetricSnapshot]
    ) -> MetricStatus:
        """Calculate overall system status"""
        if not snapshots:
            return MetricStatus.UNKNOWN

        status_counts = {
            MetricStatus.HEALTHY: 0,
            MetricStatus.DEGRADED: 0,
            MetricStatus.UNHEALTHY: 0,
            MetricStatus.UNKNOWN: 0
        }

        for snapshot in snapshots:
            status_counts[snapshot.status] += 1

        # Determine overall status
        if status_counts[MetricStatus.UNHEALTHY] > 0:
            return MetricStatus.UNHEALTHY
        elif status_counts[MetricStatus.DEGRADED] > 0:
            return MetricStatus.DEGRADED
        elif status_counts[MetricStatus.HEALTHY] > 0:
            return MetricStatus.HEALTHY
        else:
            return MetricStatus.UNKNOWN

    def _calculate_health_score(
        self,
        snapshots: List[MetricSnapshot]
    ) -> float:
        """Calculate overall health score (0.0 to 1.0)"""
        if not snapshots:
            return 0.5

        status_weights = {
            MetricStatus.HEALTHY: 1.0,
            MetricStatus.DEGRADED: 0.5,
            MetricStatus.UNHEALTHY: 0.0,
            MetricStatus.UNKNOWN: 0.5
        }

        total_weight = sum(status_weights[s.status] for s in snapshots)
        return total_weight / len(snapshots)

    def _identify_issues(
        self,
        interviews: List[Interview],
        snapshots: List[MetricSnapshot]
    ) -> List[str]:
        """Identify current issues"""
        issues = []

        # Check for low engagement
        engagement_snapshots = [s for s in snapshots if s.metric_name == "engagement_score"]
        if engagement_snapshots:
            avg_engagement = sum(s.value for s in engagement_snapshots) / len(engagement_snapshots)
            if avg_engagement < 0.5:
                issues.append(f"Low average engagement: {avg_engagement:.2f}")

        # Check for high error rate
        for alert in self.active_alerts:
            if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL] and not alert.resolved:
                issues.append(f"{alert.metric_name}: {alert.message}")

        # Check completion rate
        if interviews:
            completion_rate = sum(
                1 for i in interviews if i.status == "completed"
            ) / len(interviews)
            if completion_rate < 0.7:
                issues.append(f"Low completion rate: {completion_rate*100:.1f}%")

        return issues

    def _generate_recommendations(
        self,
        issues: List[str],
        trends: Dict[str, str]
    ) -> List[str]:
        """Generate recommendations based on issues and trends"""
        recommendations = []

        # Check for declining metrics
        for metric_name, trend in trends.items():
            if trend == "decreasing":
                if "engagement" in metric_name:
                    recommendations.append("Consider reviewing interview scripts for engagement")
                elif "quality" in metric_name:
                    recommendations.append("Review follow-up question generation quality")
                elif "completion" in metric_name:
                    recommendations.append("Investigate reasons for interview abandonment")

        # Issue-specific recommendations
        for issue in issues:
            if "engagement" in issue.lower():
                recommendations.append("Analyze top-performing interviews for engagement patterns")
            elif "error" in issue.lower():
                recommendations.append("Check system logs for error patterns")
            elif "completion" in issue.lower():
                recommendations.append("Review interview length and question difficulty")

        return recommendations

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.metadata["acknowledged_by"] = acknowledged_by
                alert.metadata["acknowledged_at"] = datetime.utcnow().isoformat()
                logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                break

    def resolve_alert(self, alert_id: str, resolved_by: str):
        """Resolve an alert"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.metadata["resolved_by"] = resolved_by
                alert.metadata["resolved_at"] = datetime.utcnow().isoformat()
                logger.info(f"Alert {alert_id} resolved by {resolved_by}")
                break

    def get_metric_history(
        self,
        metric_name: str,
        limit: Optional[int] = None
    ) -> List[MetricSnapshot]:
        """Get history for a specific metric"""
        if metric_name not in self.metric_history:
            return []

        history = list(self.metric_history[metric_name])
        if limit:
            history = history[-limit:]

        return history

    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None
    ) -> List[QualityAlert]:
        """Get active alerts, optionally filtered by severity"""
        alerts = [a for a in self.active_alerts if not a.resolved]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts
