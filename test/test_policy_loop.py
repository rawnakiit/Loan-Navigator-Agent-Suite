import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, SystemMessage
from app.state import AgentState
from app.agents.policy_agent import policy_agent_node
from app.supervisor import supervisor_node, RouteQuery, clarification_node

@patch("app.agents.policy_agent.get_vector_store")
@patch("app.agents.policy_agent.record_agent_invocation")
@patch("app.agents.policy_agent.record_fallback_event")
def test_policy_agent_fallback_on_poor_similarity_scores(
    mock_record_fallback, mock_record_invocation, mock_get_vector_store
):
    """
    Test that if Chroma returns matches with distances above the threshold (> 0.75),
    the agent registers a fallback, increments retries, and returns to the supervisor.
    """
    # Arrange
    mock_vector_store = MagicMock()
    mock_doc = MagicMock()
    mock_doc.metadata = {"source": "manual.pdf", "page": 1}
    mock_doc.page_content = "This content is irrelevant."
    
    # 0.85 distance is > 0.75 threshold (poor match/low confidence)
    mock_vector_store.similarity_search_with_score.return_value = [
        (mock_doc, 0.85)
    ]
    mock_get_vector_store.return_value = mock_vector_store

    initial_state: AgentState = {
        "messages": [HumanMessage(content="What are the rules for prepaying loans?")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "policy_agent",
        "policy_retries": 0,
    }

    # Act
    result = policy_agent_node(initial_state)

    # Assert
    assert result["policy_retries"] == 1
    assert result["current_agent"] == "supervisor"
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], SystemMessage)
    assert "No policy documents matched" in result["messages"][0].content
    mock_record_fallback.assert_called_once_with("policy_agent")


@patch("app.supervisor.get_llm")
def test_supervisor_max_retries_safeguard(mock_get_llm):
    """
    Test that if max retries (>= 2) has been hit, the supervisor forces
    routing to 'synthesize_response' immediately without querying the LLM.
    """
    # Arrange
    initial_state: AgentState = {
        "messages": [
            HumanMessage(content="What are the rules for prepaying loans?"),
            SystemMessage(content="System Note: No documents matched. Retry #2"),
        ],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "supervisor",
        "policy_retries": 2,
    }

    # Act
    result = supervisor_node(initial_state)

    # Assert
    mock_get_llm.assert_not_called()
    assert result == {"current_agent": "clarification_node", "clarification_needed": True}


@patch("app.supervisor.get_llm")
def test_supervisor_rewrites_query_for_policy_retry(mock_get_llm):
    """
    Test that on a retry cycle, the supervisor requests a rewritten query
    from the LLM structured output and passes it as a new HumanMessage.
    """
    # Arrange
    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # Simulate LLM choosing to rewrite the query
    mock_structured_llm.invoke.return_value = RouteQuery(
        destination="policy_agent",
        rewritten_query="BlueLoans4all rules and options for paying loans off early"
    )
    mock_structured_llm.return_value = RouteQuery(
        destination="policy_agent",
        rewritten_query="BlueLoans4all rules and options for paying loans off early"
    )

    initial_state: AgentState = {
        "messages": [
            HumanMessage(content="prepayment rules?"),
            SystemMessage(content="System Note: No high confidence documents matched. Retry #1"),
        ],
        "intent": "",
        "current_agent": "supervisor",
        "policy_retries": 1,
    }

    # Act
    result = supervisor_node(initial_state)

    # Assert
    assert result["current_agent"] == "policy_agent"
    assert result["messages"][0].content == "BlueLoans4all rules and options for paying loans off early"


