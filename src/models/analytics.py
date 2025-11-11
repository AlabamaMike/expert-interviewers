"""
Analytics and insight extraction models
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class Theme(BaseModel):
    """A theme identified across responses"""
    theme_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    keywords: List[str] = Field(default_factory=list)
    frequency: int = Field(default=0)
    sentiment: Optional[str] = None
    representative_quotes: List[str] = Field(default_factory=list)


class InsightType(str, Field):
    """Types of insights that can be extracted"""
    PAIN_POINT = "pain_point"
    OPPORTUNITY = "opportunity"
    PATTERN = "pattern"
    CONTRADICTION = "contradiction"
    HYPOTHESIS_VALIDATION = "hypothesis_validation"
    UNEXPECTED = "unexpected"


class Insight(BaseModel):
    """A single insight extracted from interview(s)"""
    insight_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # Using InsightType
    title: str
    description: str
    evidence: List[str] = Field(default_factory=list, description="Supporting quotes/data")
    confidence: float = Field(ge=0.0, le=1.0)
    impact_score: float = Field(ge=0.0, le=1.0, description="Estimated importance")
    source_interviews: List[str] = Field(default_factory=list)
    related_themes: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)


class SentimentDataPoint(BaseModel):
    """Point in sentiment trajectory"""
    timestamp: datetime
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    section: Optional[str] = None
    trigger: Optional[str] = None


class SentimentTrajectory(BaseModel):
    """Sentiment changes throughout interview"""
    interview_id: str
    data_points: List[SentimentDataPoint] = Field(default_factory=list)
    overall_sentiment: float = Field(ge=-1.0, le=1.0)
    sentiment_variance: float = Field(ge=0.0)
    positive_peaks: List[SentimentDataPoint] = Field(default_factory=list)
    negative_peaks: List[SentimentDataPoint] = Field(default_factory=list)


class ThemeAnalysis(BaseModel):
    """Theme analysis across interviews"""
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    themes: List[Theme] = Field(default_factory=list)
    interview_ids: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    total_interviews: int = 0
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class InsightExtraction(BaseModel):
    """Complete insight extraction from interview(s)"""
    extraction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    interview_id: Optional[str] = None  # Single interview or None for multi-interview
    interview_ids: List[str] = Field(default_factory=list)  # For cross-interview analysis

    # Extracted content
    executive_summary: str = Field(description="3-5 bullet point summary")
    key_findings: List[Insight] = Field(default_factory=list)
    themes: List[Theme] = Field(default_factory=list)
    notable_quotes: List[Dict[str, str]] = Field(default_factory=list)

    # Analysis
    sentiment_summary: Dict[str, Any] = Field(default_factory=dict)
    contradictions: List[str] = Field(default_factory=list)
    research_objective_alignment: float = Field(ge=0.0, le=1.0)

    # Quality
    data_quality_score: float = Field(ge=0.0, le=1.0)
    confidence_level: float = Field(ge=0.0, le=1.0)

    # Recommendations
    follow_up_recommendations: List[str] = Field(default_factory=list)
    suggested_next_questions: List[str] = Field(default_factory=list)

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: str = Field(default="system")
    model_used: Optional[str] = None


class CrossInterviewPattern(BaseModel):
    """Pattern identified across multiple interviews"""
    pattern_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str  # e.g., "segment_difference", "universal_pain_point", "outlier"
    description: str
    affected_interviews: List[str] = Field(default_factory=list)
    frequency: float = Field(ge=0.0, le=1.0, description="How often this pattern appears")
    statistical_significance: Optional[float] = None
    segments: Dict[str, Any] = Field(default_factory=dict)


class SegmentAnalysis(BaseModel):
    """Analysis by respondent segment"""
    segment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    segment_name: str
    segment_criteria: Dict[str, Any] = Field(default_factory=dict)
    interview_count: int = 0
    interview_ids: List[str] = Field(default_factory=list)

    # Segment-specific findings
    key_insights: List[Insight] = Field(default_factory=list)
    unique_themes: List[Theme] = Field(default_factory=list)
    avg_sentiment: float = Field(ge=-1.0, le=1.0)

    # Comparisons
    differences_from_average: Dict[str, Any] = Field(default_factory=dict)
    statistical_significance: Dict[str, float] = Field(default_factory=dict)


class TrendAnalysis(BaseModel):
    """Trend analysis over time"""
    trend_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metric_name: str
    time_series: List[Dict[str, Any]] = Field(default_factory=list)
    direction: str = Field(description="increasing, decreasing, stable, volatile")
    rate_of_change: Optional[float] = None
    prediction: Optional[Dict[str, Any]] = None
    confidence: float = Field(ge=0.0, le=1.0)
