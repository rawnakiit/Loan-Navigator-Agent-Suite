import logging
from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.agents import sql_agent_node, policy_agent_node, calculator_agent_node
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

def supervisor_node(state: AgentState):
    """
    The central orchestrator node.
    Responsible for classifying user intent and deciding the next node.
    """
    logger.info("Supervisor analyzing intent...")
    
    # TODO: Use LLM to classify intent based on state["messages"]
    # Mock intent classification for skeleton:
    query = state["messages"][-1].content.lower()
    
    if "emi" in query or "balance" in query:
        intent = "sql"
        next_node = "sql_agent"
    elif "policy" in query or "rule" in query or "eligibility" in query:
        intent = "policy"
        next_node = "policy_agent"
    elif "calculate" in query or "what-if" in query or "prepayment" in query:
        intent = "calculator"
        next_node = "calculator_agent"
    else:
        intent = "unknown"
        next_node = "synthesize_response"
        
    return {"intent": intent, "current_agent": next_node}

def synthesize_response_node(state: AgentState):
    """
    Synthesizes the final response from all collected results.
    """
    logger.info("Synthesizing final response...")
    # TODO: Use LLM to generate a natural language response
    
    parts = []
    if state.get("sql_result"):
        parts.append(state["sql_result"])
    if state.get("policy_result"):
        parts.append(state["policy_result"])
    if state.get("calc_result"):
        parts.append(state["calc_result"])
        
    final_resp = "\n".join(parts) if parts else "I couldn't find an answer to your query."
    return {"final_response": final_resp}

def router(state: AgentState) -> str:
    """
    Routing logic based on the current agent state.
    """
    return state.get("current_agent", "synthesize_response")

# Build the Graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("sql_agent", sql_agent_node)
workflow.add_node("policy_agent", policy_agent_node)
workflow.add_node("calculator_agent", calculator_agent_node)
workflow.add_node("synthesize_response", synthesize_response_node)

# Add edges
workflow.set_entry_point("supervisor")

# Conditional edges from supervisor
workflow.add_conditional_edges(
    "supervisor",
    router,
    {
        "sql_agent": "sql_agent",
        "policy_agent": "policy_agent",
        "calculator_agent": "calculator_agent",
        "synthesize_response": "synthesize_response"
    }
)

# Agents route back to synthesize
workflow.add_edge("sql_agent", "synthesize_response")
workflow.add_edge("policy_agent", "synthesize_response")
workflow.add_edge("calculator_agent", "synthesize_response")
workflow.add_edge("synthesize_response", END)

# Compile the graph
app_graph = workflow.compile()

def run_supervisor(query: str) -> dict:
    """
    Entry point to trigger the workflow.
    """
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "intent": "",
        "sql_result": "",
        "policy_result": "",
        "calc_result": "",
        "final_response": "",
        "current_agent": ""
    }
    
    result = app_graph.invoke(initial_state)
    return result
