"""Tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SWE-Bench Green Agent"
    assert data["status"] == "running"
    assert "endpoints" in data


def test_card():
    """Test /card endpoint."""
    response = client.get("/card")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SWE-Bench Green Agent"
    assert data["protocol"] == "A2A"
    assert data["model_type"] == "green"
    assert "swe-bench" in data["capabilities"]


def test_reset():
    """Test /reset endpoint."""
    response = client.post("/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_task_numpy_good():
    """Test /task endpoint with numpy good patch."""
    response = client.post(
        "/task",
        json={"task_id": "numpy-1234", "patch_choice": "good"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "numpy-1234"
    assert data["verdict"] == "PASS"
    assert data["tests_passed"] == 12
    assert data["total_tests"] == 12
    assert data["failure_type"] is None


def test_task_numpy_bad():
    """Test /task endpoint with numpy bad patch."""
    response = client.post(
        "/task",
        json={"task_id": "numpy-1234", "patch_choice": "bad"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "numpy-1234"
    assert data["verdict"] == "FAIL"
    assert data["tests_passed"] < data["total_tests"]
    assert data["failure_type"] == "test_failure"


def test_task_django_good():
    """Test /task endpoint with django good patch."""
    response = client.post(
        "/task",
        json={"task_id": "django-5678", "patch_choice": "good"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "django-5678"
    assert data["verdict"] == "PASS"
    assert data["tests_passed"] == 8
    assert data["total_tests"] == 8


def test_task_django_bad():
    """Test /task endpoint with django bad patch (apply error)."""
    response = client.post(
        "/task",
        json={"task_id": "django-5678", "patch_choice": "bad"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "django-5678"
    assert data["verdict"] == "FAIL"
    assert data["tests_passed"] == 0
    assert data["failure_type"] == "apply_error"


def test_health():
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_logs_endpoint():
    """Test /logs endpoint."""
    # First run a task to generate a log
    client.post(
        "/task",
        json={"task_id": "numpy-1234", "patch_choice": "good"}
    )

    # Then retrieve the log
    response = client.get("/logs/numpy-1234-good.txt")
    assert response.status_code == 200
    assert "SWE-Bench Green Agent Evaluation Log" in response.text


def test_logs_not_found():
    """Test /logs endpoint with non-existent log."""
    response = client.get("/logs/nonexistent.txt")
    assert response.status_code == 404
