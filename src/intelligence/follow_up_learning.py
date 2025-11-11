"""
Follow-up Learning System
Learns from successful follow-up patterns to improve future question generation
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
import json

from ..models.interview import Interview, InterviewResponse
from ..models.call_guide import FollowUpAction
from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class FollowUpOutcome:
    """Outcome of a follow-up question"""
    follow_up_question: str
    follow_up_action: FollowUpAction
    original_response_quality: float
    follow_up_response_quality: float
    improvement_score: float  # How much better the follow-up response was
    context: str
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FollowUpPattern:
    """Learned pattern for follow-ups"""
    pattern_id: str
    pattern_type: str  # e.g., "vague_to_specific", "enthusiasm_probe"
    trigger_conditions: List[str]
    effective_actions: List[FollowUpAction]
    success_rate: float
    sample_count: int
    avg_improvement: float
    best_examples: List[str]
    learned_from_interviews: List[str]
    last_updated: datetime


@dataclass
class QuestionTemplate:
    """Template for generating follow-up questions"""
    template_id: str
    template_text: str
    action_type: FollowUpAction
    effectiveness_score: float
    usage_count: int
    success_count: int
    applicable_contexts: List[str]
    variables: List[str]  # Variables in template (e.g., {topic}, {concern})


class FollowUpLearningSystem:
    """System for learning and improving follow-up question generation"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        min_pattern_samples: int = 5,
        min_success_rate: float = 0.6
    ):
        """
        Initialize learning system

        Args:
            llm_provider: LLM provider for analysis
            min_pattern_samples: Minimum samples to establish a pattern
            min_success_rate: Minimum success rate to consider pattern valid
        """
        self.llm = llm_provider
        self.min_pattern_samples = min_pattern_samples
        self.min_success_rate = min_success_rate

        # Storage for learned patterns
        self.patterns: Dict[str, FollowUpPattern] = {}
        self.templates: Dict[str, QuestionTemplate] = {}
        self.outcomes: List[FollowUpOutcome] = []

        # Statistics
        self.action_effectiveness: Dict[FollowUpAction, List[float]] = defaultdict(list)

        logger.info("Initialized FollowUpLearningSystem")

    async def learn_from_interview(self, interview: Interview):
        """
        Learn from a completed interview

        Args:
            interview: Completed interview to analyze
        """
        try:
            # Identify follow-up sequences
            sequences = self._identify_follow_up_sequences(interview)

            # Analyze each sequence
            for sequence in sequences:
                outcome = await self._analyze_follow_up_outcome(sequence)
                if outcome:
                    self.outcomes.append(outcome)

                    # Track action effectiveness
                    self.action_effectiveness[outcome.follow_up_action].append(
                        outcome.improvement_score
                    )

            # Update patterns every N interviews
            if len(self.outcomes) >= self.min_pattern_samples:
                await self._update_patterns()

            logger.info(f"Learned from interview {interview.interview_id}")

        except Exception as e:
            logger.error(f"Error learning from interview: {e}")

    def _identify_follow_up_sequences(
        self,
        interview: Interview
    ) -> List[Tuple[InterviewResponse, InterviewResponse]]:
        """Identify follow-up question sequences in interview"""
        sequences = []

        responses = interview.responses
        for i in range(len(responses) - 1):
            current = responses[i]
            next_response = responses[i + 1]

            # Check if next response is a follow-up
            # (In a real system, this would be tracked explicitly)
            if self._is_follow_up(current, next_response):
                sequences.append((current, next_response))

        return sequences

    def _is_follow_up(
        self,
        original: InterviewResponse,
        potential_follow_up: InterviewResponse
    ) -> bool:
        """Determine if a response is a follow-up to another"""
        # Simple heuristic: check if questions are in same section and sequential
        return (
            original.section_name == potential_follow_up.section_name and
            original.sequence_number + 1 == potential_follow_up.sequence_number
        )

    async def _analyze_follow_up_outcome(
        self,
        sequence: Tuple[InterviewResponse, InterviewResponse]
    ) -> Optional[FollowUpOutcome]:
        """Analyze the outcome of a follow-up question"""
        try:
            original, follow_up = sequence

            # Calculate response quality scores
            original_quality = self._calculate_response_quality(original)
            follow_up_quality = self._calculate_response_quality(follow_up)

            # Calculate improvement
            improvement = follow_up_quality - original_quality

            # Determine action type (simplified - would be tracked in real system)
            action = self._infer_follow_up_action(original, follow_up)

            # Determine success
            success = improvement > 0.1  # Threshold for meaningful improvement

            outcome = FollowUpOutcome(
                follow_up_question=follow_up.question_text,
                follow_up_action=action,
                original_response_quality=original_quality,
                follow_up_response_quality=follow_up_quality,
                improvement_score=improvement,
                context=f"Original: {original.response_text[:100]}...",
                success=success,
                metadata={
                    "original_sentiment": original.sentiment.value if original.sentiment else "unknown",
                    "follow_up_sentiment": follow_up.sentiment.value if follow_up.sentiment else "unknown",
                    "section": original.section_name
                }
            )

            return outcome

        except Exception as e:
            logger.error(f"Error analyzing follow-up outcome: {e}")
            return None

    def _calculate_response_quality(self, response: InterviewResponse) -> float:
        """Calculate quality score for a response"""
        # Combine multiple quality indicators
        factors = []

        # Length (normalized)
        word_count = len(response.response_text.split())
        length_score = min(1.0, word_count / 50.0)  # 50 words = full score
        factors.append(length_score)

        # Information density from metadata
        if "information_density" in response.analysis_metadata:
            factors.append(response.analysis_metadata["information_density"])

        # Sentiment (neutral to positive is good)
        if response.sentiment:
            sentiment_map = {
                "very_positive": 1.0,
                "positive": 0.8,
                "neutral": 0.7,
                "negative": 0.5,
                "very_negative": 0.3
            }
            sentiment_score = sentiment_map.get(response.sentiment.value, 0.7)
            factors.append(sentiment_score)

        # Theme count (more themes = richer response)
        theme_score = min(1.0, len(response.themes) / 3.0)
        factors.append(theme_score)

        # Average all factors
        return sum(factors) / len(factors) if factors else 0.5

    def _infer_follow_up_action(
        self,
        original: InterviewResponse,
        follow_up: InterviewResponse
    ) -> FollowUpAction:
        """Infer what type of follow-up action was taken"""
        follow_up_question = follow_up.question_text.lower()

        # Pattern matching (simplified)
        if "example" in follow_up_question or "specific" in follow_up_question:
            return FollowUpAction.EXAMPLE
        elif "clarify" in follow_up_question or "mean by" in follow_up_question:
            return FollowUpAction.CLARIFY
        elif "compare" in follow_up_question or "versus" in follow_up_question:
            return FollowUpAction.COMPARE
        elif "more about" in follow_up_question or "elaborate" in follow_up_question:
            return FollowUpAction.DRILL_DEEPER
        else:
            return FollowUpAction.PROBE

    async def _update_patterns(self):
        """Update learned patterns based on accumulated outcomes"""
        try:
            # Group outcomes by trigger conditions
            condition_groups = defaultdict(list)

            for outcome in self.outcomes:
                # Identify trigger conditions
                conditions = self._identify_trigger_conditions(outcome)
                condition_key = "|".join(sorted(conditions))
                condition_groups[condition_key].append(outcome)

            # Analyze each group
            for condition_key, group_outcomes in condition_groups.items():
                if len(group_outcomes) >= self.min_pattern_samples:
                    success_rate = sum(1 for o in group_outcomes if o.success) / len(group_outcomes)

                    if success_rate >= self.min_success_rate:
                        # Create or update pattern
                        conditions = condition_key.split("|")
                        pattern = await self._create_pattern(conditions, group_outcomes)
                        self.patterns[pattern.pattern_id] = pattern

            logger.info(f"Updated patterns: {len(self.patterns)} active patterns")

        except Exception as e:
            logger.error(f"Error updating patterns: {e}")

    def _identify_trigger_conditions(self, outcome: FollowUpOutcome) -> List[str]:
        """Identify trigger conditions for an outcome"""
        conditions = []

        # Quality-based triggers
        if outcome.original_response_quality < 0.4:
            conditions.append("low_quality")
        elif outcome.original_response_quality < 0.6:
            conditions.append("medium_quality")

        # Sentiment-based triggers
        original_sentiment = outcome.metadata.get("original_sentiment", "")
        if "negative" in original_sentiment:
            conditions.append("negative_sentiment")
        elif "positive" in original_sentiment:
            conditions.append("positive_sentiment")

        # Action type
        conditions.append(f"action_{outcome.follow_up_action.value}")

        return conditions

    async def _create_pattern(
        self,
        conditions: List[str],
        outcomes: List[FollowUpOutcome]
    ) -> FollowUpPattern:
        """Create a pattern from outcomes"""
        # Calculate statistics
        success_count = sum(1 for o in outcomes if o.success)
        success_rate = success_count / len(outcomes)
        avg_improvement = sum(o.improvement_score for o in outcomes) / len(outcomes)

        # Identify most effective actions
        action_counts = Counter(o.follow_up_action for o in outcomes if o.success)
        effective_actions = [action for action, _ in action_counts.most_common(3)]

        # Get best examples
        best_outcomes = sorted(
            [o for o in outcomes if o.success],
            key=lambda x: x.improvement_score,
            reverse=True
        )[:3]
        best_examples = [o.follow_up_question for o in best_outcomes]

        # Generate pattern type name
        pattern_type = self._generate_pattern_type_name(conditions, effective_actions)

        pattern_id = f"pattern_{pattern_type}_{len(self.patterns)}"

        return FollowUpPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            trigger_conditions=conditions,
            effective_actions=effective_actions,
            success_rate=success_rate,
            sample_count=len(outcomes),
            avg_improvement=avg_improvement,
            best_examples=best_examples,
            learned_from_interviews=[],  # Would track in real system
            last_updated=datetime.utcnow()
        )

    def _generate_pattern_type_name(
        self,
        conditions: List[str],
        actions: List[FollowUpAction]
    ) -> str:
        """Generate descriptive name for pattern"""
        condition_str = "_".join(c for c in conditions if not c.startswith("action_"))
        action_str = "_".join(a.value for a in actions[:2])
        return f"{condition_str}_to_{action_str}"

    async def suggest_follow_up(
        self,
        original_response: str,
        response_quality: float,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest a follow-up question based on learned patterns

        Args:
            original_response: The response to follow up on
            response_quality: Quality score of the response
            context: Additional context

        Returns:
            Suggested follow-up with confidence score
        """
        try:
            # Identify current conditions
            conditions = []
            if response_quality < 0.4:
                conditions.append("low_quality")
            elif response_quality < 0.6:
                conditions.append("medium_quality")

            # Find matching patterns
            matching_patterns = [
                pattern for pattern in self.patterns.values()
                if any(c in pattern.trigger_conditions for c in conditions)
            ]

            if not matching_patterns:
                return None

            # Get best pattern
            best_pattern = max(matching_patterns, key=lambda p: p.success_rate * p.sample_count)

            # Use LLM to generate question based on pattern
            suggestion = await self._generate_from_pattern(
                best_pattern,
                original_response,
                context
            )

            return {
                "question": suggestion,
                "pattern_id": best_pattern.pattern_id,
                "confidence": best_pattern.success_rate,
                "action": best_pattern.effective_actions[0].value if best_pattern.effective_actions else "probe",
                "reasoning": f"Based on pattern with {best_pattern.success_rate:.1%} success rate"
            }

        except Exception as e:
            logger.error(f"Error suggesting follow-up: {e}")
            return None

    async def _generate_from_pattern(
        self,
        pattern: FollowUpPattern,
        response: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate follow-up question based on pattern"""
        try:
            prompt = f"""Generate a follow-up question based on this learned pattern:

**Pattern Type:** {pattern.pattern_type}
**Effective Actions:** {', '.join(a.value for a in pattern.effective_actions)}
**Success Rate:** {pattern.success_rate:.1%}

**Best Examples from Pattern:**
{chr(10).join(f"- {ex}" for ex in pattern.best_examples[:3])}

**Current Response:**
"{response}"

**Task:**
Generate a follow-up question that follows the same successful pattern.
Make it natural, conversational, and likely to elicit a better response.
"""

            result = await self.llm.generate(
                prompt=prompt,
                system_prompt="You are an expert at asking follow-up questions based on successful patterns.",
                max_tokens=100
            )

            return result.content.strip().strip('"')

        except Exception as e:
            logger.error(f"Error generating from pattern: {e}")
            return "Could you tell me more about that?"

    def get_effectiveness_report(self) -> Dict[str, Any]:
        """Get report on follow-up effectiveness"""
        report = {
            "total_outcomes_analyzed": len(self.outcomes),
            "total_patterns_learned": len(self.patterns),
            "action_effectiveness": {},
            "top_patterns": [],
            "improvement_statistics": {}
        }

        # Action effectiveness
        for action, improvements in self.action_effectiveness.items():
            if improvements:
                report["action_effectiveness"][action.value] = {
                    "avg_improvement": sum(improvements) / len(improvements),
                    "success_rate": sum(1 for i in improvements if i > 0) / len(improvements),
                    "sample_count": len(improvements)
                }

        # Top patterns
        top_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.success_rate * p.sample_count,
            reverse=True
        )[:5]

        report["top_patterns"] = [
            {
                "pattern_id": p.pattern_id,
                "pattern_type": p.pattern_type,
                "success_rate": p.success_rate,
                "sample_count": p.sample_count,
                "avg_improvement": p.avg_improvement
            }
            for p in top_patterns
        ]

        # Overall improvement statistics
        if self.outcomes:
            improvements = [o.improvement_score for o in self.outcomes]
            report["improvement_statistics"] = {
                "avg_improvement": sum(improvements) / len(improvements),
                "positive_outcomes": sum(1 for i in improvements if i > 0) / len(improvements),
                "significant_improvements": sum(1 for i in improvements if i > 0.2) / len(improvements)
            }

        return report

    def export_patterns(self) -> str:
        """Export learned patterns as JSON"""
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "pattern_count": len(self.patterns),
            "patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "pattern_type": p.pattern_type,
                    "trigger_conditions": p.trigger_conditions,
                    "effective_actions": [a.value for a in p.effective_actions],
                    "success_rate": p.success_rate,
                    "sample_count": p.sample_count,
                    "avg_improvement": p.avg_improvement,
                    "best_examples": p.best_examples,
                    "last_updated": p.last_updated.isoformat()
                }
                for p in self.patterns.values()
            ]
        }
        return json.dumps(export_data, indent=2)

    def import_patterns(self, json_data: str):
        """Import learned patterns from JSON"""
        try:
            data = json.loads(json_data)

            for pattern_data in data.get("patterns", []):
                pattern = FollowUpPattern(
                    pattern_id=pattern_data["pattern_id"],
                    pattern_type=pattern_data["pattern_type"],
                    trigger_conditions=pattern_data["trigger_conditions"],
                    effective_actions=[FollowUpAction(a) for a in pattern_data["effective_actions"]],
                    success_rate=pattern_data["success_rate"],
                    sample_count=pattern_data["sample_count"],
                    avg_improvement=pattern_data["avg_improvement"],
                    best_examples=pattern_data["best_examples"],
                    learned_from_interviews=[],
                    last_updated=datetime.fromisoformat(pattern_data["last_updated"])
                )
                self.patterns[pattern.pattern_id] = pattern

            logger.info(f"Imported {len(data.get('patterns', []))} patterns")

        except Exception as e:
            logger.error(f"Error importing patterns: {e}")
