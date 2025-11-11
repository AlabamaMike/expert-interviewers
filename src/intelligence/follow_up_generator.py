"""
Follow-up Generator - Dynamically generates contextual follow-up questions
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from ..models.call_guide import Question, FollowUpAction
from ..models.interview import InterviewResponse
from .llm_provider import LLMProvider
from .response_analyzer import ResponseAnalysis

logger = logging.getLogger(__name__)


@dataclass
class FollowUpQuestion:
    """A generated follow-up question"""
    question_text: str
    reason: str  # Why this follow-up is valuable
    action_type: FollowUpAction
    priority: float  # 0.0 to 1.0
    expected_insight: str  # What insight we hope to gain


class FollowUpGenerator:
    """Generates adaptive follow-up questions based on responses"""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize follow-up generator

        Args:
            llm_provider: LLM provider for generation
        """
        self.llm = llm_provider
        logger.info("Initialized FollowUpGenerator")

        # Follow-up templates for different triggers
        self.templates = {
            FollowUpAction.DRILL_DEEPER: [
                "Can you tell me more about {topic}?",
                "What specifically about {topic} stands out to you?",
                "Help me understand {topic} in more detail.",
            ],
            FollowUpAction.PROBE: [
                "That's interesting. Can you elaborate on that?",
                "What led you to that conclusion?",
                "Can you walk me through your thinking on that?",
            ],
            FollowUpAction.CLARIFY: [
                "Just to make sure I understand, you're saying {clarification}?",
                "Can you clarify what you mean by {term}?",
                "I want to make sure I understand - could you explain that differently?",
            ],
            FollowUpAction.EXAMPLE: [
                "Can you give me a specific example of that?",
                "When was the last time you experienced that?",
                "Can you describe a situation where that happened?",
            ],
            FollowUpAction.COMPARE: [
                "How does that compare to {comparison}?",
                "What's different about {aspect} compared to before?",
                "How would you contrast that with {alternative}?",
            ],
        }

    async def generate_follow_ups(
        self,
        original_question: Question,
        response: str,
        analysis: ResponseAnalysis,
        context: Optional[Dict[str, Any]] = None,
        max_follow_ups: int = 3,
    ) -> List[FollowUpQuestion]:
        """
        Generate contextual follow-up questions

        Args:
            original_question: The original question asked
            response: The respondent's answer
            analysis: Analysis of the response
            context: Optional context (interview history, objectives, etc.)
            max_follow_ups: Maximum number of follow-ups to generate

        Returns:
            List of generated follow-up questions, ranked by priority
        """
        try:
            # Determine if follow-ups are needed
            if not self._should_generate_follow_ups(analysis, original_question):
                logger.debug("No follow-ups needed for this response")
                return []

            # Build generation prompt
            prompt = self._build_generation_prompt(
                original_question, response, analysis, context
            )

            # Define output schema
            schema = {
                "type": "object",
                "properties": {
                    "follow_ups": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_text": {"type": "string"},
                                "reason": {"type": "string"},
                                "action_type": {
                                    "type": "string",
                                    "enum": ["drill_deeper", "probe", "clarify", "example", "compare"]
                                },
                                "priority": {"type": "number", "minimum": 0, "maximum": 1},
                                "expected_insight": {"type": "string"}
                            },
                            "required": ["question_text", "reason", "action_type", "priority"]
                        },
                        "maxItems": max_follow_ups
                    }
                },
                "required": ["follow_ups"]
            }

            # Generate follow-ups
            result = await self.llm.generate_structured(
                prompt=prompt,
                output_schema=schema,
                system_prompt="You are an expert interviewer skilled at asking insightful follow-up questions."
            )

            # Convert to FollowUpQuestion objects
            follow_ups = [
                FollowUpQuestion(
                    question_text=fu["question_text"],
                    reason=fu["reason"],
                    action_type=FollowUpAction(fu["action_type"]),
                    priority=fu["priority"],
                    expected_insight=fu.get("expected_insight", "")
                )
                for fu in result.get("follow_ups", [])
            ]

            # Sort by priority
            follow_ups.sort(key=lambda x: x.priority, reverse=True)

            logger.info(f"Generated {len(follow_ups)} follow-up questions")
            return follow_ups

        except Exception as e:
            logger.error(f"Error generating follow-ups: {e}")
            return []

    def _should_generate_follow_ups(
        self,
        analysis: ResponseAnalysis,
        original_question: Question
    ) -> bool:
        """
        Determine if follow-ups should be generated

        Args:
            analysis: Response analysis
            original_question: Original question

        Returns:
            True if follow-ups are warranted
        """
        # Generate follow-ups if:
        # 1. Response requires clarification
        if analysis.requires_clarification:
            return True

        # 2. Low information density (vague answer)
        if analysis.information_density < 0.4:
            return True

        # 3. Strong signals of interest (enthusiasm, emotion)
        if any(signal in analysis.signals for signal in ["enthusiasm", "emotional"]):
            return True

        # 4. Contradictions detected
        if analysis.contradictions:
            return True

        # 5. High information density (valuable, worth exploring more)
        if analysis.information_density > 0.7:
            return True

        # 6. Question has configured follow-up triggers
        if original_question.follow_up_triggers:
            return True

        return False

    def _build_generation_prompt(
        self,
        original_question: Question,
        response: str,
        analysis: ResponseAnalysis,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for follow-up generation"""
        prompt = f"""Generate insightful follow-up questions for this interview response:

**Original Question:**
{original_question.text}

**Respondent's Answer:**
{response}

**Analysis:**
- Sentiment: {analysis.sentiment.value}
- Information Density: {analysis.information_density:.2f}
- Key Themes: {', '.join(analysis.themes)}
- Signals: {', '.join(analysis.signals)}
- Requires Clarification: {analysis.requires_clarification}
"""

        if analysis.contradictions:
            prompt += f"\n- Contradictions: {', '.join(analysis.contradictions)}\n"

        if context:
            if context.get("research_objective"):
                prompt += f"\n**Research Objective:**\n{context['research_objective']}\n"

            if context.get("time_remaining"):
                prompt += f"\n**Time Remaining:** {context['time_remaining']} seconds\n"

        prompt += """
**Task:**
Generate follow-up questions that will extract maximum insight value. Consider:

1. **DRILL_DEEPER**: Ask for more details on interesting points
2. **PROBE**: Explore reasoning and motivations
3. **CLARIFY**: Resolve vague or ambiguous statements
4. **EXAMPLE**: Request concrete examples
5. **COMPARE**: Compare with alternatives or past experiences

For each follow-up:
- Make it conversational and natural
- Focus on uncovering deeper insights
- Avoid yes/no questions
- Prioritize questions that align with research objectives
- Consider the time remaining

Generate up to 3 follow-up questions, ranked by priority (most valuable first).
"""
        return prompt

    async def apply_trigger_rules(
        self,
        question: Question,
        response: str,
        analysis: ResponseAnalysis
    ) -> List[FollowUpQuestion]:
        """
        Apply configured follow-up trigger rules

        Args:
            question: Question with trigger rules
            response: Respondent's answer
            analysis: Response analysis

        Returns:
            Follow-ups based on trigger rules
        """
        follow_ups = []

        for trigger in question.follow_up_triggers:
            # Check if trigger condition is met
            if self._check_trigger_condition(trigger.condition, response, analysis):
                # Use template if available
                if trigger.template:
                    follow_up = FollowUpQuestion(
                        question_text=trigger.template,
                        reason=f"Triggered by: {trigger.condition}",
                        action_type=trigger.action,
                        priority=trigger.priority / 10.0,  # Normalize to 0-1
                        expected_insight=f"Follow up on {trigger.action.value}"
                    )
                    follow_ups.append(follow_up)

        return follow_ups

    def _check_trigger_condition(
        self,
        condition: str,
        response: str,
        analysis: ResponseAnalysis
    ) -> bool:
        """
        Check if a trigger condition is met

        Args:
            condition: Condition string (e.g., "vague_response", "enthusiasm")
            response: Response text
            analysis: Response analysis

        Returns:
            True if condition is met
        """
        condition_lower = condition.lower()

        # Check for common trigger conditions
        if "vague" in condition_lower:
            return analysis.information_density < 0.4

        if "enthusiasm" in condition_lower:
            return "enthusiasm" in analysis.signals

        if "hesitation" in condition_lower:
            return "hesitation" in analysis.signals

        if "short" in condition_lower:
            return len(response.split()) < 20

        if "detailed" in condition_lower or "long" in condition_lower:
            return len(response.split()) > 100

        if "negative" in condition_lower:
            return "negative" in analysis.sentiment.value

        # Default: check if condition keywords appear in response
        return condition_lower in response.lower()
