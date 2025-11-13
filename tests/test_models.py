"""
Tests for data models
"""

import pytest
from src.models.call_guide import CallGuide, Question, Section, QuestionType
from src.models.interview import Interview, InterviewResponse, InterviewStatus
from src.models.analytics import Insight, Theme


def test_call_guide_creation():
    """Test creating a call guide"""
    guide = CallGuide(
        name="Test Guide",
        research_objective="Test objective",
        sections=[]
    )

    assert guide.name == "Test Guide"
    assert guide.research_objective == "Test objective"
    assert len(guide.sections) == 0
    assert guide.guide_id is not None


def test_question_creation():
    """Test creating a question"""
    question = Question(
        text="What do you think?",
        type=QuestionType.OPEN,
        required=True
    )

    assert question.text == "What do you think?"
    assert question.type == QuestionType.OPEN
    assert question.required is True
    assert question.max_follow_ups == 3


def test_section_with_questions():
    """Test creating a section with questions"""
    questions = [
        Question(text="Question 1", type=QuestionType.OPEN, required=True),
        Question(text="Question 2", type=QuestionType.SCALE, required=False)
    ]

    section = Section(
        section_name="Test Section",
        objective="Test objective",
        questions=questions
    )

    assert section.section_name == "Test Section"
    assert len(section.questions) == 2
    assert section.questions[0].text == "Question 1"


def test_interview_creation():
    """Test creating an interview"""
    interview = Interview(
        call_guide_id="test-guide-id",
        respondent_phone="+1234567890",
        respondent_name="Test User"
    )

    assert interview.status == InterviewStatus.SCHEDULED
    assert interview.respondent_phone == "+1234567890"
    assert interview.respondent_name == "Test User"
    assert len(interview.responses) == 0


def test_interview_response():
    """Test creating an interview response"""
    response = InterviewResponse(
        interview_id="test-interview",
        question_id="q1",
        section_name="Test Section",
        question_text="What do you think?",
        response_text="I think it's great!"
    )

    assert response.question_text == "What do you think?"
    assert response.response_text == "I think it's great!"
    assert response.is_follow_up is False
    assert response.follow_up_count == 0


def test_insight_creation():
    """Test creating an insight"""
    insight = Insight(
        type="pain_point",
        title="Major Issue",
        description="Users struggle with X",
        evidence=["Quote 1", "Quote 2"],
        confidence=0.85,
        impact_score=0.9
    )

    assert insight.type == "pain_point"
    assert insight.title == "Major Issue"
    assert len(insight.evidence) == 2
    assert insight.confidence == 0.85


def test_theme_creation():
    """Test creating a theme"""
    theme = Theme(
        name="User Experience",
        description="Issues related to UX",
        keywords=["usability", "interface", "navigation"],
        frequency=15
    )

    assert theme.name == "User Experience"
    assert len(theme.keywords) == 3
    assert theme.frequency == 15