@patch("app.agents.policy_agent.get_vector_store")
@patch("app.agents.policy_agent.get_llm")
@patch("app.agents.policy_agent.record_agent_invocation")
def test_policy_agent_success_path(
    mock_record_invocation, mock_get_llm, mock_get_vector_store
):
    """
    Test that if Chroma returns matches with distances below the threshold (<= 0.75),
    the policy agent runs the RAG chain successfully.
    """
    mock_vector_store = MagicMock()
    mock_doc = MagicMock()
    mock_doc.metadata = {"source": "manual.pdf", "page": 1}
    mock_doc.page_content = "This content is highly relevant."
    
    # 0.5 distance is <= 0.75 threshold (high confidence match)
    mock_vector_store.similarity_search_with_score.return_value = [
        (mock_doc, 0.5)
    ]
    mock_get_vector_store.return_value = mock_vector_store

    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.invoke.return_value = AIMessage(content="According to manual.pdf page 1, early prepayment is allowed.")
    mock_llm.return_value = AIMessage(content="According to manual.pdf page 1, early prepayment is allowed.")

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Can I prepay early?")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "policy_agent",
        "policy_retries": 0,
        "clarification_needed": False,
    }

    result = policy_agent_node(initial_state)

    assert result["current_agent"] == "synthesize_response"
    assert "early prepayment is allowed" in result["policy_result"]


@patch("app.agents.policy_agent.get_vector_store")
@patch("app.agents.policy_agent.record_agent_invocation")
@patch("app.agents.policy_agent.record_fallback_event")
def test_policy_agent_max_retries_reached(
    mock_record_fallback, mock_record_invocation, mock_get_vector_store
):
    """
    Test that if Chroma returns poor matches and retry is already 1,
    the policy agent redirects to clarification_node.
    """
    mock_vector_store = MagicMock()
    mock_doc = MagicMock()
    mock_doc.metadata = {"source": "manual.pdf", "page": 1}
    mock_doc.page_content = "Irrelevant content."
    mock_vector_store.similarity_search_with_score.return_value = [
        (mock_doc, 0.9)
    ]
    mock_get_vector_store.return_value = mock_vector_store

    initial_state: AgentState = {
        "messages": [HumanMessage(content="Can I prepay early?")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "policy_agent",
        "policy_retries": 1,
        "clarification_needed": False,
    }

    result = policy_agent_node(initial_state)

    assert result["policy_retries"] == 2
    assert result["current_agent"] == "clarification_node"
    assert result["clarification_needed"] is True
    assert result["policy_result"] == "I couldn't find specific rules regarding this in the policy manuals."


@patch("app.supervisor.get_llm")
def test_clarification_node_policy_error(mock_get_llm):
    """
    Test that clarification_node creates a correct system prompt and gets LLM response
    when policy lookup fails.
    """
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.invoke.return_value = AIMessage(content="Could you clarify your policy query?")
    mock_llm.return_value = AIMessage(content="Could you clarify your policy query?")

    state: AgentState = {
        "messages": [HumanMessage(content="What are the rules for prepaying loans?")],
        "intent": "",
        "sql_result": "",
        "policy_result": "I couldn't find specific rules regarding this in the policy manuals.",
        "calc_result": "",
        "final_response": "",
        "current_agent": "clarification_node",
        "policy_retries": 2,
        "clarification_needed": True,
    }

    result = clarification_node(state)
    assert result["clarification_needed"] is True
    assert result["final_response"] == "Could you clarify your policy query?"


@patch("app.supervisor.get_llm")
def test_clarification_node_calc_error(mock_get_llm):
    """
    Test that clarification_node creates a correct system prompt and gets LLM response
    when calculator validation fails.
    """
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.invoke.return_value = AIMessage(content="Could you clarify your prepayment amount?")
    mock_llm.return_value = AIMessage(content="Could you clarify your prepayment amount?")

    state: AgentState = {
        "messages": [HumanMessage(content="Prepay 10,000 on a 500 loan")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "Validation Error: The prepayment amount cannot exceed outstanding principal balance",
        "final_response": "",
        "current_agent": "clarification_node",
        "policy_retries": 0,
        "clarification_needed": True,
    }

    result = clarification_node(state)
    assert result["clarification_needed"] is True
    assert result["final_response"] == "Could you clarify your prepayment amount?"