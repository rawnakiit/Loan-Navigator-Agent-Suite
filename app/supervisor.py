import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.agents import sql_agent_node, policy_agent_node, calculator_agent_node
from app.utils.llm import get_llm
from langchain_core.messages import HumanMessage
# from langchain_core.pydantic_v1 import BaseModel, Field
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from app.utils.monitoring import record_agent_invocation, record_fallback_event
from langfuse.langchain import CallbackHandler
import os

logger = logging.getLogger(__name__)


# --- 1. SUPERVISOR (ROUTER) LOGIC ---

# Use Pydantic to define the output schema for our router
class RouteQuery(BaseModel):
    """Decide where to route the user's query."""
    destination: Literal["sql_agent", "policy_agent", "calculator_agent", "end_conversation"] = Field(
        description="Given the user query, pick the best tool/agent to handle it."
    )
    rewritten_query: str | None = Field(
        default=None,
        description="If routing to 'policy_agent' and previous attempts failed, provide a rewritten, broader query to search the vector database. Otherwise, leave null."
    )


def supervisor_node(state: AgentState):
    """
    The central orchestrator node.
    This node uses an LLM to classify the user's intent and decide which agent to call next.
    """
    logger.info("Supervisor: Analyzing intent...")
    record_agent_invocation("supervisor") # <-- METRIC: Supervisor Invoked

    retries = state.get("policy_retries", 0)
    if retries >= 2:
        logger.warning(f"Supervisor: Max retries ({retries}) reached for policy lookup. Routing to clarification_node.")
        return {"current_agent": "clarification_node", "clarification_needed": True}

    query = state["messages"][-1].content
    llm = get_llm()

    # Create a structured output chain to force the LLM to choose a destination
    structured_llm = llm.with_structured_output(RouteQuery)

    # If this is a retry, build a prompt that alerts the LLM to rewrite the query
    if retries > 0:
        original_query = ""
        for msg in reversed(state["messages"]):
            if msg.type == "human":
                original_query = msg.content
                break
        system_prompt = f"""You are an expert routing assistant for a loan processing system.
        The user's original query was: "{original_query}".
        A previous attempt to retrieve policy documents failed because no high-confidence records were found.
        Your job is to either:
        1. Route back to 'policy_agent' and provide a rewritten, broader query in 'rewritten_query' to search the policy database.
        2. Route to 'end_conversation' if you need to ask the user for clarification.
        """
    else:
        # Prompt the LLM to route the query
        system_prompt = """You are an expert routing assistant for a loan processing system. Your job is to determine the best agent to handle a user's query.
        The available agents are:
        - 'sql_agent': Use for questions about specific loan details like "what is my balance?", "show my EMI amount", or any query that requires fetching exact data for a specific loan from a database.
        - 'policy_agent': Use for general questions about company rules, prepayment policies, top-up eligibility criteria, or regulatory guidelines.
        - 'calculator_agent': Use for "what-if" scenarios, such as "what happens if I prepay 50,000?", or any query that requires mathematical calculation.
        - 'end_conversation': Use for simple greetings, thank yous, or any query that does not require using a tool.
        """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{query}")
    ])

    router_chain = prompt | structured_llm

    # The result will be a Pydantic object with the destination
    route = router_chain.invoke({"query": query})
    logger.info(f"Supervisor: Routing to '{route.destination}'")

    if route.destination == "end_conversation":
        record_fallback_event("supervisor", "unknown_intent") # <-- METRIC: Supervisor Fallback
        return {"current_agent": "synthesize_response"}
    elif route.destination == "policy_agent" and route.rewritten_query:
        logger.info(f"Supervisor: Rewriting policy query to: '{route.rewritten_query}'")
        return {
            "current_agent": "policy_agent",
            "messages": [HumanMessage(content=route.rewritten_query)]
        }
    else:
        return {"current_agent": route.destination}


# --- 2. RESPONSE SYNTHESIZER LOGIC ---

