import logging
from app.state import AgentState
from app.utils.llm import get_llm
from app.tools.calculator import calculate_prepayment_impact

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
# Modern, standard Pydantic import
from pydantic import BaseModel, Field
from app.utils.monitoring import record_agent_invocation, record_fallback_event

logger = logging.getLogger(__name__)

# Standard Pydantic schema to extract parameters reliably
class CalculatorInput(BaseModel):
    principal: float = Field(description="The outstanding principal loan amount.")
    interest_rate: float = Field(description="The annual interest rate (e.g., 9.5).")
    tenure_months: int = Field(description="The remaining tenure of the loan in months.")
    prepayment_amount: float = Field(description="The amount the user wishes to prepay.")

def calculator_agent_node(state: AgentState) -> dict:
    """
    Agent responsible for running financial simulations.
    Extracts numerical parameters from the query and runs Python calculation logic.
    """
    logger.info("Calculator Agent: Processing query...")
    record_agent_invocation("calculator_agent") # <-- METRIC: Invocation recorded
    
    query = state["messages"][-1].content
    
    try:
        # 1. Use LLM to extract numerical parameters from the user's question
        system_prompt = """
        You are a data extraction assistant. Extract the financial parameters from the user's query 
        to feed into a prepayment calculator.
        
        If a value is missing from the user's query, assume the following defaults:
        - principal: 100000 (if not specified)
        - interest_rate: 10.0 (if not specified)
        - tenure_months: 24 (if not specified)
        - prepayment_amount: 10000 (if not specified)
        
        Output MUST be a valid JSON matching the required schema.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])
        
        llm = get_llm()
        parser = JsonOutputParser(pydantic_object=CalculatorInput)
        
        extraction_chain = prompt | llm | parser
        logger.info("Extracting parameters from query...")
        params = extraction_chain.invoke({"question": query})
        
        # 2. Run the actual Python calculation logic
        logger.info(f"Running simulation with params: {params}")
        sim_result = calculate_prepayment_impact(
            principal=params["principal"],
            annual_interest_rate=params["interest_rate"],
            remaining_tenure_months=params["tenure_months"],
            prepayment_amount=params["prepayment_amount"]
        )
        
        # 3. Format the result for the synthesizer
        if sim_result["status"] == "Loan Closed":
             final_response = f"Calculation Result: {sim_result['message']}"
        else:
             final_response = (
                 f"Calculation Result: By prepaying ₹{params['prepayment_amount']}, your new principal becomes ₹{sim_result['new_principal']}. "
                 f"You have two options:\n"
                 f"1. Reduce your EMI: Your new EMI will be ₹{sim_result['option_a_new_emi']} (Original was ₹{sim_result['original_emi']}).\n"
                 f"2. Reduce your tenure: Keep your EMI same, and your loan will end {sim_result['option_b_months_saved']} months earlier."
             )
        
        return {"calc_result": final_response, "current_agent": "synthesize_response"}

    except Exception as e:
        record_fallback_event("calculator_agent", "parsing_error") # <-- METRIC: Error Fallback
        logger.error(f"Error in Calculator Agent: {e}")
        error_msg = "Sorry, I couldn't perform the calculation. Please ensure you provide the loan amount, interest rate, and prepayment amount clearly."
        return {"calc_result": error_msg, "current_agent": "synthesize_response"}