"""
Database models using SQLAlchemy
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

Base = declarative_base()


class InterviewStatusEnum(str, enum.Enum):
    """Interview status enum"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ResponseSentimentEnum(str, enum.Enum):
    """Response sentiment enum"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class CallGuideModel(Base):
    """Call guide database model"""
    __tablename__ = "call_guides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    research_objective = Column(Text, nullable=False)

    # JSON fields for complex data
    target_respondent_profile = Column(JSON, default={})
    sections = Column(JSON, nullable=False)
    adaptive_rules = Column(JSON, default={})
    voice_profile = Column(JSON, default={})

    # Metadata
    version = Column(String(50), default="1.0")
    tags = Column(JSON, default=[])
    created_by = Column(String(255))

    # Settings
    estimated_duration_minutes = Column(Integer, default=30)
    max_duration_minutes = Column(Integer, default=60)
    min_completion_percentage = Column(Float, default=0.7)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    interviews = relationship("InterviewModel", back_populates="call_guide")


class InterviewModel(Base):
    """Interview session database model"""
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_guide_id = Column(UUID(as_uuid=True), ForeignKey("call_guides.id"), nullable=False, index=True)

    # Respondent info
    respondent_id = Column(String(255), index=True)
    respondent_name = Column(String(255))
    respondent_phone = Column(String(50), nullable=False, index=True)
    respondent_email = Column(String(255))
    respondent_metadata = Column(JSON, default={})

    # Status
    status = Column(SQLEnum(InterviewStatusEnum), default=InterviewStatusEnum.SCHEDULED, nullable=False, index=True)

    # Timing
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)

    # Call details
    call_sid = Column(String(255), index=True)
    recording_url = Column(String(500))

    # State
    conversation_state = Column(JSON, default={})
    current_section = Column(String(255))
    current_question_id = Column(String(255))
    sections_completed = Column(JSON, default=[])
    questions_skipped = Column(JSON, default=[])

    # Metrics (stored as JSON for flexibility)
    engagement_metrics = Column(JSON, default={})
    quality_metrics = Column(JSON, default={})

    # Flags
    requires_human_review = Column(Boolean, default=False, index=True)
    escalation_reason = Column(Text)
    interviewer_notes = Column(JSON, default=[])
    tags = Column(JSON, default=[])

    # Consent
    consent_given = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime)
    gdpr_compliant = Column(Boolean, default=True)
    can_be_recorded = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    call_guide = relationship("CallGuideModel", back_populates="interviews")
    responses = relationship("InterviewResponseModel", back_populates="interview", cascade="all, delete-orphan")
    insights = relationship("InsightExtractionModel", back_populates="interview")


class InterviewResponseModel(Base):
    """Interview response database model"""
    __tablename__ = "interview_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id"), nullable=False, index=True)
    question_id = Column(String(255), nullable=False, index=True)
    section_name = Column(String(255), nullable=False, index=True)

    # Content
    question_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    response_audio_url = Column(String(500))

    # Timing
    asked_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime)
    response_time_seconds = Column(Float)

    # Analysis
    sentiment = Column(SQLEnum(ResponseSentimentEnum))
    confidence_score = Column(Float)
    key_phrases = Column(JSON, default=[])
    themes = Column(JSON, default=[])
    information_density = Column(Float)

    # Follow-ups
    is_follow_up = Column(Boolean, default=False, index=True)
    parent_response_id = Column(UUID(as_uuid=True), ForeignKey("interview_responses.id"))
    follow_up_count = Column(Integer, default=0)
    generated_follow_ups = Column(JSON, default=[])

    # Quality
    is_complete = Column(Boolean, default=True)
    requires_clarification = Column(Boolean, default=False)
    flags = Column(JSON, default=[])

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    interview = relationship("InterviewModel", back_populates="responses")
    parent_response = relationship("InterviewResponseModel", remote_side=[id])


class InsightExtractionModel(Base):
    """Insight extraction database model"""
    __tablename__ = "insight_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id"), index=True)

    # For cross-interview analysis
    interview_ids = Column(JSON, default=[])

    # Content
    executive_summary = Column(Text, nullable=False)
    key_findings = Column(JSON, default=[])
    themes = Column(JSON, default=[])
    notable_quotes = Column(JSON, default=[])

    # Analysis
    sentiment_summary = Column(JSON, default={})
    contradictions = Column(JSON, default=[])
    research_objective_alignment = Column(Float)

    # Quality
    data_quality_score = Column(Float)
    confidence_level = Column(Float)

    # Recommendations
    follow_up_recommendations = Column(JSON, default=[])
    suggested_next_questions = Column(JSON, default=[])

    # Metadata
    generated_by = Column(String(255), default="system")
    model_used = Column(String(100))

    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    interview = relationship("InterviewModel", back_populates="insights")


class MetricsModel(Base):
    """Metrics tracking database model"""
    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Metric identification
    metric_name = Column(String(255), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)  # counter, gauge, histogram

    # Values
    value = Column(Float, nullable=False)
    labels = Column(JSON, default={})

    # Context
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id"), index=True)
    call_guide_id = Column(UUID(as_uuid=True), ForeignKey("call_guides.id"), index=True)

    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class WebhookModel(Base):
    """Webhook configuration database model"""
    __tablename__ = "webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Configuration
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, default=[])  # List of event types to trigger on

    # Security
    secret = Column(String(255))
    headers = Column(JSON, default={})

    # Status
    is_active = Column(Boolean, default=True, index=True)
    last_triggered_at = Column(DateTime)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EventLogModel(Base):
    """Event log for audit trail"""
    __tablename__ = "event_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, default={})

    # Context
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id"), index=True)
    user_id = Column(String(255), index=True)

    # Metadata
    ip_address = Column(String(50))
    user_agent = Column(String(500))

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
