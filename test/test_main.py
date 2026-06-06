import pytest
import os
import importlib
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

# Set dummy env vars before importing app.main to avoid logging setup or initialization errors
with patch.dict(os.environ, {"GCP_PROJECT_ID": "dummy-project", "API_KEY": "secret-key"}):
    from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@patch("app.main.run_supervisor")
@patch.dict(os.environ, {"API_KEY": ""})
def test_process_query_no_api_key_set(mock_run):
    mock_run.return_value = {"final_response": "Hello world", "clarification_needed": False}
    response = client.post("/api/v1/query", json={"query": "Test query", "user_id": "user1"})
    assert response.status_code == 200
    assert response.json() == {"response": "Hello world", "status": "success"}

@patch("app.main.run_supervisor")
@patch.dict(os.environ, {"API_KEY": "valid-key"})
def test_process_query_valid_api_key(mock_run):
    mock_run.return_value = {"final_response": "Hello world", "clarification_needed": False}
    response = client.post(
        "/api/v1/query",
        json={"query": "Test query", "user_id": "user1"},
        headers={"X-API-Key": "valid-key"}
    )
    assert response.status_code == 200
    assert response.json() == {"response": "Hello world", "status": "success"}

@patch.dict(os.environ, {"API_KEY": "valid-key"})
def test_process_query_invalid_api_key():
    response = client.post(
        "/api/v1/query",
        json={"query": "Test query", "user_id": "user1"},
        headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 403
    assert "Could not validate credentials" in response.json()["detail"]

@patch("app.main.run_supervisor")
@patch.dict(os.environ, {"API_KEY": "valid-key"})
def test_process_query_clarification_needed(mock_run):
    mock_run.return_value = {"final_response": "Clarify please", "clarification_needed": True}
    response = client.post(
        "/api/v1/query",
        json={"query": "Test query", "user_id": "user1"},
        headers={"X-API-Key": "valid-key"}
    )
    assert response.status_code == 200
    assert response.json() == {"response": "Clarify please", "status": "clarification_needed"}

@patch("app.main.run_supervisor")
@patch.dict(os.environ, {"API_KEY": "valid-key"})
def test_process_query_exception(mock_run):
    mock_run.side_effect = Exception("Graph error")
    response = client.post(
        "/api/v1/query",
        json={"query": "Test query", "user_id": "user1"},
        headers={"X-API-Key": "valid-key"}
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


def test_main_import_without_gcp_logging():
    """
    Test that app.main imports cleanly and logs a warning if google.cloud.logging raises an Exception.
    """
    with patch.dict(sys.modules, {"google.cloud.logging": None}):
        import app.main
        importlib.reload(app.main)


@patch("app.main.find_dotenv")
def test_main_import_env_fallback(mock_find_dotenv):
    """
    Test that app.main gracefully falls back to the current directory if app/.env is not found.
    """
    mock_find_dotenv.side_effect = [None, "dummy_env"]
    import app.main
    importlib.reload(app.main)