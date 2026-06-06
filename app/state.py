from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    The state dictionary for the LangGraph execution.
    Contains messages exchanged between agents, user intent,
    and the final generated response.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intent: str
    sql_result: str
    policy_result: str
    calc_result: str
    final_response: str
    current_agent: str
    policy_retries: int
    clarification_needed: bool
