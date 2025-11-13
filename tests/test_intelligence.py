"""
Tests for intelligence layer
"""

import pytest
from src.intelligence.response_analyzer import ResponseAnalyzer
from src.intelligence.follow_up_generator import FollowUpGenerator
from src.models.call_guide import Question, QuestionType


@pytest.mark.asyncio
async def test_response_analyzer(mock_llm):
    """Test response analysis"""
    analyzer = ResponseAnalyzer(mock_llm)

    analysis = await analyzer.analyze_response(
        question="What do you think about the product?",
        response="I really love it! It's amazing and solves all my problems.",
        context={}
    )

    assert analysis is not None
    assert analysis.sentiment is not None
    assert isinstance(analysis.key_phrases, list)
    assert isinstance(analysis.themes, list)
    assert 0 <= analysis.information_density <= 1


@pytest.mark.asyncio
async def test_follow_up_generator(mock_llm):
    """Test follow-up question generation"""
    generator = FollowUpGenerator(mock_llm)

    question = Question(
        text="What challenges do you face?",
        type=QuestionType.OPEN,
        required=True
    )

    # Mock analysis result
    class MockAnalysis:
        def __init__(self):
            self.sentiment = "positive"
            self.information_density = 0.3  # Low, should trigger follow-up
            self.requires_clarification = False
            self.signals = ["vague"]
            self.contradictions = []
            self.themes = []

    analysis = MockAnalysis()

    follow_ups = await generator.generate_follow_ups(
        original_question=question,
        response="It's complicated.",
        analysis=analysis,
        max_follow_ups=2
    )

    # Should generate follow-ups for vague response
    assert isinstance(follow_ups, list)
