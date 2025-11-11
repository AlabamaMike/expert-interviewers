"""
Insight Extractor - Extracts and synthesizes insights from interviews
"""

from typing import List, Dict, Any, Optional
import logging
from ..models.analytics import (
    InsightExtraction, Insight, Theme, SentimentTrajectory,
    SentimentDataPoint, CrossInterviewPattern
)
from ..models.interview import Interview, InterviewResponse
from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class InsightExtractor:
    """Extracts insights from interview data using LLM"""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize insight extractor

        Args:
            llm_provider: LLM provider for analysis
        """
        self.llm = llm_provider
        logger.info("Initialized InsightExtractor")

    async def extract_interview_insights(
        self,
        interview: Interview,
        research_objective: str
    ) -> InsightExtraction:
        """
        Extract insights from a single interview

        Args:
            interview: Completed interview
            research_objective: Research objective for context

        Returns:
            InsightExtraction with comprehensive analysis
        """
        try:
            # Build comprehensive prompt
            prompt = self._build_extraction_prompt(interview, research_objective)

            # Define output schema
            schema = {
                "type": "object",
                "properties": {
                    "executive_summary": {"type": "string"},
                    "key_findings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "evidence": {"type": "array", "items": {"type": "string"}},
                                "confidence": {"type": "number"},
                                "impact_score": {"type": "number"}
                            }
                        }
                    },
                    "themes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "keywords": {"type": "array", "items": {"type": "string"}},
                                "frequency": {"type": "integer"}
                            }
                        }
                    },
                    "notable_quotes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "quote": {"type": "string"},
                                "context": {"type": "string"},
                                "significance": {"type": "string"}
                            }
                        }
                    },
                    "contradictions": {"type": "array", "items": {"type": "string"}},
                    "research_objective_alignment": {"type": "number"},
                    "data_quality_score": {"type": "number"},
                    "follow_up_recommendations": {"type": "array", "items": {"type": "string"}},
                    "suggested_next_questions": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["executive_summary", "key_findings", "themes"]
            }

            # Get structured insights from LLM
            result = await self.llm.generate_structured(
                prompt=prompt,
                output_schema=schema,
                system_prompt="You are an expert research analyst specializing in extracting actionable insights from qualitative interviews."
            )

            # Build InsightExtraction object
            extraction = InsightExtraction(
                interview_id=interview.interview_id,
                interview_ids=[interview.interview_id],
                executive_summary=result["executive_summary"],
                key_findings=[
                    Insight(
                        type=f["type"],
                        title=f["title"],
                        description=f["description"],
                        evidence=f.get("evidence", []),
                        confidence=f.get("confidence", 0.5),
                        impact_score=f.get("impact_score", 0.5),
                        source_interviews=[interview.interview_id]
                    )
                    for f in result.get("key_findings", [])
                ],
                themes=[
                    Theme(
                        name=t["name"],
                        description=t["description"],
                        keywords=t.get("keywords", []),
                        frequency=t.get("frequency", 1)
                    )
                    for t in result.get("themes", [])
                ],
                notable_quotes=result.get("notable_quotes", []),
                contradictions=result.get("contradictions", []),
                research_objective_alignment=result.get("research_objective_alignment", 0.5),
                data_quality_score=result.get("data_quality_score", 0.7),
                follow_up_recommendations=result.get("follow_up_recommendations", []),
                suggested_next_questions=result.get("suggested_next_questions", []),
                model_used=self.llm.model if hasattr(self.llm, 'model') else "unknown"
            )

            logger.info(f"Extracted {len(extraction.key_findings)} insights from interview {interview.interview_id}")
            return extraction

        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            # Return minimal extraction on error
            return InsightExtraction(
                interview_id=interview.interview_id,
                interview_ids=[interview.interview_id],
                executive_summary="Error extracting insights",
                key_findings=[],
                themes=[],
                research_objective_alignment=0.0,
                data_quality_score=0.0
            )

    def _build_extraction_prompt(
        self,
        interview: Interview,
        research_objective: str
    ) -> str:
        """Build comprehensive extraction prompt"""
        # Collect all Q&A pairs
        qa_pairs = []
        for i, response in enumerate(interview.responses, 1):
            qa_pairs.append(f"""
Q{i}: {response.question_text}
A{i}: {response.response_text}
[Sentiment: {response.sentiment.value if response.sentiment else 'unknown'}]
""")

        prompt = f"""Analyze this research interview and extract key insights:

**Research Objective:**
{research_objective}

**Interview Metadata:**
- Duration: {interview.duration_seconds} seconds
- Completion: {interview.quality_metrics.completion_percentage * 100:.1f}%
- Engagement Score: {interview.engagement_metrics.overall_engagement:.2f}

**Interview Content:**
{chr(10).join(qa_pairs)}

**Analysis Task:**

1. **Executive Summary**: Provide a concise summary (3-5 bullet points) of the most important findings from this interview.

2. **Key Findings**: Identify the most significant insights. For each:
   - Type: (pain_point, opportunity, pattern, contradiction, hypothesis_validation, unexpected)
   - Title: Brief descriptive title
   - Description: Detailed explanation
   - Evidence: Supporting quotes from the interview
   - Confidence: How confident you are in this finding (0.0-1.0)
   - Impact Score: Estimated importance/actionability (0.0-1.0)

3. **Themes**: Identify recurring themes throughout the interview:
   - Name of theme
   - Description
   - Keywords associated with it
   - Frequency (rough count)

4. **Notable Quotes**: Extract the most impactful or revealing quotes with:
   - The quote itself
   - Context (what was being discussed)
   - Significance (why this quote matters)

