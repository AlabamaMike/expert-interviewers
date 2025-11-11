"""
Call Guide data models - defines interview structure and adaptive behavior
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid


class QuestionType(str, Enum):
    """Types of questions that can be asked"""
    OPEN = "open"
    CLOSED = "closed"
    SCALE = "scale"
    MULTIPLE_CHOICE = "multiple_choice"


class FollowUpAction(str, Enum):
    """Actions to take based on response patterns"""
    DRILL_DEEPER = "drill_deeper"
    PROBE = "probe"
    CLARIFY = "clarify"
    EXAMPLE = "example"
    COMPARE = "compare"


class FollowUpTrigger(BaseModel):
    """Defines when and how to generate follow-up questions"""
    condition: str = Field(description="Pattern or condition that triggers this follow-up")
    action: FollowUpAction = Field(description="Type of follow-up action to take")
    priority: int = Field(default=1, description="Priority when multiple triggers match")
    template: Optional[str] = Field(default=None, description="Optional template for follow-up question")


class Question(BaseModel):
    """Individual question within an interview section"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str = Field(description="The question text to ask")
    type: QuestionType = Field(description="Type of question")
    required: bool = Field(default=True, description="Whether this question must be answered")
    follow_up_triggers: List[FollowUpTrigger] = Field(default_factory=list)
    max_follow_ups: int = Field(default=3, description="Maximum number of follow-up questions")
    time_allocation: int = Field(default=120, description="Time allocation in seconds")
    context: Optional[str] = Field(default=None, description="Context or background for the question")
    expected_response_patterns: List[str] = Field(default_factory=list, description="Expected patterns in responses")


class Section(BaseModel):
    """Section of the interview with related questions"""
    section_name: str = Field(description="Name of this section")
    objective: str = Field(description="Research objective for this section")
    questions: List[Question] = Field(description="Questions in this section")
    order: int = Field(default=0, description="Order of this section in the interview")
    time_limit: Optional[int] = Field(default=None, description="Time limit for this section in seconds")
    skip_conditions: List[str] = Field(default_factory=list, description="Conditions under which to skip this section")


class InterestSignal(str, Enum):
    """Signals that indicate respondent interest or engagement"""
    ENTHUSIASM = "enthusiasm"
    HESITATION = "hesitation"
    CONFUSION = "confusion"
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"
    EMOTIONAL = "emotional"


class BranchingRule(BaseModel):
    """Rules for branching logic in the interview"""
    condition: str = Field(description="Condition that triggers this branch")
    target_section: str = Field(description="Section to branch to")
    priority: int = Field(default=1)


class AdaptiveRules(BaseModel):
    """Rules for adaptive behavior during the interview"""
    interest_signals: List[InterestSignal] = Field(default_factory=list)
    branching_logic: List[BranchingRule] = Field(default_factory=list)
    skip_conditions: Dict[str, str] = Field(default_factory=dict)
    time_management: Dict[str, Any] = Field(default_factory=dict)
    complexity_adaptation: bool = Field(default=True, description="Adapt question complexity based on responses")


class RespondentProfile(BaseModel):
    """Target respondent profile for the interview"""
    demographics: Dict[str, Any] = Field(default_factory=dict)
    expertise_level: Optional[str] = None
    industry: Optional[str] = None
    role: Optional[str] = None
    experience_years: Optional[int] = None


class CallGuide(BaseModel):
    """Complete call guide definition for structured interviews"""
    guide_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="Name of this call guide")
    research_objective: str = Field(description="Overall research objective")
    target_respondent_profile: RespondentProfile = Field(default_factory=RespondentProfile)
    sections: List[Section] = Field(description="Sections of the interview")
    adaptive_rules: AdaptiveRules = Field(default_factory=AdaptiveRules)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    version: str = Field(default="1.0")
    tags: List[str] = Field(default_factory=list)

    # Interview settings
    estimated_duration_minutes: int = Field(default=30)
    max_duration_minutes: int = Field(default=60)
    min_completion_percentage: float = Field(default=0.7, description="Minimum completion to consider valid")

    # Voice settings
    voice_profile: Dict[str, Any] = Field(default_factory=lambda: {
        "speaking_rate": 150,
        "pitch_variation": "moderate",
        "energy_level": "matched_to_respondent",
        "accent": "neutral"
    })

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Product Feedback Interview",
                "research_objective": "Understand user pain points with current product",
                "sections": [
                    {
                        "section_name": "Introduction",
                        "objective": "Build rapport and set context",
                        "questions": [
                            {
                                "text": "Can you tell me about your role and how you use our product?",
                                "type": "open",
                                "required": True
                            }
                        ]
                    }
                ]
            }
        }
