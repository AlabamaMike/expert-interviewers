"""
Pytest configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.main import app
from src.data.database import Base
from src.data.connection import get_db
from src.intelligence.llm_provider import MockLLMProvider
from src.voice_engine.stt import MockSTT
from src.voice_engine.tts import MockTTS


# Test database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client(test_db):
    """Create test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm():
    """Mock LLM provider for testing"""
    return MockLLMProvider()


@pytest.fixture
def mock_stt():
    """Mock STT provider for testing"""
    return MockSTT()


@pytest.fixture
def mock_tts():
    """Mock TTS provider for testing"""
    return MockTTS()
