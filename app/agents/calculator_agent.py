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
        
        principal = params.get("principal", 0.0)
        prepayment_amount = params.get("prepayment_amount", 0.0)
        interest_rate = params.get("interest_rate", 0.0)
        tenure_months = params.get("tenure_months", 0)

        # Perform explicit input validation to catch errors
        if principal <= 0 or interest_rate <= 0 or tenure_months <= 0 or prepayment_amount <= 0:
            err_msg = "The loan balance, interest rate, tenure, and prepayment amount must all be positive values greater than zero."
            logger.warning(f"Calculator Agent Validation Error: {err_msg}")
            return {
                "calc_result": f"Validation Error: {err_msg}",
                "current_agent": "clarification_node",
                "clarification_needed": True
            }

        if prepayment_amount > principal:
            err_msg = f"The prepayment amount (₹{prepayment_amount}) cannot exceed your outstanding principal balance (₹{principal})."
            logger.warning(f"Calculator Agent Validation Error: {err_msg}")
            return {
                "calc_result": f"Validation Error: {err_msg}",
                "current_agent": "clarification_node",
                "clarification_needed": True
            }

        # 2. Run the actual Python calculation logic
        logger.info(f"Running simulation with params: {params}")
        sim_result = calculate_prepayment_impact(
            principal=principal,
            annual_interest_rate=interest_rate,
            remaining_tenure_months=tenure_months,
            prepayment_amount=prepayment_amount
        )
        
        # 3. Format the result for the synthesizer
        if sim_result["status"] == "Loan Closed":
             final_response = f"Calculation Result: {sim_result['message']}"
        else:
             def format_schedule_summary(schedule: list) -> str:
                 if len(schedule) <= 6:
                     lines = [f"Month {s['month']}: Payment ₹{s['payment']}, Interest ₹{s['interest_paid']}, Principal Paid ₹{s['principal_paid']}, Remaining Balance ₹{s['remaining_balance']}" for s in schedule]
                     return "\n".join(lines)
                 else:
                     first_3 = schedule[:3]
                     last_3 = schedule[-3:]
                     lines = [f"Month {s['month']}: Payment ₹{s['payment']}, Interest ₹{s['interest_paid']}, Principal Paid ₹{s['principal_paid']}, Remaining Balance ₹{s['remaining_balance']}" for s in first_3]
                     lines.append("...")
                     for s in last_3:
                         lines.append(f"Month {s['month']}: Payment ₹{s['payment']}, Interest ₹{s['interest_paid']}, Principal Paid ₹{s['principal_paid']}, Remaining Balance ₹{s['remaining_balance']}")
                     return "\n".join(lines)

             final_response = (
                 f"Calculation Result:\n"
                 f"By making a prepayment of ₹{params['prepayment_amount']}, your new outstanding principal becomes ₹{sim_result['new_principal']}.\n"
                 f"Original Total Repayment: ₹{sim_result['original_total_repayment']}\n\n"
                 f"Option A: Reduce EMI (Keep original tenure of {tenure_months} months):\n"
                 f"- New Monthly EMI: ₹{sim_result['option_a_new_emi']} (Original was ₹{sim_result['original_emi']})\n"
                 f"- Total Repayment Amount: ₹{sim_result['option_a_total_repayment']}\n"
                 f"- Total Interest Saved: ₹{sim_result['option_a_interest_saved']}\n"
                 f"- Amortization Schedule Summary:\n{format_schedule_summary(sim_result['option_a_schedule'])}\n\n"
                 f"Option B: Reduce Tenure (Keep original EMI of ₹{sim_result['original_emi']}):\n"
                 f"- New Loan Tenure: {sim_result['option_b_new_tenure_months']} months (Reduced by {sim_result['option_b_months_saved']} months)\n"
                 f"- Total Repayment Amount: ₹{sim_result['option_b_total_repayment']}\n"
                 f"- Total Interest Saved: ₹{sim_result['option_b_interest_saved']}\n"
                 f"- Amortization Schedule Summary:\n{format_schedule_summary(sim_result['option_b_schedule'])}"
             )
        
        return {"calc_result": final_response, "current_agent": "synthesize_response"}

    except Exception as e:
        record_fallback_event("calculator_agent", "parsing_error") # <-- METRIC: Error Fallback
        logger.error(f"Error in Calculator Agent: {e}")
        error_msg = f"Calculation failed: {str(e)}"
        return {
            "calc_result": f"Validation Error: {error_msg}",
            "current_agent": "clarification_node",
            "clarification_needed": True
        }
