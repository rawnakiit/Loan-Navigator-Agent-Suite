import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from app.tools.calculator import calculate_emi, calculate_prepayment_impact
from app.agents.calculator_agent import calculator_agent_node
from app.state import AgentState

def test_calculate_emi_standard_formula():
    """
    Validates standard EMI calculation using the specification's reference example:
    - Principal: INR 75,000
    - Annual Rate: 12% (Monthly Rate: 1%)
    - Tenure: 12 Months
    - Expected EMI: INR 6,663.66
    """
    principal = 75000.0
    annual_rate = 12.0
    tenure = 12

    emi = calculate_emi(principal, annual_rate, tenure)
    assert emi == 6663.66


def test_calculate_prepayment_impact_success():
    """
    Validates successful prepayment simulation math for a borrower.
    Ensures:
    - Original EMI matches baseline.
    - Option A correctly reduces the EMI while keeping the tenure constant.
    - Option B correctly reduces the tenure (months saved) while keeping the original EMI.
    - Total interest saved is computed, positive, and correct.
    - Amortization schedules for both options are properly compiled and terminate at zero.
    """
    # Arrange
    principal = 75000.0
    annual_rate = 12.0
    remaining_tenure = 12
    prepayment = 10000.0

    # Act
    result = calculate_prepayment_impact(
        principal=principal,
        annual_interest_rate=annual_rate,
        remaining_tenure_months=remaining_tenure,
        prepayment_amount=prepayment
    )

    # Assert General Properties
    assert result["status"] == "Success"
    assert result["original_principal"] == principal
    assert result["prepayment_amount"] == prepayment
    assert result["new_principal"] == 65000.0
    assert result["original_emi"] == 6663.66
    assert result["original_total_repayment"] > principal

    # Option A Assertions (Reduce EMI, Keep Tenure)
    assert result["option_a_new_emi"] < result["original_emi"]
    assert result["option_a_new_emi"] == 5775.17  # calculate_emi(65000, 12, 12)
    assert len(result["option_a_schedule"]) == remaining_tenure
    assert result["option_a_interest_saved"] > 0
    # Last month of schedule must have a zero remaining balance
    assert result["option_a_schedule"][-1]["remaining_balance"] == 0.0

    # Option B Assertions (Reduce Tenure, Keep EMI)
    assert len(result["option_b_schedule"]) < remaining_tenure
    assert result["option_b_new_tenure_months"] == len(result["option_b_schedule"])
    assert result["option_b_months_saved"] == remaining_tenure - result["option_b_new_tenure_months"]
    assert result["option_b_months_saved"] > 0
    assert result["option_b_interest_saved"] > 0
    # Ensure the standard monthly payment on option B (except the last payment) is the original EMI
    for payment_entry in result["option_b_schedule"][:-1]:
        assert payment_entry["payment"] == result["original_emi"]
    # Last month of schedule must have a zero remaining balance
    assert result["option_b_schedule"][-1]["remaining_balance"] == 0.0


def test_calculate_prepayment_impact_loan_closed():
    """
    Validates simulation logic when the prepayment amount is greater than
    or equal to the outstanding principal balance.
    """
    # Arrange
    principal = 75000.0
    annual_rate = 12.0
    remaining_tenure = 12
    prepayment = 80000.0  # Overpaying outstanding principal

    # Act
    result = calculate_prepayment_impact(
        principal=principal,
        annual_interest_rate=annual_rate,
        remaining_tenure_months=remaining_tenure,
        prepayment_amount=prepayment
    )

    # Assert
    assert result["status"] == "Loan Closed"
    assert "covers the entire outstanding balance" in result["message"]


@patch("app.agents.calculator_agent.get_llm")
@patch("app.agents.calculator_agent.record_agent_invocation")
def test_calculator_agent_node_successful_extraction(mock_record, mock_get_llm):
    """
    Test that a valid JSON mock LLM response is parsed successfully,
    the calculation runs, and the result routes to synthesize_response.
    """
    # Arrange
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    # JSON output matching the CalculatorInput schema
    mock_llm.invoke.return_value = AIMessage(
        content='{"principal": 75000.0, "interest_rate": 12.0, "tenure_months": 12, "prepayment_amount": 10000.0}'
    )
    mock_llm.return_value = AIMessage(
        content='{"principal": 75000.0, "interest_rate": 12.0, "tenure_months": 12, "prepayment_amount": 10000.0}'
    )
    
    state: AgentState = {
        "messages": [HumanMessage(content="Prepay 10,000 on 75,000 at 12% for 12 months")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "calculator_agent",
        "policy_retries": 0,
        "clarification_needed": False,
    }
    
    # Act
    result = calculator_agent_node(state)
    
    # Assert
    assert result["current_agent"] == "synthesize_response"
    assert "Calculation Result:" in result["calc_result"]
    assert "₹10000" in result["calc_result"]
    mock_llm.assert_called_once()


@patch("app.agents.calculator_agent.get_llm")
@patch("app.agents.calculator_agent.record_agent_invocation")
def test_calculator_agent_node_prepayment_exceeds_principal(mock_record, mock_get_llm):
    """
    Test that when prepayment amount exceeds principal, the calculator validation
    correctly intercepts it and routes to clarification_node.
    """
    # Arrange
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    # prepayment_amount (60000.0) > principal (50000.0)
    mock_llm.invoke.return_value = AIMessage(
        content='{"principal": 50000.0, "interest_rate": 10.0, "tenure_months": 12, "prepayment_amount": 60000.0}'
    )
    mock_llm.return_value = AIMessage(
        content='{"principal": 50000.0, "interest_rate": 10.0, "tenure_months": 12, "prepayment_amount": 60000.0}'
    )
    
    state: AgentState = {
        "messages": [HumanMessage(content="Prepay 60,000 on 50,000 loan")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "calculator_agent",
        "policy_retries": 0,
        "clarification_needed": False,
    }
    
    # Act
    result = calculator_agent_node(state)
    
    # Assert
    assert result["current_agent"] == "clarification_node"
    assert result["clarification_needed"] is True
    assert "Validation Error: The prepayment amount" in result["calc_result"]


@patch("app.agents.calculator_agent.get_llm")
@patch("app.agents.calculator_agent.record_agent_invocation")
@patch("app.agents.calculator_agent.record_fallback_event")
def test_calculator_agent_node_malformed_json_fallback(mock_record_fallback, mock_record, mock_get_llm):
    """
    Test that when the LLM returns a malformed non-JSON output, the exception is
    caught and handled cleanly, routing to clarification_node and recording the metric.
    """
    # Arrange
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    mock_llm.invoke.return_value = AIMessage(content="Sorry, I cannot help with that.")
    mock_llm.return_value = AIMessage(content="Sorry, I cannot help with that.")
    
    state: AgentState = {
        "messages": [HumanMessage(content="Prepayment calculations")],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": "calculator_agent",
        "policy_retries": 0,
        "clarification_needed": False,
    }
    
    # Act
    result = calculator_agent_node(state)
    
    # Assert
    assert result["current_agent"] == "clarification_node"
    assert result["clarification_needed"] is True
    assert "Validation Error: Calculation failed" in result["calc_result"]
    mock_record_fallback.assert_called_once_with("calculator_agent", "parsing_error")