"""
Interview session and response models
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid


class InterviewStatus(str, Enum):
    """Status of an interview session"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ResponseSentiment(str, Enum):
    """Sentiment of a response"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class InterviewResponse(BaseModel):
    """A single response within an interview"""
    response_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    interview_id: str = Field(description="ID of the parent interview")
    question_id: str = Field(description="ID of the question being answered")
    section_name: str = Field(description="Section this response belongs to")

    # Response content
    question_text: str = Field(description="The question that was asked")
    response_text: str = Field(description="The respondent's answer")
    response_audio_url: Optional[str] = Field(default=None, description="URL to audio recording")

    # Timing
    asked_at: datetime = Field(default_factory=datetime.utcnow)
    answered_at: Optional[datetime] = None
    response_time_seconds: Optional[float] = None

    # Analysis
    sentiment: Optional[ResponseSentiment] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    key_phrases: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    information_density: Optional[float] = Field(default=None, description="Measure of insight value")

    # Follow-ups
    is_follow_up: bool = Field(default=False)
    parent_response_id: Optional[str] = None
    follow_up_count: int = Field(default=0)
    generated_follow_ups: List[str] = Field(default_factory=list)

    # Quality metrics
    is_complete: bool = Field(default=True)
    requires_clarification: bool = Field(default=False)
    flags: List[str] = Field(default_factory=list)


class TranscriptEntry(BaseModel):
    """Single entry in interview transcript"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    speaker: str = Field(description="'agent' or 'respondent'")
    text: str = Field(description="Spoken text")
    confidence: Optional[float] = Field(default=None, description="STT confidence")
    duration_seconds: Optional[float] = None


class InterviewTranscript(BaseModel):
    """Complete transcript of an interview"""
    interview_id: str
    entries: List[TranscriptEntry] = Field(default_factory=list)
    total_duration_seconds: float = 0
    word_count: int = 0
    agent_talk_time_seconds: float = 0
    respondent_talk_time_seconds: float = 0


class EngagementMetrics(BaseModel):
    """Metrics tracking respondent engagement"""
    avg_response_length: float = 0
    avg_response_time: float = 0
    enthusiasm_score: float = Field(default=0, ge=0.0, le=1.0)
    hesitation_count: int = 0
    interruption_count: int = 0
    silence_count: int = 0
    overall_engagement: float = Field(default=0, ge=0.0, le=1.0)


class QualityMetrics(BaseModel):
    """Quality metrics for the interview"""
    completion_percentage: float = Field(ge=0.0, le=1.0)
    questions_asked: int = 0
    questions_answered: int = 0
    follow_ups_generated: int = 0
    insight_yield: float = Field(default=0, description="Valuable findings per minute")
    guide_adherence: float = Field(default=0, ge=0.0, le=1.0)
    technical_quality_score: float = Field(default=0, ge=0.0, le=1.0)
    stt_accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class Interview(BaseModel):
    """Complete interview session"""
    interview_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_guide_id: str = Field(description="ID of the call guide used")

    # Respondent info
    respondent_id: Optional[str] = None
    respondent_name: Optional[str] = None
    respondent_phone: str
    respondent_email: Optional[str] = None
    respondent_metadata: Dict[str, Any] = Field(default_factory=dict)

    # Session info
    status: InterviewStatus = Field(default=InterviewStatus.SCHEDULED)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Call details
    call_sid: Optional[str] = Field(default=None, description="Twilio call SID")
    recording_url: Optional[str] = None

    # Responses
    responses: List[InterviewResponse] = Field(default_factory=list)
    current_section: Optional[str] = None
    current_question_id: Optional[str] = None

    # State
    conversation_state: Dict[str, Any] = Field(default_factory=dict)
    sections_completed: List[str] = Field(default_factory=list)
    questions_skipped: List[str] = Field(default_factory=list)

    # Metrics
    engagement_metrics: EngagementMetrics = Field(default_factory=EngagementMetrics)
    quality_metrics: QualityMetrics = Field(default_factory=QualityMetrics)

    # Flags and notes
    requires_human_review: bool = Field(default=False)
    escalation_reason: Optional[str] = None
    interviewer_notes: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    # Consent and compliance
    consent_given: bool = Field(default=False)
    consent_timestamp: Optional[datetime] = None
    gdpr_compliant: bool = Field(default=True)
    can_be_recorded: bool = Field(default=True)

    class Config:
        json_schema_extra = {
            "example": {
                "call_guide_id": "uuid-here",
                "respondent_phone": "+1234567890",
                "status": "scheduled",
                "scheduled_at": "2024-01-15T10:00:00Z"
            }
        }
