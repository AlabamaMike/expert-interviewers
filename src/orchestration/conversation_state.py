"""
Conversation State Management - Tracks interview progress and context
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConversationPhase(str, Enum):
    """Phases of the interview"""
    CONSENT = "consent"
    INTRODUCTION = "introduction"
    MAIN_INTERVIEW = "main_interview"
    FOLLOW_UPS = "follow_ups"
    CLOSING = "closing"
    COMPLETED = "completed"


@dataclass
class ConversationState:
    """Tracks the current state of an interview conversation"""
    interview_id: str
    call_guide_id: str

    # Current position
    current_phase: ConversationPhase = ConversationPhase.CONSENT
    current_section_index: int = 0
    current_question_index: int = 0
    current_section_name: Optional[str] = None
    current_question_id: Optional[str] = None

    # Tracking
    questions_asked: List[str] = field(default_factory=list)
    questions_answered: List[str] = field(default_factory=list)
    questions_skipped: List[str] = field(default_factory=list)
    sections_completed: List[str] = field(default_factory=list)

    # Follow-ups
    follow_up_depth: int = 0  # Current depth of follow-up questions
    follow_up_stack: List[str] = field(default_factory=list)  # Stack of follow-up questions
    awaiting_follow_up_response: bool = False

    # Time management
    started_at: Optional[datetime] = None
    section_started_at: Optional[datetime] = None
    time_budget_seconds: int = 1800  # 30 minutes default
    time_used_seconds: float = 0

    # Context
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    key_facts_collected: Dict[str, Any] = field(default_factory=dict)
    detected_signals: List[str] = field(default_factory=list)

    # Flags
    consent_given: bool = False
    should_terminate: bool = False
    termination_reason: Optional[str] = None
    requires_human_escalation: bool = False

    def add_message(self, speaker: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to conversation history"""
        self.conversation_history.append({
            "timestamp": datetime.utcnow(),
            "speaker": speaker,
            "text": text,
            "metadata": metadata or {}
        })

    def get_time_remaining(self) -> float:
        """Calculate time remaining in seconds"""
        if not self.started_at:
            return self.time_budget_seconds

        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        return max(0, self.time_budget_seconds - elapsed)

    def get_progress_percentage(self, total_questions: int) -> float:
        """Calculate interview progress percentage"""
        if total_questions == 0:
            return 0.0
        return len(self.questions_answered) / total_questions

    def should_prioritize_remaining_questions(self) -> bool:
        """Check if we should skip follow-ups to finish core questions"""
        time_remaining = self.get_time_remaining()
        remaining_questions = len(self.questions_asked) - len(self.questions_answered)

        # If less than 5 minutes and more than 3 questions remaining, prioritize
        return time_remaining < 300 and remaining_questions > 3


class ConversationStateManager:
    """Manages conversation state for multiple interviews"""

    def __init__(self):
        """Initialize state manager"""
        self.states: Dict[str, ConversationState] = {}
        logger.info("Initialized ConversationStateManager")

    def create_state(
        self,
        interview_id: str,
        call_guide_id: str,
        time_budget_seconds: int = 1800
    ) -> ConversationState:
        """
        Create a new conversation state

        Args:
            interview_id: Interview ID
            call_guide_id: Call guide ID
            time_budget_seconds: Time budget for interview

        Returns:
            New ConversationState
        """
        state = ConversationState(
            interview_id=interview_id,
            call_guide_id=call_guide_id,
            time_budget_seconds=time_budget_seconds,
            started_at=datetime.utcnow()
        )
        self.states[interview_id] = state
        logger.info(f"Created conversation state for interview {interview_id}")
        return state

    def get_state(self, interview_id: str) -> Optional[ConversationState]:
        """Get state for an interview"""
        return self.states.get(interview_id)

    def update_state(self, interview_id: str, state: ConversationState):
        """Update state for an interview"""
        self.states[interview_id] = state
        logger.debug(f"Updated state for interview {interview_id}")

    def delete_state(self, interview_id: str):
        """Delete state for an interview"""
        if interview_id in self.states:
            del self.states[interview_id]
            logger.info(f"Deleted state for interview {interview_id}")

    def advance_to_next_question(
        self,
        state: ConversationState,
        total_questions_in_section: int
    ) -> bool:
        """
        Advance to next question

        Args:
            state: Current state
            total_questions_in_section: Total questions in current section

        Returns:
            True if advanced, False if section is complete
        """
        state.current_question_index += 1

        if state.current_question_index >= total_questions_in_section:
            # Section complete
            if state.current_section_name:
                state.sections_completed.append(state.current_section_name)
            return False

        return True

    def advance_to_next_section(
        self,
        state: ConversationState,
        total_sections: int
    ) -> bool:
        """
        Advance to next section

        Args:
            state: Current state
            total_sections: Total number of sections

        Returns:
            True if advanced, False if interview is complete
        """
        state.current_section_index += 1
        state.current_question_index = 0
        state.section_started_at = datetime.utcnow()

        if state.current_section_index >= total_sections:
            # Interview complete
            state.current_phase = ConversationPhase.CLOSING
            return False

        return True

    def push_follow_up(self, state: ConversationState, follow_up_text: str):
        """Push a follow-up question onto the stack"""
        state.follow_up_stack.append(follow_up_text)
        state.follow_up_depth += 1
        state.awaiting_follow_up_response = True
        logger.debug(f"Pushed follow-up, depth now: {state.follow_up_depth}")

    def pop_follow_up(self, state: ConversationState) -> Optional[str]:
        """Pop a follow-up question from the stack"""
        if state.follow_up_stack:
            follow_up = state.follow_up_stack.pop()
            state.follow_up_depth = len(state.follow_up_stack)
            state.awaiting_follow_up_response = len(state.follow_up_stack) > 0
            logger.debug(f"Popped follow-up, depth now: {state.follow_up_depth}")
            return follow_up
        return None

    def should_generate_follow_up(
        self,
        state: ConversationState,
        max_follow_up_depth: int = 3
    ) -> bool:
        """
        Determine if we should generate a follow-up question

        Args:
            state: Current state
            max_follow_up_depth: Maximum allowed follow-up depth

        Returns:
            True if follow-up should be generated
        """
        # Don't generate follow-ups if:
        # 1. Already at max depth
        if state.follow_up_depth >= max_follow_up_depth:
            return False

        # 2. Should prioritize remaining questions due to time
        if state.should_prioritize_remaining_questions():
            return False

        # 3. Already have pending follow-ups
        if state.follow_up_stack:
            return False

        return True
