import pytest
import os
import sys
import importlib
from unittest.mock import patch, MagicMock
from app.utils.db import get_sql_database_tool
from app.utils.llm import get_llm
from app.utils.vector_store import get_vector_store
from app.utils.monitoring import record_agent_invocation, record_fallback_event, _write_time_series

# --- Tests for app/utils/db.py ---

@patch("os.path.exists")
def test_get_sql_database_tool_file_not_found(mock_exists):
    mock_exists.return_value = False
    with pytest.raises(FileNotFoundError):
        get_sql_database_tool()

@patch("os.path.exists")
@patch("langchain_community.utilities.SQLDatabase.from_uri")
def test_get_sql_database_tool_success(mock_from_uri, mock_exists):
    mock_exists.return_value = True
    mock_db = MagicMock()
    mock_from_uri.return_value = mock_db
    assert get_sql_database_tool() == mock_db

@patch("os.path.exists")
@patch("langchain_community.utilities.SQLDatabase.from_uri")
def test_get_sql_database_tool_exception(mock_from_uri, mock_exists):
    mock_exists.return_value = True
    mock_from_uri.side_effect = Exception("DB Connection Error")
    with pytest.raises(Exception) as excinfo:
        get_sql_database_tool()
    assert "DB Connection Error" in str(excinfo.value)


# --- Tests for app/utils/llm.py ---

@patch("app.utils.llm.ChatGoogleGenerativeAI")
@patch.dict(os.environ, {"GCP_PROJECT_ID": "gcp-project-123", "GCP_LOCATION": "us-central1"})
def test_get_llm_production(mock_chat_gen_ai):
    mock_llm_instance = MagicMock()
    mock_chat_gen_ai.return_value = mock_llm_instance
    
    with patch("app.utils.llm.PROJECT_ID", "gcp-project-123"):
        llm = get_llm()
        assert llm == mock_llm_instance
        mock_chat_gen_ai.assert_called_once_with(
            model="gemini-2.5-flash",
            project="gcp-project-123",
            location="us-central1",
            vertexai=True,
            temperature=0.2
        )

@patch("app.utils.llm.ChatGoogleGenerativeAI")
def test_get_llm_local_dev(mock_chat_gen_ai):
    mock_llm_instance = MagicMock()
    mock_chat_gen_ai.return_value = mock_llm_instance
    
    with patch("app.utils.llm.PROJECT_ID", None):
        llm = get_llm()
        assert llm == mock_llm_instance
        mock_chat_gen_ai.assert_called_once_with(
            model="gemini-2.5-flash",
            temperature=0.2
        )

@patch("app.utils.llm.ChatGoogleGenerativeAI")
def test_get_llm_exception(mock_chat_gen_ai):
    mock_chat_gen_ai.side_effect = Exception("LLM Load Failure")
    with patch("app.utils.llm.PROJECT_ID", None), pytest.raises(Exception):
        get_llm()


# --- Tests for app/utils/vector_store.py ---

@patch("os.path.exists")
def test_get_vector_store_not_found(mock_exists):
    mock_exists.return_value = False
    with pytest.raises(FileNotFoundError):
        get_vector_store()

@patch("os.path.exists")
@patch("app.utils.vector_store.GoogleGenerativeAIEmbeddings")
@patch("app.utils.vector_store.Chroma")
def test_get_vector_store_success(mock_chroma, mock_embeddings, mock_exists):
    mock_exists.return_value = True
    mock_embed_instance = MagicMock()
    mock_embeddings.return_value = mock_embed_instance
    mock_chroma_instance = MagicMock()
    mock_chroma.return_value = mock_chroma_instance
    
    with patch("app.utils.vector_store.PROJECT_ID", "gcp-proj"):
        res = get_vector_store()
        assert res == mock_chroma_instance
        mock_embeddings.assert_called_once_with(
            model="gemini-embedding-001",
            project="gcp-proj",
            location="us-central1"
        )

@patch("os.path.exists")
@patch("app.utils.vector_store.GoogleGenerativeAIEmbeddings")
@patch("app.utils.vector_store.Chroma")
def test_get_vector_store_local_models_prefix(mock_chroma, mock_embeddings, mock_exists):
    mock_exists.return_value = True
    mock_embed_instance = MagicMock()
    mock_embeddings.return_value = mock_embed_instance
    mock_chroma_instance = MagicMock()
    mock_chroma.return_value = mock_chroma_instance
    
    with patch("app.utils.vector_store.PROJECT_ID", None):
        res = get_vector_store()
        assert res == mock_chroma_instance
        mock_embeddings.assert_called_once_with(
            model="models/gemini-embedding-001",
            project=None,
            location="us-central1"
        )

@patch("os.path.exists")
@patch("app.utils.vector_store.GoogleGenerativeAIEmbeddings")
def test_get_vector_store_exception(mock_embeddings, mock_exists):
    mock_exists.return_value = True
    mock_embeddings.side_effect = Exception("Embedding Init Error")
    with pytest.raises(Exception):
        get_vector_store()


# --- Tests for app/utils/monitoring.py ---

@patch("app.utils.monitoring.client")
def test_write_time_series_no_client(mock_client):
    with patch("app.utils.monitoring.client", None):
        res = _write_time_series("some_metric", {})
        assert res is None

@patch("app.utils.monitoring.client")
def test_write_time_series_success(mock_client):
    mock_client_instance = MagicMock()
    with patch("app.utils.monitoring.client", mock_client_instance), patch("app.utils.monitoring.PROJECT_ID", "my-project"), patch("app.utils.monitoring.project_name", "projects/my-project"):
        _write_time_series("custom.googleapis.com/test", {"label": "value"})
        mock_client_instance.create_time_series.assert_called_once()

@patch("app.utils.monitoring._write_time_series")
def test_record_agent_invocation(mock_write):
    record_agent_invocation("test_agent")
    mock_write.assert_called_once_with(
        metric_type="custom.googleapis.com/agent/invocation_count",
        metric_labels={"agent_name": "test_agent"}
    )

@patch("app.utils.monitoring._write_time_series")
def test_record_fallback_event(mock_write):
    record_fallback_event("test_agent", "timeout")
    mock_write.assert_called_once_with(
        metric_type="custom.googleapis.com/agent/fallback_count",
        metric_labels={"agent_name": "test_agent", "reason": "timeout"}
    )


def test_monitoring_client_init_exception():
    """
    Test that app.utils.monitoring imports/loads cleanly and handles client initialization exceptions gracefully.
    """
    with patch("google.cloud.monitoring_v3.MetricServiceClient", side_effect=Exception("Client init error")):
        import app.utils.monitoring
        importlib.reload(app.utils.monitoring)
        assert app.utils.monitoring.client is None


@patch("app.utils.monitoring.client")
def test_write_time_series_exception(mock_client):
    """
    Test that if client.create_time_series raises an exception, the failure is caught and logged.
    """
    mock_client_instance = MagicMock()
    mock_client_instance.create_time_series.side_effect = Exception("Write API quota exceeded")
    with patch("app.utils.monitoring.client", mock_client_instance), patch("app.utils.monitoring.PROJECT_ID", "my-project"), patch("app.utils.monitoring.project_name", "projects/my-project"):
        # This shouldn't raise any exception up to the caller
        _write_time_series("custom.googleapis.com/test", {"label": "value"})
        mock_client_instance.create_time_series.assert_called_once()