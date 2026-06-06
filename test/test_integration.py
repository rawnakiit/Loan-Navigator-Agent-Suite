import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from app.supervisor import app_graph, RouteQuery

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
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # Mock sequential invoke returns:
    # 1. First invoke: SQL query writing inside sql_agent_node
    # 2. Second invoke: Synthesis of final natural language in synthesize_response_node
    mock_llm.invoke.side_effect = [
        AIMessage(content="SELECT loan_amount FROM loan_data WHERE customer_id = 101;"),
        AIMessage(content="Your loan amount with BlueLoans4all is ₹75,000. It is currently active.")
    ]

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
    assert result["clarification_needed"] is False
    assert result["current_agent"] == "synthesize_response"

    # Ensure the database mock was queried
    mock_db.run.assert_called_once_with("SELECT loan_amount FROM loan_data WHERE customer_id = 101;")
    # Ensure both stages executed metrics
    assert mock_metrics.call_count >= 2