5. **Contradictions**: Note any internal contradictions or inconsistencies in the responses.

6. **Research Objective Alignment**: Rate how well this interview addressed the research objective (0.0-1.0)

7. **Data Quality Score**: Assess the overall quality and reliability of the data collected (0.0-1.0)

8. **Follow-up Recommendations**: Suggest areas that need further investigation.

9. **Suggested Next Questions**: Propose specific questions for future interviews based on what you learned.

Focus on actionable insights that provide real value for the research objective.
"""
        return prompt

    async def synthesize_cross_interview_insights(
        self,
        interviews: List[Interview],
        research_objective: str
    ) -> InsightExtraction:
        """
        Synthesize insights across multiple interviews

        Args:
            interviews: List of completed interviews
            research_objective: Research objective

        Returns:
            InsightExtraction with cross-interview analysis
        """
        try:
            # Build cross-interview prompt
            prompt = self._build_cross_interview_prompt(interviews, research_objective)

            # Generate synthesis
            result = await self.llm.generate(
                prompt=prompt,
                system_prompt="You are an expert at synthesizing insights from multiple interviews to identify patterns and trends.",
                temperature=0.5,
                max_tokens=3000
            )

            # Create comprehensive extraction
            extraction = InsightExtraction(
                interview_ids=[i.interview_id for i in interviews],
                executive_summary=result.content[:500],  # First part of response
                key_findings=[],  # Would need structured parsing
                themes=[],
                research_objective_alignment=0.8,
                data_quality_score=0.8,
                model_used=self.llm.model if hasattr(self.llm, 'model') else "unknown"
            )

            logger.info(f"Synthesized insights from {len(interviews)} interviews")
            return extraction

        except Exception as e:
            logger.error(f"Error synthesizing cross-interview insights: {e}")
            return InsightExtraction(
                interview_ids=[i.interview_id for i in interviews],
                executive_summary="Error synthesizing insights",
                key_findings=[],
                themes=[],
                research_objective_alignment=0.0,
                data_quality_score=0.0
            )

    def _build_cross_interview_prompt(
        self,
        interviews: List[Interview],
        research_objective: str
    ) -> str:
        """Build prompt for cross-interview synthesis"""
        # Summarize each interview
        interview_summaries = []
        for i, interview in enumerate(interviews, 1):
            response_count = len(interview.responses)
            avg_sentiment = sum(
                1 if r.sentiment and 'positive' in r.sentiment.value else
                -1 if r.sentiment and 'negative' in r.sentiment.value else 0
                for r in interview.responses
            ) / max(response_count, 1)

            interview_summaries.append(f"""
Interview {i} (ID: {interview.interview_id}):
- Responses: {response_count}
- Engagement: {interview.engagement_metrics.overall_engagement:.2f}
- Avg Sentiment: {"Positive" if avg_sentiment > 0.3 else "Negative" if avg_sentiment < -0.3 else "Neutral"}
- Key Themes: {', '.join(set([theme for r in interview.responses for theme in r.themes[:2]]))}
""")

        prompt = f"""Synthesize insights across multiple interviews:

**Research Objective:**
{research_objective}

**Interview Overview:**
Total Interviews: {len(interviews)}
{chr(10).join(interview_summaries)}

**Synthesis Task:**

1. **Common Patterns**: What themes or patterns appear across multiple interviews?

2. **Segment Differences**: Are there notable differences between respondent groups?

3. **Universal Insights**: What insights are consistent across all/most interviews?

4. **Outliers**: Which interviews or responses stand out as unusual?

5. **Contradictions**: Are there contradictions between different respondents?

6. **Confidence Levels**: Which findings have strong support vs. weak support?

7. **Actionable Recommendations**: What are the top 3-5 actionable insights from this research?

8. **Research Gaps**: What questions remain unanswered?

Provide a comprehensive synthesis that would be valuable for decision-making.
"""
        return prompt

    def calculate_sentiment_trajectory(
        self,
        interview: Interview
    ) -> SentimentTrajectory:
        """
        Calculate sentiment changes throughout interview

        Args:
            interview: Completed interview

        Returns:
            SentimentTrajectory showing sentiment evolution
        """
        sentiment_map = {
            "very_positive": 1.0,
            "positive": 0.5,
            "neutral": 0.0,
            "negative": -0.5,
            "very_negative": -1.0
        }

        data_points = []
        for response in interview.responses:
            if response.sentiment and response.answered_at:
                score = sentiment_map.get(response.sentiment.value, 0.0)
                data_points.append(SentimentDataPoint(
                    timestamp=response.answered_at,
                    sentiment_score=score,
                    section=response.section_name
                ))

        # Calculate overall sentiment
        overall = sum(dp.sentiment_score for dp in data_points) / max(len(data_points), 1)

        # Calculate variance
        if len(data_points) > 1:
            mean = overall
            variance = sum((dp.sentiment_score - mean) ** 2 for dp in data_points) / len(data_points)
        else:
            variance = 0.0

        # Identify peaks
        positive_peaks = sorted(
            [dp for dp in data_points if dp.sentiment_score > 0.5],
            key=lambda x: x.sentiment_score,
            reverse=True
        )[:3]

        negative_peaks = sorted(
            [dp for dp in data_points if dp.sentiment_score < -0.5],
            key=lambda x: x.sentiment_score
        )[:3]

        return SentimentTrajectory(
            interview_id=interview.interview_id,
            data_points=data_points,
            overall_sentiment=overall,
            sentiment_variance=variance,
            positive_peaks=positive_peaks,
            negative_peaks=negative_peaks
        )
