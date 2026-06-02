from app.state import AgentState
import logging

logger = logging.getLogger(__name__)

def calculator_agent_node(state: AgentState) -> dict:
    """
    Agent responsible for running financial simulations.
    Handles 'what-if' scenarios like prepayments and amortization schedules.
    """
    logger.info("Calculator Agent processing...")
    
    query = state["messages"][-1].content
    
    # TODO: Parse query for numerical inputs (loan amount, interest, prepayment amount)
    # TODO: Implement amortization logic / validation
    
    # Mock result
    mock_result = f"Mock Calculator Result: If you prepay 10,000 INR, your new EMI will be 2,500 INR."
    
    return {"calc_result": mock_result, "current_agent": "synthesize_response"}
