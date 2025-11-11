"""
Interview Orchestrator - Main controller for conducting autonomous interviews
"""

from typing import Optional, Dict, Any, List
import logging
import asyncio
from datetime import datetime

from ..models.call_guide import CallGuide, Question, Section
from ..models.interview import (
    Interview, InterviewResponse, InterviewStatus,
    ResponseSentiment, EngagementMetrics, QualityMetrics
)
from ..intelligence.llm_provider import LLMProvider
from ..intelligence.response_analyzer import ResponseAnalyzer
from ..intelligence.follow_up_generator import FollowUpGenerator
from ..voice_engine.stt import STTProvider
from ..voice_engine.tts import TTSProvider
from .conversation_state import (
    ConversationState, ConversationStateManager, ConversationPhase
)

logger = logging.getLogger(__name__)


class InterviewOrchestrator:
    """
    Orchestrates autonomous research interviews

    This is the main controller that:
    1. Manages conversation flow through call guide
    2. Coordinates STT/TTS for voice interaction
    3. Analyzes responses in real-time
    4. Generates adaptive follow-up questions
    5. Maintains conversation state
    6. Handles edge cases and escalation
    """

    def __init__(
        self,
        stt_provider: STTProvider,
        tts_provider: TTSProvider,
        llm_provider: LLMProvider,
        state_manager: Optional[ConversationStateManager] = None
    ):
        """
        Initialize interview orchestrator

        Args:
            stt_provider: Speech-to-text provider
            tts_provider: Text-to-speech provider
            llm_provider: LLM provider for intelligence
            state_manager: Optional state manager (creates new if None)
        """
        self.stt = stt_provider
        self.tts = tts_provider
        self.llm = llm_provider
        self.state_manager = state_manager or ConversationStateManager()

        # Initialize intelligence components
        self.response_analyzer = ResponseAnalyzer(llm_provider)
        self.follow_up_generator = FollowUpGenerator(llm_provider)

        logger.info("Initialized InterviewOrchestrator")

    async def conduct_interview(
        self,
        call_guide: CallGuide,
        interview: Interview,
        audio_stream_handler: Any  # Handler for audio I/O
    ) -> Interview:
        """
        Conduct a complete interview

        Args:
            call_guide: Call guide to follow
            interview: Interview object to populate
            audio_stream_handler: Handler for audio input/output

        Returns:
            Completed Interview object
        """
        try:
            logger.info(f"Starting interview {interview.interview_id}")

            # Initialize conversation state
            state = self.state_manager.create_state(
                interview_id=interview.interview_id,
                call_guide_id=call_guide.guide_id,
                time_budget_seconds=call_guide.max_duration_minutes * 60
            )

            # Update interview status
            interview.status = InterviewStatus.IN_PROGRESS
            interview.started_at = datetime.utcnow()

            # Phase 1: Consent
            if not await self._handle_consent_phase(state, interview, audio_stream_handler):
                interview.status = InterviewStatus.FAILED
                interview.completed_at = datetime.utcnow()
                return interview

            # Phase 2: Introduction
            await self._handle_introduction_phase(
                state, call_guide, interview, audio_stream_handler
            )

            # Phase 3: Main Interview
            await self._handle_main_interview_phase(
                state, call_guide, interview, audio_stream_handler
            )

            # Phase 4: Closing
            await self._handle_closing_phase(
                state, call_guide, interview, audio_stream_handler
            )

            # Finalize interview
            interview.status = InterviewStatus.COMPLETED
            interview.completed_at = datetime.utcnow()
            interview.duration_seconds = (
                interview.completed_at - interview.started_at
            ).total_seconds()

            # Calculate final metrics
            self._calculate_final_metrics(interview, call_guide)

            logger.info(f"Completed interview {interview.interview_id}")
            return interview

        except Exception as e:
            logger.error(f"Error conducting interview: {e}", exc_info=True)
            interview.status = InterviewStatus.FAILED
            interview.completed_at = datetime.utcnow()
            interview.escalation_reason = f"System error: {str(e)}"
            return interview

    async def _handle_consent_phase(
        self,
        state: ConversationState,
        interview: Interview,
        audio_handler: Any
    ) -> bool:
        """
        Handle consent collection phase

        Returns:
            True if consent given, False otherwise
        """
        logger.info("Starting consent phase")
        state.current_phase = ConversationPhase.CONSENT

        # Prepare consent statement
        consent_text = """
        Thank you for participating in this research interview. Before we begin,
        I need to inform you that this call may be recorded for quality and research purposes.
        Your responses will be kept confidential and used only for research.
        You may stop the interview at any time. Do you consent to participate in this interview?
        """

        # Speak consent statement
        await self._speak(consent_text, audio_handler)
        state.add_message("agent", consent_text)

        # Listen for response
        response = await self._listen(audio_handler, timeout=30)
        state.add_message("respondent", response)

        # Analyze consent response
        consent_given = await self._analyze_consent(response)

        if consent_given:
            state.consent_given = True
            interview.consent_given = True
            interview.consent_timestamp = datetime.utcnow()
            await self._speak("Thank you. Let's begin.", audio_handler)
            logger.info("Consent received")
            return True
        else:
            await self._speak(
                "I understand. Thank you for your time. Goodbye.",
                audio_handler
            )
            logger.info("Consent denied")
            return False

    async def _handle_introduction_phase(
        self,
        state: ConversationState,
        call_guide: CallGuide,
        interview: Interview,
        audio_handler: Any
    ):
        """Handle introduction phase"""
        logger.info("Starting introduction phase")
        state.current_phase = ConversationPhase.INTRODUCTION

        intro_text = f"""
        Great! This interview will take approximately {call_guide.estimated_duration_minutes} minutes.
        I'll be asking you questions about {call_guide.research_objective}.
        Feel free to share your thoughts openly - there are no right or wrong answers.
        Are you ready to begin?
        """

        await self._speak(intro_text, audio_handler)
        state.add_message("agent", intro_text)

        response = await self._listen(audio_handler, timeout=15)
        state.add_message("respondent", response)

        # Proceed regardless of response (assuming readiness)
        await self._speak("Excellent. Let's get started.", audio_handler)

    async def _handle_main_interview_phase(
        self,
        state: ConversationState,
        call_guide: CallGuide,
        interview: Interview,
        audio_handler: Any
    ):
        """Handle main interview phase"""
        logger.info("Starting main interview phase")
        state.current_phase = ConversationPhase.MAIN_INTERVIEW

        # Iterate through sections
        for section_idx, section in enumerate(call_guide.sections):
            state.current_section_index = section_idx
            state.current_section_name = section.section_name
            state.section_started_at = datetime.utcnow()

            logger.info(f"Starting section: {section.section_name}")

            # Check if should skip section
            if await self._should_skip_section(section, state, interview):
                logger.info(f"Skipping section: {section.section_name}")
                continue

            # Optional: Announce section transition
            if section_idx > 0:
                transition = f"Now let's talk about {section.section_name.lower()}."
                await self._speak(transition, audio_handler)

            # Iterate through questions in section
            for question_idx, question in enumerate(section.questions):
                state.current_question_index = question_idx
                state.current_question_id = question.id

                # Check time constraints
                if state.get_time_remaining() < 60:  # Less than 1 minute
                    logger.warning("Time running out, wrapping up")
                    break

                # Ask question and handle response
                await self._handle_question_response_cycle(
                    question, section, state, call_guide, interview, audio_handler
                )

            # Mark section as completed
            state.sections_completed.append(section.section_name)

    async def _handle_question_response_cycle(
        self,
        question: Question,
        section: Section,
        state: ConversationState,
        call_guide: CallGuide,
        interview: Interview,
        audio_handler: Any
    ):
        """Handle a complete question-response cycle with follow-ups"""
        logger.debug(f"Asking question: {question.text}")

        # Speak question
        await self._speak(question.text, audio_handler)
        state.add_message("agent", question.text)
        state.questions_asked.append(question.id)

        asked_at = datetime.utcnow()

        # Listen for response
        response_text = await self._listen(audio_handler, timeout=120)
        answered_at = datetime.utcnow()

        state.add_message("respondent", response_text)
        state.questions_answered.append(question.id)

        # Create response record
        interview_response = InterviewResponse(
            interview_id=interview.interview_id,
            question_id=question.id,
            section_name=section.section_name,
            question_text=question.text,
            response_text=response_text,
            asked_at=asked_at,
            answered_at=answered_at,
            response_time_seconds=(answered_at - asked_at).total_seconds()
        )

        # Analyze response
        context = {
            "research_objective": call_guide.research_objective,
            "previous_responses": state.conversation_history[-5:],  # Last 5 exchanges
            "time_remaining": state.get_time_remaining()
        }

        analysis = await self.response_analyzer.analyze_response(
            question=question.text,
            response=response_text,
            context=context
        )

        # Update response with analysis
        interview_response.sentiment = analysis.sentiment
        interview_response.confidence_score = analysis.confidence
        interview_response.key_phrases = analysis.key_phrases
        interview_response.themes = analysis.themes
        interview_response.information_density = analysis.information_density
        interview_response.requires_clarification = analysis.requires_clarification

        # Add to interview
        interview.responses.append(interview_response)

        # Update engagement metrics
        state.detected_signals.extend(analysis.signals)

        # Provide brief acknowledgment
        acknowledgment = await self._generate_acknowledgment(analysis)
        await self._speak(acknowledgment, audio_handler)

        # Generate and ask follow-up questions if appropriate
        if self.state_manager.should_generate_follow_up(state, question.max_follow_ups):
            await self._handle_follow_ups(
                question, response_text, analysis, section,
                state, call_guide, interview, audio_handler
            )

    async def _handle_follow_ups(
        self,
        original_question: Question,
        response: str,
        analysis: Any,
        section: Section,
        state: ConversationState,
        call_guide: CallGuide,
        interview: Interview,
        audio_handler: Any
    ):
        """Generate and ask follow-up questions"""
        logger.debug("Generating follow-up questions")

        context = {
            "research_objective": call_guide.research_objective,
            "time_remaining": state.get_time_remaining()
        }

        # Generate follow-ups
        follow_ups = await self.follow_up_generator.generate_follow_ups(
            original_question=original_question,
            response=response,
            analysis=analysis,
            context=context,
            max_follow_ups=min(2, original_question.max_follow_ups)
        )

        # Ask top priority follow-up
        if follow_ups and state.follow_up_depth < original_question.max_follow_ups:
            top_follow_up = follow_ups[0]
            logger.info(f"Asking follow-up: {top_follow_up.question_text}")

            await self._speak(top_follow_up.question_text, audio_handler)
            state.add_message("agent", top_follow_up.question_text)
            state.follow_up_depth += 1

            # Listen for follow-up response
            follow_up_response = await self._listen(audio_handler, timeout=120)
            state.add_message("respondent", follow_up_response)

            # Create follow-up response record
            follow_up_record = InterviewResponse(
                interview_id=interview.interview_id,
                question_id=f"{original_question.id}_followup_{state.follow_up_depth}",
                section_name=section.section_name,
                question_text=top_follow_up.question_text,
                response_text=follow_up_response,
                is_follow_up=True,
                parent_response_id=interview.responses[-1].response_id if interview.responses else None,
                asked_at=datetime.utcnow(),
                answered_at=datetime.utcnow()
            )

            interview.responses.append(follow_up_record)

            # Acknowledge
            await self._speak("Thank you for elaborating.", audio_handler)

    async def _handle_closing_phase(
        self,
        state: ConversationState,
        call_guide: CallGuide,
        interview: Interview,
        audio_handler: Any
    ):
        """Handle closing phase"""
        logger.info("Starting closing phase")
        state.current_phase = ConversationPhase.CLOSING

        closing_text = """
        Thank you so much for sharing your thoughts with me today.
        Your insights are very valuable for our research.
        Is there anything else you'd like to add before we finish?
        """

        await self._speak(closing_text, audio_handler)
        state.add_message("agent", closing_text)

        # Listen for any final thoughts
        final_thoughts = await self._listen(audio_handler, timeout=60)
        if final_thoughts and len(final_thoughts) > 10:
            state.add_message("respondent", final_thoughts)
            interview.interviewer_notes.append(f"Final thoughts: {final_thoughts}")

        # Final goodbye
        goodbye = "Thank you again for your time. Have a great day!"
        await self._speak(goodbye, audio_handler)

        state.current_phase = ConversationPhase.COMPLETED

    async def _speak(self, text: str, audio_handler: Any):
        """Convert text to speech and play"""
        try:
            # Generate speech
            audio_result = await self.tts.synthesize(text)

            # Play audio through handler
            if hasattr(audio_handler, 'play_audio'):
                await audio_handler.play_audio(audio_result.audio_data)

            logger.debug(f"Spoke: {text[:50]}...")
        except Exception as e:
            logger.error(f"Error in speech synthesis: {e}")

    async def _listen(self, audio_handler: Any, timeout: int = 30) -> str:
        """Listen for and transcribe speech"""
        try:
            # Get audio stream from handler
            if hasattr(audio_handler, 'get_audio_stream'):
                audio_stream = audio_handler.get_audio_stream(timeout=timeout)
            else:
                # Mock for testing
                await asyncio.sleep(0.5)
                return "This is a mock response"

            # Transcribe
            transcription = ""
            async for result in self.stt.transcribe_stream(audio_stream):
                if result.is_final:
                    transcription += result.text + " "

            logger.debug(f"Heard: {transcription[:50]}...")
            return transcription.strip()

        except Exception as e:
            logger.error(f"Error in speech recognition: {e}")
            return ""

    async def _analyze_consent(self, response: str) -> bool:
        """Analyze if consent was given"""
        response_lower = response.lower()
        affirmative_words = ["yes", "yeah", "sure", "okay", "agree", "consent", "ok"]
        negative_words = ["no", "nope", "don't", "disagree", "refuse"]

        # Check for affirmative
        if any(word in response_lower for word in affirmative_words):
            return True

        # Check for negative
        if any(word in response_lower for word in negative_words):
            return False

        # Default to True for ambiguous (could use LLM for better analysis)
        return True

    async def _should_skip_section(
        self,
        section: Section,
        state: ConversationState,
        interview: Interview
    ) -> bool:
        """Determine if a section should be skipped"""
        # Check skip conditions
        for condition in section.skip_conditions:
            # Simple keyword-based condition checking
            # In production, this would use LLM for more sophisticated logic
            if condition in str(state.key_facts_collected):
                return True

        return False

    async def _generate_acknowledgment(self, analysis: Any) -> str:
        """Generate brief acknowledgment based on response analysis"""
        if "enthusiasm" in analysis.signals:
            return "That's great!"
        elif "hesitation" in analysis.signals:
            return "I see."
        elif analysis.sentiment.value == "positive":
            return "Interesting."
        else:
            return "I understand."

    def _calculate_final_metrics(self, interview: Interview, call_guide: CallGuide):
        """Calculate final quality and engagement metrics"""
        responses = interview.responses

        if not responses:
            return

        # Quality metrics
        total_questions = sum(len(section.questions) for section in call_guide.sections)
        interview.quality_metrics.questions_asked = len([r for r in responses if not r.is_follow_up])
        interview.quality_metrics.questions_answered = len([r for r in responses if r.response_text])
        interview.quality_metrics.follow_ups_generated = len([r for r in responses if r.is_follow_up])
        interview.quality_metrics.completion_percentage = (
            interview.quality_metrics.questions_answered / max(total_questions, 1)
        )

        # Engagement metrics
        response_lengths = [len(r.response_text.split()) for r in responses if r.response_text]
        if response_lengths:
            interview.engagement_metrics.avg_response_length = sum(response_lengths) / len(response_lengths)

        response_times = [r.response_time_seconds for r in responses if r.response_time_seconds]
        if response_times:
            interview.engagement_metrics.avg_response_time = sum(response_times) / len(response_times)

        # Overall engagement score (simple heuristic)
        engagement_score = 0.0
        if interview.engagement_metrics.avg_response_length > 30:
            engagement_score += 0.4
        if interview.quality_metrics.completion_percentage > 0.7:
            engagement_score += 0.3
        if interview.quality_metrics.follow_ups_generated > 0:
            engagement_score += 0.3

        interview.engagement_metrics.overall_engagement = min(1.0, engagement_score)

        logger.info(f"Final metrics - Completion: {interview.quality_metrics.completion_percentage:.1%}, "
                   f"Engagement: {interview.engagement_metrics.overall_engagement:.2f}")
