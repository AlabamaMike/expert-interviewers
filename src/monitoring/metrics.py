"""
Metrics collection using Prometheus
"""

from prometheus_client import Counter, Histogram, Gauge, Summary
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """Prometheus metrics for Expert Interviewers"""

    def __init__(self):
        """Initialize Prometheus metrics"""

        # Interview metrics
        self.interviews_total = Counter(
            "interviews_total",
            "Total number of interviews",
            ["status", "call_guide_id"]
        )

        self.interview_duration = Histogram(
            "interview_duration_seconds",
            "Interview duration in seconds",
            ["call_guide_id"],
            buckets=[60, 300, 600, 900, 1800, 2700, 3600]
        )

        self.interview_completion_rate = Gauge(
            "interview_completion_rate",
            "Interview completion percentage",
            ["call_guide_id"]
        )

        # Response metrics
        self.responses_total = Counter(
            "responses_total",
            "Total number of responses collected",
            ["section"]
        )

        self.response_sentiment = Counter(
            "response_sentiment_total",
            "Response sentiment distribution",
            ["sentiment"]
        )

        self.information_density = Histogram(
            "information_density",
            "Information density of responses",
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )

        # Follow-up metrics
        self.follow_ups_generated = Counter(
            "follow_ups_generated_total",
            "Total follow-up questions generated",
            ["action_type"]
        )

        self.follow_up_effectiveness = Histogram(
            "follow_up_effectiveness",
            "Effectiveness of follow-up questions (0-1)",
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )

        # Quality metrics
        self.engagement_score = Histogram(
            "engagement_score",
            "Respondent engagement score",
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )

        self.data_quality_score = Histogram(
            "data_quality_score",
            "Data quality score",
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )

        # System metrics
        self.stt_latency = Histogram(
            "stt_latency_seconds",
            "Speech-to-text latency",
            buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        )

        self.tts_latency = Histogram(
            "tts_latency_seconds",
            "Text-to-speech latency",
            buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0]
        )

        self.llm_latency = Histogram(
            "llm_latency_seconds",
            "LLM response latency",
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
        )

        self.llm_tokens_used = Counter(
            "llm_tokens_used_total",
            "Total LLM tokens used",
            ["operation"]
        )

        # Error metrics
        self.errors_total = Counter(
            "errors_total",
            "Total errors",
            ["error_type", "component"]
        )

        self.escalations_total = Counter(
            "escalations_total",
            "Total human escalations",
            ["reason"]
        )

        logger.info("Prometheus metrics initialized")


class MetricsCollector:
    """Collects and records metrics throughout the system"""

    def __init__(self, prometheus_metrics: Optional[PrometheusMetrics] = None):
        """
        Initialize metrics collector

        Args:
            prometheus_metrics: PrometheusMetrics instance (creates new if None)
        """
        self.metrics = prometheus_metrics or PrometheusMetrics()
        logger.info("MetricsCollector initialized")

    def record_interview_started(self, call_guide_id: str):
        """Record interview start"""
        self.metrics.interviews_total.labels(
            status="started",
            call_guide_id=call_guide_id
        ).inc()

    def record_interview_completed(
        self,
        call_guide_id: str,
        duration_seconds: float,
        completion_rate: float,
        engagement_score: float,
        data_quality_score: float
    ):
        """Record interview completion"""
        self.metrics.interviews_total.labels(
            status="completed",
            call_guide_id=call_guide_id
        ).inc()

        self.metrics.interview_duration.labels(
            call_guide_id=call_guide_id
        ).observe(duration_seconds)

        self.metrics.interview_completion_rate.labels(
            call_guide_id=call_guide_id
        ).set(completion_rate)

        self.metrics.engagement_score.observe(engagement_score)
        self.metrics.data_quality_score.observe(data_quality_score)

    def record_interview_failed(self, call_guide_id: str, error_type: str):
        """Record interview failure"""
        self.metrics.interviews_total.labels(
            status="failed",
            call_guide_id=call_guide_id
        ).inc()

        self.metrics.errors_total.labels(
            error_type=error_type,
            component="interview"
        ).inc()

    def record_response(
        self,
        section: str,
        sentiment: str,
        information_density: float
    ):
        """Record a response"""
        self.metrics.responses_total.labels(section=section).inc()
        self.metrics.response_sentiment.labels(sentiment=sentiment).inc()
        self.metrics.information_density.observe(information_density)

    def record_follow_up(self, action_type: str, effectiveness: Optional[float] = None):
        """Record follow-up generation"""
        self.metrics.follow_ups_generated.labels(action_type=action_type).inc()

        if effectiveness is not None:
            self.metrics.follow_up_effectiveness.observe(effectiveness)

    def record_stt_latency(self, latency_seconds: float):
        """Record STT latency"""
        self.metrics.stt_latency.observe(latency_seconds)

    def record_tts_latency(self, latency_seconds: float):
        """Record TTS latency"""
        self.metrics.tts_latency.observe(latency_seconds)

    def record_llm_call(self, operation: str, latency_seconds: float, tokens_used: int):
        """Record LLM call"""
        self.metrics.llm_latency.observe(latency_seconds)
        self.metrics.llm_tokens_used.labels(operation=operation).inc(tokens_used)

    def record_error(self, error_type: str, component: str):
        """Record an error"""
        self.metrics.errors_total.labels(
            error_type=error_type,
            component=component
        ).inc()

    def record_escalation(self, reason: str):
        """Record human escalation"""
        self.metrics.escalations_total.labels(reason=reason).inc()


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
