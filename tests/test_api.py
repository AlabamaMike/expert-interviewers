"""
Tests for API endpoints
"""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(test_client):
    """Test root endpoint"""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Expert Interviewers"
    assert "version" in data


def test_health_check(test_client):
    """Test health check endpoint"""
    response = test_client.get("/api/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_call_guide(test_client):
    """Test creating a call guide"""
    call_guide_data = {
        "name": "Test Guide",
        "research_objective": "Test objective",
        "sections": []
    }

    response = test_client.post("/api/call-guides/", json=call_guide_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Guide"
    assert "guide_id" in data


def test_get_call_guide(test_client):
    """Test getting a call guide"""
    # Create a guide first
    call_guide_data = {
        "name": "Test Guide",
        "research_objective": "Test objective",
        "sections": []
    }
    create_response = test_client.post("/api/call-guides/", json=call_guide_data)
    guide_id = create_response.json()["guide_id"]

    # Get the guide
    response = test_client.get(f"/api/call-guides/{guide_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["guide_id"] == guide_id


def test_schedule_interview(test_client):
    """Test scheduling an interview"""
    # Create a call guide first
    call_guide_data = {
        "name": "Test Guide",
        "research_objective": "Test objective",
        "sections": []
    }
    guide_response = test_client.post("/api/call-guides/", json=call_guide_data)
    guide_id = guide_response.json()["guide_id"]

    # Schedule interview
    interview_data = {
        "call_guide_id": guide_id,
        "respondent_phone": "+1234567890",
        "respondent_name": "Test User"
    }

    response = test_client.post("/api/interviews/schedule", json=interview_data)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "scheduled"
    assert data["respondent_phone"] == "+1234567890"


def test_dashboard_overview(test_client):
    """Test dashboard overview endpoint"""
    response = test_client.get("/api/dashboard/overview?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert "interviews" in data
    assert "performance" in data
    assert "quality" in data


def test_call_guide_performance(test_client):
    """Test call guide performance endpoint"""
    response = test_client.get("/api/dashboard/call-guides/performance?hours=168")
    assert response.status_code == 200
    data = response.json()
    assert "call_guides" in data
    assert isinstance(data["call_guides"], list)