def synthesize_response_node(state: AgentState):
    """
    Synthesizes the final user-facing response from all collected results.
    This node uses an LLM to create a single, coherent, and helpful answer.
    """
    logger.info("Synthesizer: Compiling final response...")
    record_agent_invocation("synthesizer") # <-- METRIC: Supervisor Invoked
    query = state["messages"][-1].content

    # Collect all the results from the agent states
    context = ""
    if state.get("sql_result"):
        context += f"Data from the database:\n{state['sql_result']}\n\n"
    if state.get("policy_result"):
        context += f"Relevant policy guidelines:\n{state['policy_result']}\n\n"
    if state.get("calc_result"):
        context += f"Calculation results:\n{state['calc_result']}\n\n"

    # If no tools were called, provide a generic response
    if not context:
        record_fallback_event("synthesizer", "no_agent_data") # <-- METRIC: Supervisor Fallback
        final_resp = "I'm here to help with your loan questions. Feel free to ask about your balance, our policies, or to run a prepayment simulation."
        return {"final_response": final_resp}

    # Use an LLM to synthesize a natural language response
    # system_prompt = """You are a helpful and friendly AI assistant for BlueLoans4all.
    # Your task is to create a single, clear, and concise response for the user based on the information gathered by our internal tools.
    # Combine the information from the different sources into a single, easy-to-understand answer.

    # - Address the user's original question directly.
    # - Do not just list the raw data. Explain what it means.
    # - Maintain a professional and helpful tone.
    # - Do not mention the internal tools or agent names (e.g., "The SQL agent found..."). Just present the final answer.
    # """
    system_prompt = """You are a helpful and friendly AI assistant for BlueLoans4all, an Indian financial company.
    Your task is to create a single, clear, and concise response for the user based on the information gathered by our internal tools.
    Combine the information from the different sources into a single, easy-to-understand answer.
    
    - Address the user's original question directly.
    - **Crucially, when mentioning any monetary values (like loan balances, EMIs, or amounts), you MUST use the Indian Rupee symbol (₹).**
    - Do not just list the raw data. Explain what it means in a helpful way.
    - Maintain a professional and helpful tone.
    - Do not mention the internal tools or agent names (e.g., "The SQL agent found..."). Just present the final answer.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "My original question was: {query}\n\nHere is the information our system found:\n{context}")
    ])

    llm = get_llm()
    synthesis_chain = prompt | llm | StrOutputParser()

    final_resp = synthesis_chain.invoke({
        "query": query,
        "context": context
    })

    return {"final_response": final_resp}


def clarification_node(state: AgentState):
    """
    Triggered when database/policy lookup fails or max retries are reached.
    Conversational agent requesting clarification.
    """
    logger.info("Clarification Node: Formulating clarification request...")
    query = state["messages"][-1].content
    
    # Try to determine context of failure
    failure_context = ""
    calc_res = state.get("calc_result", "")
    if state.get("policy_result") == "I couldn't find specific rules regarding this in the policy manuals.":
        failure_context = "policy manuals search returned no relevant matches"
    elif state.get("sql_result") == "No data found" or not state.get("sql_result"):
        failure_context = "loan database queries did not match any specific customer records"
    elif calc_res.startswith("Validation Error:"):
        failure_context = f"the loan prepayment calculator simulation failed because of validation rules: {calc_res.replace('Validation Error:', '').strip()}"

    system_prompt = f"""You are a customer support agent for BlueLoans4all.
    Our automated backend failed to find specific results for the user's query: "{query}".
    Reason/Context: {failure_context or 'No specific records or manuals match the query.'}
    
    Write a brief, polite, and professional response asking the user to clarify or expand their query
    (e.g., providing their loan account number, being more specific with terms, or entering valid loan/prepayment amounts) so we can help them.
    Do not use developer jargon or name internal agents. Keep it customer-friendly and warm.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{query}")
    ])
    
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()
    resp = chain.invoke({"query": query})
    
    return {
        "final_response": resp,
        "clarification_needed": True,
        "current_agent": END
    }


# --- 3. GRAPH DEFINITION AND WIRING ---

# The router function remains the same
def router(state: AgentState) -> str:
    """Routing logic based on the 'current_agent' field in the state."""
    return state.get("current_agent", "synthesize_response")


# Build the Graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("sql_agent", sql_agent_node)
workflow.add_node("policy_agent", policy_agent_node)
workflow.add_node("calculator_agent", calculator_agent_node)
workflow.add_node("synthesize_response", synthesize_response_node)
workflow.add_node("clarification_node", clarification_node)

# Add edges
workflow.set_entry_point("supervisor")

# Conditional edges from supervisor to the specialized agents
workflow.add_conditional_edges(
    "supervisor",
    router,
    {
        "sql_agent": "sql_agent",
        "policy_agent": "policy_agent",
        "calculator_agent": "calculator_agent",
        "clarification_node": "clarification_node",
        "synthesize_response": "synthesize_response"  # For when no tool is needed
    }
)

# All specialized agents route back to the synthesizer
workflow.add_edge("sql_agent", "synthesize_response")

# Policy agent routes conditionally back to supervisor or to synthesize_response
workflow.add_conditional_edges(
    "policy_agent",
    router,
    {
        "supervisor": "supervisor",
        "clarification_node": "clarification_node",
        "synthesize_response": "synthesize_response"
    }
)

# Calculator agent routes conditionally to clarification_node or synthesize_response
workflow.add_conditional_edges(
    "calculator_agent",
    router,
    {
        "clarification_node": "clarification_node",
        "synthesize_response": "synthesize_response"
    }
)

# The synthesizer marks the end of the process
workflow.add_edge("synthesize_response", END)

# The clarification node marks the end of the process
workflow.add_edge("clarification_node", END)

# Compile the graph
app_graph = workflow.compile()


# The entry point function remains the same
def run_supervisor(query: str, user_id:str="default-user") -> dict:
    """Entry point to trigger the workflow."""
    # Initialize the Langfuse CallbackHandler. Keys are read automatically from environment variables.
    langfuse_callback = CallbackHandler()

    initial_state = {
        "messages": [HumanMessage(content=query)],
    }
    # The invoke method will return the final state of the graph
    final_state = app_graph.invoke(
        initial_state,
        config={
            "callbacks": [langfuse_callback],
            "run_name": "LoanNavigator-Trace",
            "metadata": {
                "langfuse_user_id": user_id,
                "query_source": "streamlit-ui"
            }
        }
    )

    # Explicitly log the final outcome of the interaction for terminal and cloud logging
    final_resp = final_state.get("final_response", "")
    clarification_status = final_state.get("clarification_needed", False)
    logger.info(
        f"Supervisor Execution Completed. "
        f"Clarification Needed: {clarification_status} | "
        f"Final Response: '{final_resp[:150]}...'"
    )
    return final_state
