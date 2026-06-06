import pytest
import os
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from app.supervisor import app_graph, RouteQuery, run_supervisor

@patch("app.utils.llm.ChatGoogleGenerativeAI")
@patch("app.agents.sql_agent.get_sql_database_tool")
@patch("app.utils.monitoring._write_time_series")
@patch("app.supervisor.CallbackHandler")
def test_end_to_end_sql_flow(mock_callback, mock_metrics, mock_get_db, mock_chat_google_genai):
    """
    Verifies an end-to-end integration path:
    1. Supervisor routes user to 'sql_agent'.
    2. SQL Agent translates to SQL, executes it, and outputs structured results.
    3. Response Synthesizer merges results and outputs a final, warm response with (₹) symbols.
    """
    # Arrange
    mock_llm = MagicMock()
    mock_chat_google_genai.return_value = mock_llm

    # Mock the Supervisor's structured intent classifier
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = RouteQuery(
        destination="sql_agent",
        rewritten_query=None
    )
    mock_structured_llm.return_value = RouteQuery(
        destination="sql_agent",
        rewritten_query=None
    )
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # Mock sequential invoke returns:
    # 1. First invoke: SQL query writing inside sql_agent_node
    # 2. Second invoke: Synthesis of final natural language in synthesize_response_node
    mock_llm.side_effect = [
        AIMessage(content="SELECT loan_amount FROM loan_data WHERE customer_id = 101;"),
        AIMessage(content="Your loan amount with BlueLoans4all is ₹75,000. It is currently active.")
    ]
    mock_llm.invoke.side_effect = mock_llm.side_effect

    # Mock DB execution
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.run.return_value = "[(75000.0,)]"

    # Act
    initial_state = {
        "messages": [HumanMessage(content="How much is my loan amount?")]
    }
    
    # Execute the actual LangGraph workflow end-to-end
    result = app_graph.invoke(initial_state)

    # Assert
    assert "final_response" in result
    assert "₹75,000" in result["final_response"]
    assert result.get("clarification_needed", False) is False
    assert result["current_agent"] == "synthesize_response"

    # Ensure the database mock was queried
    mock_db.run.assert_called_once_with("SELECT loan_amount FROM loan_data WHERE customer_id = 101;")
    # Ensure both stages executed metrics
    assert mock_metrics.call_count >= 2


@patch("app.supervisor.app_graph")
@patch("app.supervisor.CallbackHandler")
@patch.dict(os.environ, {
    "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
    "LANGFUSE_SECRET_KEY": "sk-lf-test",
    "LANGFUSE_HOST": "https://test.langfuse.com"
})
def test_run_supervisor(mock_callback_class, mock_graph):
    """
    Test that run_supervisor builds the correct Langfuse CallbackHandler and
    invokes the graph.
    """
    mock_callback_instance = MagicMock()
    mock_callback_class.return_value = mock_callback_instance
    
    mock_graph.invoke.return_value = {
        "final_response": "Test finalized response",
        "clarification_needed": False
    }
    
    res = run_supervisor("This is a query", user_id="user-999")
    
    mock_callback_class.assert_called_once_with(
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        host="https://test.langfuse.com",
        trace_name="LoanNavigator-Trace",
        user_id="user-999",
        metadata={"query_source": "streamlit-ui"}
    )
    mock_graph.invoke.assert_called_once_with(
        {"messages": [HumanMessage(content="This is a query")]},
        config={"callbacks": [mock_callback_instance]}
    )
    assert res["final_response"] == "Test finalized response"