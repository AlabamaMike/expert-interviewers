"""
Response Analyzer - Analyzes respondent answers using LLM
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
from ..models.interview import ResponseSentiment, InterviewResponse
from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class ResponseAnalysis:
    """Analysis of a single response"""
    sentiment: ResponseSentiment
    confidence: float
    key_phrases: List[str]
    themes: List[str]
    information_density: float
    requires_clarification: bool
    signals: List[str]  # e.g., "enthusiasm", "hesitation", "confusion"
    contradictions: List[str]
    notable_content: str  # Brief summary of what makes this response valuable


class ResponseAnalyzer:
    """Analyzes interview responses using LLM"""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize response analyzer

        Args:
            llm_provider: LLM provider for analysis
        """
        self.llm = llm_provider
        logger.info("Initialized ResponseAnalyzer")

    async def analyze_response(
        self,
        question: str,
        response: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ResponseAnalysis:
        """
        Analyze a single response

        Args:
            question: The question that was asked
            response: The respondent's answer
            context: Optional context (previous responses, respondent profile, etc.)

        Returns:
            ResponseAnalysis with detailed analysis
        """
        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(question, response, context)

            # Define output schema
            schema = {
                "type": "object",
                "properties": {
                    "sentiment": {
                        "type": "string",
                        "enum": ["very_positive", "positive", "neutral", "negative", "very_negative"]
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "key_phrases": {"type": "array", "items": {"type": "string"}},
                    "themes": {"type": "array", "items": {"type": "string"}},
                    "information_density": {"type": "number", "minimum": 0, "maximum": 1},
                    "requires_clarification": {"type": "boolean"},
                    "signals": {"type": "array", "items": {"type": "string"}},
                    "contradictions": {"type": "array", "items": {"type": "string"}},
                    "notable_content": {"type": "string"}
                },
                "required": ["sentiment", "confidence", "information_density"]
            }

            # Get structured analysis from LLM
            result = await self.llm.generate_structured(
                prompt=prompt,
                output_schema=schema,
                system_prompt="You are an expert research analyst specializing in qualitative interview analysis."
            )

            # Convert to ResponseAnalysis
            return ResponseAnalysis(
                sentiment=ResponseSentiment(result["sentiment"]),
                confidence=result["confidence"],
                key_phrases=result.get("key_phrases", []),
                themes=result.get("themes", []),
                information_density=result["information_density"],
                requires_clarification=result.get("requires_clarification", False),
                signals=result.get("signals", []),
                contradictions=result.get("contradictions", []),
                notable_content=result.get("notable_content", "")
            )

        except Exception as e:
            logger.error(f"Error analyzing response: {e}")
            # Return default analysis on error
            return ResponseAnalysis(
                sentiment=ResponseSentiment.NEUTRAL,
                confidence=0.0,
                key_phrases=[],
                themes=[],
                information_density=0.5,
                requires_clarification=False,
                signals=[],
                contradictions=[],
                notable_content="Analysis failed"
            )

    def _build_analysis_prompt(
        self,
        question: str,
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for response analysis"""
        prompt = f"""Analyze this interview response in detail:

**Question Asked:**
{question}

**Respondent's Answer:**
{response}
"""

        if context:
            if context.get("previous_responses"):
                prompt += f"\n**Previous Context:**\n{context['previous_responses']}\n"

            if context.get("research_objective"):
                prompt += f"\n**Research Objective:**\n{context['research_objective']}\n"

        prompt += """
**Analysis Task:**
Provide a detailed analysis including:

1. **Sentiment**: Overall emotional tone (very_positive, positive, neutral, negative, very_negative)
2. **Confidence**: Your confidence in this analysis (0.0 to 1.0)
3. **Key Phrases**: Important phrases or quotes from the response
4. **Themes**: Main themes or topics addressed
5. **Information Density**: How much valuable insight this response contains (0.0 to 1.0)
   - 0.0-0.3: Vague, surface-level, or off-topic
   - 0.4-0.6: Moderate detail and relevance
   - 0.7-1.0: Rich, detailed, highly relevant insights
6. **Requires Clarification**: Does this response need follow-up questions?
7. **Signals**: Detected signals (enthusiasm, hesitation, confusion, agreement, disagreement, emotional)
8. **Contradictions**: Any contradictions with prior responses or internal inconsistencies
9. **Notable Content**: Brief summary of what makes this response valuable (or not)

Focus on extracting maximum research value from this response.
"""
        return prompt

    async def compare_responses(
        self,
        responses: List[InterviewResponse],
        research_objective: str
    ) -> Dict[str, Any]:
        """
        Compare multiple responses to identify patterns and contradictions

        Args:
            responses: List of responses to compare
            research_objective: The research objective for context

        Returns:
            Dict with patterns, contradictions, and insights
        """
        try:
            # Build comparison prompt
            response_texts = [
                f"Q: {r.question_text}\nA: {r.response_text}"
                for r in responses
            ]

            prompt = f"""Compare these interview responses and identify patterns:

**Research Objective:**
{research_objective}

**Responses:**
{chr(10).join([f"{i+1}. {r}" for i, r in enumerate(response_texts)])}

**Analysis Task:**
Identify:
1. Common themes across responses
2. Contradictions or inconsistencies
3. Evolution of opinions/attitudes
4. Areas needing deeper exploration
5. Overall coherence of the narrative
"""

            result = await self.llm.generate(
                prompt=prompt,
                system_prompt="You are an expert at identifying patterns in qualitative research.",
                temperature=0.5
            )

            return {
                "analysis": result.content,
                "response_count": len(responses),
                "research_objective": research_objective
            }

        except Exception as e:
            logger.error(f"Error comparing responses: {e}")
            return {"error": str(e)}
