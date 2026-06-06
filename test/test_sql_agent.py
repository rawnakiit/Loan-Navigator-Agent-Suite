import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from app.agents.sql_agent import sql_agent_node
from app.state import AgentState

@patch("app.agents.sql_agent.get_llm")
@patch("app.agents.sql_agent.get_sql_database_tool")
@patch("app.agents.sql_agent.record_agent_invocation")
def test_sql_agent_node_success(mock_record, mock_get_db, mock_get_llm):
    """
    Test that the SQL Analyst Agent correctly receives an LLM-generated SQL string,
    runs it on the database tool, and forwards the data to the synthesizer.
    """
    # Arrange
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.invoke.return_value = AIMessage(content="SELECT loan_amount FROM loan_data WHERE loan_id = 2003;")
    mock_llm.return_value = AIMessage(content="SELECT loan_amount FROM loan_data WHERE loan_id = 2003;")

    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.run.return_value = "[(75000.0,)]"

    state: AgentState = {
        "messages": [HumanMessage(content="Show me my loan amount for LN2003")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "sql_agent",
        "policy_retries": 0,
        "clarification_needed": False,
    }

    # Act
    result = sql_agent_node(state)

    # Assert
    assert result["current_agent"] == "synthesize_response"
    assert "Database Data Retrieved: [(75000.0,)]" in result["sql_result"]
    mock_db.run.assert_called_once_with("SELECT loan_amount FROM loan_data WHERE loan_id = 2003;")


@patch("app.agents.sql_agent.get_llm")
@patch("app.agents.sql_agent.get_sql_database_tool")
@patch("app.agents.sql_agent.record_agent_invocation")
@patch("app.agents.sql_agent.record_fallback_event")
def test_sql_agent_node_empty_db_result_fallback(mock_record_fallback, mock_record, mock_get_db, mock_get_llm):
    """
    Test that if the database execution yields no results, the SQL Analyst Agent
    properly registers a fallback event and formats a user-friendly error note.
    """
    # Arrange
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.invoke.return_value = AIMessage(content="SELECT loan_amount FROM loan_data WHERE customer_id = 9999;")
    mock_llm.return_value = AIMessage(content="SELECT loan_amount FROM loan_data WHERE customer_id = 9999;")

    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    # Empty list string format from SQLite
    mock_db.run.return_value = "[]"

    state: AgentState = {
        "messages": [HumanMessage(content="Query an unknown customer 9999")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "sql_agent",
        "policy_retries": 0,
        "clarification_needed": False,
    }

    # Act
    result = sql_agent_node(state)

    # Assert
    assert result["current_agent"] == "synthesize_response"
    assert "I couldn't find any specific information" in result["sql_result"]
    mock_record_fallback.assert_called_once_with("sql_agent", "no_db_results")


@patch("app.agents.sql_agent.get_llm")
@patch("app.agents.sql_agent.record_agent_invocation")
@patch("app.agents.sql_agent.record_fallback_event")
def test_sql_agent_node_exception(mock_record_fallback, mock_record, mock_get_llm):
    """
    Test that if an exception is raised inside the SQL agent, it is handled cleanly
    and returns a system error message.
    """
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.invoke.side_effect = Exception("Vertex connection failed")

    state: AgentState = {
        "messages": [HumanMessage(content="Query loan details LN2003")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "sql_agent",
        "policy_retries": 0,
        "clarification_needed": False,
    }

    result = sql_agent_node(state)
    assert result["current_agent"] == "synthesize_response"
    assert "Sorry, I encountered a system error" in result["sql_result"]
    mock_record_fallback.assert_called_once_with("sql_agent", "system_error")


@patch("app.agents.sql_agent.get_llm")
@patch("app.agents.sql_agent.get_sql_database_tool")
@patch("app.agents.sql_agent.record_agent_invocation")
@patch("app.agents.sql_agent.record_fallback_event")
def test_sql_agent_node_missing_identifier(mock_record_fallback, mock_record, mock_get_db, mock_get_llm):
    """
    Test that if no specific identifier is provided, the SQL Agent detects
    the 'MISSING_IDENTIFIER' token and routes to the clarification node.
    """
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.invoke.return_value = AIMessage(content="MISSING_IDENTIFIER")
    mock_llm.return_value = AIMessage(content="MISSING_IDENTIFIER")

    state: AgentState = {
        "messages": [HumanMessage(content="Show me all loan details")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "sql_agent",
        "policy_retries": 0,
        "clarification_needed": False,
    }

    result = sql_agent_node(state)
    assert result["current_agent"] == "clarification_node"
    assert result["clarification_needed"] is True
    assert result["sql_result"] == "No data found"
    mock_record_fallback.assert_called_once_with("sql_agent", "missing_identifier")