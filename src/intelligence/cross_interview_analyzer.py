"""
Cross-Interview Analysis with Statistical Pattern Detection
Enhanced analytics for identifying patterns across multiple interviews
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime
from collections import defaultdict, Counter
import statistics

from ..models.analytics import (
    CrossInterviewPattern, SegmentAnalysis, TrendAnalysis,
    InsightExtraction, Theme, Insight
)
from ..models.interview import Interview, ResponseSentiment
from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class StatisticalPattern:
    """Statistical pattern detected across interviews"""
    pattern_type: str
    description: str
    metric_name: str
    metric_value: float
    sample_size: int
    confidence_interval: Tuple[float, float]
    p_value: Optional[float] = None
    effect_size: Optional[float] = None


@dataclass
class SegmentComparison:
    """Comparison between different segments"""
    segment_a: str
    segment_b: str
    metric: str
    value_a: float
    value_b: float
    difference: float
    percentage_difference: float
    is_significant: bool
    confidence: float


@dataclass
class TimeSeriesPoint:
    """Data point in time series"""
    timestamp: datetime
    value: float
    interview_count: int
    metadata: Dict[str, Any]


class CrossInterviewAnalyzer:
    """Advanced cross-interview analysis with statistical methods"""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize cross-interview analyzer

        Args:
            llm_provider: LLM provider for qualitative analysis
        """
        self.llm = llm_provider
        logger.info("Initialized CrossInterviewAnalyzer")

    async def analyze_patterns(
        self,
        interviews: List[Interview],
        research_objective: str,
        min_pattern_frequency: float = 0.3
    ) -> List[CrossInterviewPattern]:
        """
        Detect patterns across interviews

        Args:
            interviews: List of interviews to analyze
            research_objective: Research objective for context
            min_pattern_frequency: Minimum frequency to consider a pattern (0.0-1.0)

        Returns:
            List of detected patterns
        """
        try:
            patterns = []

            # Detect universal patterns (appearing in most interviews)
            universal_patterns = await self._detect_universal_patterns(
                interviews, min_pattern_frequency
            )
            patterns.extend(universal_patterns)

            # Detect segment-specific patterns
            segment_patterns = await self._detect_segment_patterns(interviews)
            patterns.extend(segment_patterns)

            # Detect outliers
            outlier_patterns = await self._detect_outliers(interviews)
            patterns.extend(outlier_patterns)

            # Detect temporal patterns
            temporal_patterns = await self._detect_temporal_patterns(interviews)
            patterns.extend(temporal_patterns)

            logger.info(f"Detected {len(patterns)} cross-interview patterns")
            return patterns

        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}")
            return []

    async def _detect_universal_patterns(
        self,
        interviews: List[Interview],
        min_frequency: float
    ) -> List[CrossInterviewPattern]:
        """Detect patterns that appear across most interviews"""
        patterns = []

        # Collect all themes across interviews
        theme_counter = Counter()
        theme_interviews = defaultdict(set)

        for interview in interviews:
            for response in interview.responses:
                for theme in response.themes:
                    theme_counter[theme] += 1
                    theme_interviews[theme].add(interview.interview_id)

        # Identify universal themes
        total_interviews = len(interviews)
        for theme, count in theme_counter.items():
            frequency = len(theme_interviews[theme]) / total_interviews
            if frequency >= min_frequency:
                pattern = CrossInterviewPattern(
                    pattern_type="universal_theme",
                    description=f"Theme '{theme}' appears in {frequency*100:.1f}% of interviews",
                    affected_interviews=list(theme_interviews[theme]),
                    frequency=frequency,
                    segments={"theme": theme, "occurrence_count": count}
                )
                patterns.append(pattern)

        # Collect sentiment patterns
        sentiment_by_section = defaultdict(list)
        for interview in interviews:
            section_sentiments = defaultdict(list)
            for response in interview.responses:
                if response.sentiment:
                    section_sentiments[response.section_name].append(
                        self._sentiment_to_score(response.sentiment)
                    )
            for section, sentiments in section_sentiments.items():
                if sentiments:
                    sentiment_by_section[section].append(statistics.mean(sentiments))

        # Identify universal sentiment patterns
        for section, sentiments in sentiment_by_section.items():
            if len(sentiments) >= total_interviews * min_frequency:
                avg_sentiment = statistics.mean(sentiments)
                std_sentiment = statistics.stdev(sentiments) if len(sentiments) > 1 else 0

                if abs(avg_sentiment) > 0.3:  # Significant sentiment
                    sentiment_label = "positive" if avg_sentiment > 0 else "negative"
                    pattern = CrossInterviewPattern(
                        pattern_type="universal_sentiment",
                        description=f"Section '{section}' consistently shows {sentiment_label} sentiment (avg: {avg_sentiment:.2f})",
                        affected_interviews=[i.interview_id for i in interviews],
                        frequency=len(sentiments) / total_interviews,
                        segments={
                            "section": section,
                            "avg_sentiment": avg_sentiment,
                            "std_sentiment": std_sentiment
                        }
                    )
                    patterns.append(pattern)

        return patterns

    async def _detect_segment_patterns(
        self,
        interviews: List[Interview]
    ) -> List[CrossInterviewPattern]:
        """Detect patterns specific to segments"""
        patterns = []

        # Group interviews by respondent metadata if available
        # For now, we'll use engagement level as a simple segmentation
        high_engagement = []
        low_engagement = []

        for interview in interviews:
            if interview.engagement_metrics.overall_engagement > 0.7:
                high_engagement.append(interview)
            elif interview.engagement_metrics.overall_engagement < 0.4:
                low_engagement.append(interview)

        # Compare segments
        if high_engagement and low_engagement:
            # Calculate average response quality
            high_quality = statistics.mean([
                i.quality_metrics.response_quality_average
                for i in high_engagement
            ])
            low_quality = statistics.mean([
                i.quality_metrics.response_quality_average
                for i in low_engagement
            ])

            if abs(high_quality - low_quality) > 0.2:
                pattern = CrossInterviewPattern(
                    pattern_type="segment_difference",
                    description=f"High-engagement respondents show {((high_quality - low_quality) / low_quality * 100):.1f}% better response quality",
                    affected_interviews=[i.interview_id for i in high_engagement + low_engagement],
                    frequency=1.0,
                    segments={
                        "high_engagement_quality": high_quality,
                        "low_engagement_quality": low_quality,
                        "high_engagement_count": len(high_engagement),
                        "low_engagement_count": len(low_engagement)
                    }
                )
                patterns.append(pattern)

        return patterns

    async def _detect_outliers(
        self,
        interviews: List[Interview]
    ) -> List[CrossInterviewPattern]:
        """Detect outlier interviews"""
        patterns = []

        if len(interviews) < 3:
            return patterns

        # Calculate statistics for various metrics
        durations = [i.duration_seconds for i in interviews]
        response_counts = [len(i.responses) for i in interviews]
        engagement_scores = [i.engagement_metrics.overall_engagement for i in interviews]

        # Identify outliers (using simple IQR method)
        duration_outliers = self._find_outliers(durations, interviews, "duration")
        count_outliers = self._find_outliers(response_counts, interviews, "response_count")
        engagement_outliers = self._find_outliers(engagement_scores, interviews, "engagement")

        # Create patterns for significant outliers
        for outlier_interview, metric_name, value, avg_value in duration_outliers:
            if abs(value - avg_value) / avg_value > 0.5:  # 50% deviation
                pattern = CrossInterviewPattern(
                    pattern_type="outlier",
                    description=f"Interview has unusual {metric_name}: {value:.1f} vs average {avg_value:.1f}",
                    affected_interviews=[outlier_interview.interview_id],
                    frequency=1.0 / len(interviews),
                    segments={
                        "metric": metric_name,
                        "value": value,
                        "average": avg_value,
                        "deviation_percent": abs(value - avg_value) / avg_value * 100
                    }
                )
                patterns.append(pattern)

        return patterns

    def _find_outliers(
        self,
        values: List[float],
        interviews: List[Interview],
        metric_name: str
    ) -> List[Tuple[Interview, str, float, float]]:
        """Find outliers using IQR method"""
        if len(values) < 3:
            return []

        sorted_values = sorted(values)
        q1 = sorted_values[len(sorted_values) // 4]
        q3 = sorted_values[3 * len(sorted_values) // 4]
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        avg_value = statistics.mean(values)

        outliers = []
        for interview, value in zip(interviews, values):
            if value < lower_bound or value > upper_bound:
                outliers.append((interview, metric_name, value, avg_value))

        return outliers

    async def _detect_temporal_patterns(
        self,
        interviews: List[Interview]
    ) -> List[CrossInterviewPattern]:
        """Detect patterns over time"""
        patterns = []

        # Sort interviews by date
        sorted_interviews = sorted(
            [i for i in interviews if i.started_at],
            key=lambda x: x.started_at
        )

        if len(sorted_interviews) < 3:
            return patterns

        # Calculate sentiment trend over time
        sentiment_over_time = []
        for interview in sorted_interviews:
            avg_sentiment = statistics.mean([
                self._sentiment_to_score(r.sentiment)
                for r in interview.responses
                if r.sentiment
            ]) if interview.responses else 0.0

            sentiment_over_time.append(avg_sentiment)

        # Check for trends (simple linear trend)
        if len(sentiment_over_time) >= 3:
            trend = self._calculate_trend(sentiment_over_time)
            if abs(trend) > 0.1:  # Significant trend
                direction = "increasing" if trend > 0 else "decreasing"
                pattern = CrossInterviewPattern(
                    pattern_type="temporal_trend",
                    description=f"Sentiment is {direction} over time (trend: {trend:.3f})",
                    affected_interviews=[i.interview_id for i in sorted_interviews],
                    frequency=1.0,
                    segments={
                        "metric": "sentiment",
                        "trend_direction": direction,
                        "trend_slope": trend,
                        "start_value": sentiment_over_time[0],
                        "end_value": sentiment_over_time[-1]
                    }
                )
                patterns.append(pattern)

        return patterns

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate simple linear trend"""
        n = len(values)
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        return numerator / denominator if denominator != 0 else 0.0

    def _sentiment_to_score(self, sentiment: ResponseSentiment) -> float:
        """Convert sentiment enum to numeric score"""
        sentiment_map = {
            ResponseSentiment.VERY_POSITIVE: 1.0,
            ResponseSentiment.POSITIVE: 0.5,
            ResponseSentiment.NEUTRAL: 0.0,
            ResponseSentiment.NEGATIVE: -0.5,
            ResponseSentiment.VERY_NEGATIVE: -1.0
        }
        return sentiment_map.get(sentiment, 0.0)

    async def compare_segments(
        self,
        segment_a_interviews: List[Interview],
        segment_b_interviews: List[Interview],
        segment_a_name: str,
        segment_b_name: str
    ) -> SegmentAnalysis:
        """
        Compare two segments of interviews

        Args:
            segment_a_interviews: Interviews in segment A
            segment_b_interviews: Interviews in segment B
            segment_a_name: Name for segment A
            segment_b_name: Name for segment B

        Returns:
            SegmentAnalysis with comparison results
        """
        try:
            # Calculate metrics for each segment
            metrics_a = self._calculate_segment_metrics(segment_a_interviews)
            metrics_b = self._calculate_segment_metrics(segment_b_interviews)

            # Calculate differences
            differences = {}
            for metric_name in metrics_a.keys():
                if metric_name in metrics_b:
                    diff = metrics_a[metric_name] - metrics_b[metric_name]
                    pct_diff = (diff / metrics_b[metric_name] * 100) if metrics_b[metric_name] != 0 else 0
                    differences[metric_name] = {
                        "absolute": diff,
                        "percentage": pct_diff,
                        "segment_a_value": metrics_a[metric_name],
                        "segment_b_value": metrics_b[metric_name]
                    }

            # Use LLM to generate insights about differences
            comparison_prompt = f"""Compare these two interview segments:

Segment A: {segment_a_name} ({len(segment_a_interviews)} interviews)
Segment B: {segment_b_name} ({len(segment_b_interviews)} interviews)

Metrics:
{self._format_metrics_for_comparison(metrics_a, metrics_b)}

Provide insights about:
1. Key differences between segments
2. What makes each segment unique
3. Implications for product/research decisions
"""

            insights_result = await self.llm.generate(
                prompt=comparison_prompt,
                system_prompt="You are an expert at analyzing research data and identifying meaningful patterns.",
                temperature=0.5
            )

            # Create segment analysis
            analysis = SegmentAnalysis(
                segment_name=f"{segment_a_name} vs {segment_b_name}",
                segment_criteria={"comparison": "segment_comparison"},
                interview_count=len(segment_a_interviews) + len(segment_b_interviews),
                interview_ids=[i.interview_id for i in segment_a_interviews + segment_b_interviews],
                key_insights=[],
                unique_themes=[],
                avg_sentiment=metrics_a.get("avg_sentiment", 0.0),
                differences_from_average=differences,
                statistical_significance={}
            )

            logger.info(f"Completed segment comparison: {segment_a_name} vs {segment_b_name}")
            return analysis

        except Exception as e:
            logger.error(f"Error comparing segments: {e}")
            return SegmentAnalysis(
                segment_name="Error",
                segment_criteria={},
                interview_count=0,
                interview_ids=[],
                key_insights=[],
                unique_themes=[],
                avg_sentiment=0.0
            )

    def _calculate_segment_metrics(self, interviews: List[Interview]) -> Dict[str, float]:
        """Calculate aggregate metrics for a segment"""
        if not interviews:
            return {}

        metrics = {}

        # Average duration
        metrics["avg_duration"] = statistics.mean([i.duration_seconds for i in interviews])

        # Average engagement
        metrics["avg_engagement"] = statistics.mean([
            i.engagement_metrics.overall_engagement for i in interviews
        ])

        # Average completion rate
        metrics["avg_completion"] = statistics.mean([
            i.quality_metrics.completion_percentage for i in interviews
        ])

        # Average response quality
        metrics["avg_response_quality"] = statistics.mean([
            i.quality_metrics.response_quality_average for i in interviews
        ])

        # Average sentiment
        all_sentiments = []
        for interview in interviews:
            for response in interview.responses:
                if response.sentiment:
                    all_sentiments.append(self._sentiment_to_score(response.sentiment))

        metrics["avg_sentiment"] = statistics.mean(all_sentiments) if all_sentiments else 0.0

        # Average response length
        all_response_lengths = []
        for interview in interviews:
            for response in interview.responses:
                all_response_lengths.append(len(response.response_text.split()))

        metrics["avg_response_length"] = statistics.mean(all_response_lengths) if all_response_lengths else 0

        return metrics

    def _format_metrics_for_comparison(
        self,
        metrics_a: Dict[str, float],
        metrics_b: Dict[str, float]
    ) -> str:
        """Format metrics for LLM prompt"""
        lines = []
        for key in metrics_a.keys():
            if key in metrics_b:
                diff = metrics_a[key] - metrics_b[key]
                pct = (diff / metrics_b[key] * 100) if metrics_b[key] != 0 else 0
                lines.append(
                    f"- {key}: A={metrics_a[key]:.2f}, B={metrics_b[key]:.2f}, "
                    f"Diff={diff:.2f} ({pct:+.1f}%)"
                )
        return "\n".join(lines)

    async def analyze_trends(
        self,
        interviews: List[Interview],
        metric_name: str,
        time_window: Optional[str] = None
    ) -> TrendAnalysis:
        """
        Analyze trends over time for a specific metric

        Args:
            interviews: List of interviews
            metric_name: Metric to analyze
            time_window: Time window for analysis (e.g., "weekly", "monthly")

        Returns:
            TrendAnalysis with trend information
        """
        try:
            # Sort interviews by date
            sorted_interviews = sorted(
                [i for i in interviews if i.started_at],
                key=lambda x: x.started_at
            )

            if len(sorted_interviews) < 2:
                logger.warning("Not enough interviews for trend analysis")
                return TrendAnalysis(
                    metric_name=metric_name,
                    direction="stable",
                    confidence=0.0
                )

            # Extract time series data
            time_series = []
            for interview in sorted_interviews:
                value = self._extract_metric_value(interview, metric_name)
                if value is not None:
                    time_series.append({
                        "timestamp": interview.started_at.isoformat(),
                        "value": value,
                        "interview_id": interview.interview_id
                    })

            if len(time_series) < 2:
                return TrendAnalysis(
                    metric_name=metric_name,
                    time_series=time_series,
                    direction="stable",
                    confidence=0.0
                )

            # Calculate trend
            values = [point["value"] for point in time_series]
            trend_slope = self._calculate_trend(values)

            # Determine direction
            if abs(trend_slope) < 0.05:
                direction = "stable"
            elif trend_slope > 0.05:
                direction = "increasing"
            else:
                direction = "decreasing"

            # Calculate confidence based on consistency
            confidence = min(1.0, abs(trend_slope) * 10)

            return TrendAnalysis(
                metric_name=metric_name,
                time_series=time_series,
                direction=direction,
                rate_of_change=trend_slope,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return TrendAnalysis(
                metric_name=metric_name,
                direction="unknown",
                confidence=0.0
            )

    def _extract_metric_value(self, interview: Interview, metric_name: str) -> Optional[float]:
        """Extract a specific metric value from an interview"""
        metric_map = {
            "engagement": interview.engagement_metrics.overall_engagement,
            "completion": interview.quality_metrics.completion_percentage,
            "quality": interview.quality_metrics.response_quality_average,
            "duration": interview.duration_seconds / 60.0,  # Convert to minutes
            "response_count": len(interview.responses)
        }

        if metric_name in metric_map:
            return float(metric_map[metric_name])

        # Handle sentiment specially
        if metric_name == "sentiment":
            sentiments = [
                self._sentiment_to_score(r.sentiment)
                for r in interview.responses
                if r.sentiment
            ]
            return statistics.mean(sentiments) if sentiments else None

        return None

    async def generate_executive_summary(
        self,
        interviews: List[Interview],
        research_objective: str
    ) -> str:
        """
        Generate executive summary across all interviews

        Args:
            interviews: List of interviews
            research_objective: Research objective

        Returns:
            Executive summary text
        """
        try:
            # Calculate aggregate statistics
            total_interviews = len(interviews)
            total_responses = sum(len(i.responses) for i in interviews)
            avg_duration = statistics.mean([i.duration_seconds for i in interviews]) / 60
            avg_engagement = statistics.mean([i.engagement_metrics.overall_engagement for i in interviews])

            # Detect patterns
            patterns = await self.analyze_patterns(interviews, research_objective)

            # Build prompt
            prompt = f"""Generate an executive summary for this research:

**Research Objective:**
{research_objective}

**Statistics:**
- Total Interviews: {total_interviews}
- Total Responses: {total_responses}
- Average Duration: {avg_duration:.1f} minutes
- Average Engagement: {avg_engagement:.2f}

**Detected Patterns:**
{self._format_patterns(patterns)}

**Task:**
Provide a concise executive summary (3-5 paragraphs) that:
1. Summarizes the key findings
2. Highlights the most important patterns
3. Provides actionable recommendations
4. Addresses the research objective

Write in a professional, business-focused tone.
"""

            result = await self.llm.generate(
                prompt=prompt,
                system_prompt="You are an expert research analyst writing executive summaries.",
                temperature=0.5,
                max_tokens=1000
            )

            return result.content

        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return "Error generating executive summary."

    def _format_patterns(self, patterns: List[CrossInterviewPattern]) -> str:
        """Format patterns for display"""
        if not patterns:
            return "No significant patterns detected."

        lines = []
        for i, pattern in enumerate(patterns[:10], 1):  # Limit to top 10
            lines.append(f"{i}. [{pattern.pattern_type}] {pattern.description}")

        return "\n".join(lines)
