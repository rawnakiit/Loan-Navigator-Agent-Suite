import logging
from app.state import AgentState
from app.utils.llm import get_llm
from app.utils.db import get_sql_database_tool

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

def sql_agent_node(state: AgentState) -> dict:
    """
    Agent responsible for Text-to-SQL operations.
    Uses a highly specific prompt based on the known database schema to generate accurate queries.
    """
    logger.info("SQL Agent: Processing query...")
    question = state["messages"][-1].content
    
    try:
        llm = get_llm()
        db = get_sql_database_tool()
        
        # This is the exact schema you provided. We are giving it directly to the LLM.
        schema_prompt = """
        You are a strict and precise SQLite expert. Your ONLY job is to write a valid SQLite query based on the schema below.

        CRITICAL RULES:
        1. The database has a single table named 'loan_data'. YOU MUST USE THIS TABLE NAME.
        2. The schema for the 'loan_data' table is as follows:
           - "loan_id" INTEGER: The unique ID of the loan (e.g., 2001, 2002).
           - "customer_id" INTEGER: The ID of the customer.
           - "loan_amount" REAL: The original amount of the loan.
           - "interest_rate" REAL: The annual interest rate.
           - "tenure_months" INTEGER: The loan duration in months.
           - "monthly_emi" REAL: The monthly payment amount.
           - "amount_paid" REAL: The total amount paid so far.
           - "status" TEXT: The current status of the loan (e.g., 'Active', 'Closed').
           - "topup_eligible" INTEGER: 1 for True, 0 for False.
        3. To calculate the 'outstanding balance', you MUST use the formula: (loan_amount - amount_paid).
        4. If a user provides a loan ID like 'LN2003' or 'loan 2003', you must strip the letters and use only the integer part (e.g., 2003) in the WHERE clause.
        5. Output ONLY the raw SQL query. Do not add explanations or markdown formatting like ```sql.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", schema_prompt),
            ("human", "Question: {question}\n\nGenerate the SQLite query:")
        ])
        
        sql_chain = prompt | llm | StrOutputParser()
        
        logger.info(f"Generating SQL query for: {question}")
        generated_sql = sql_chain.invoke({"question": question})
        
        # Clean up any residual formatting
        cleaned_sql = generated_sql.strip().replace("```sql", "").replace("```", "").strip()
        logger.info(f"Executing SQL: {cleaned_sql}")
        
        # Execute the query
        result = db.run(cleaned_sql)
        logger.info(f"Query Result: {result}")
        
        if not result or result.strip() == "[]":
            final_response = "I couldn't find any specific information in the database for your query. Please check the loan ID and try again."
        else:
            final_response = f"Database Data Retrieved: {result}"

        return {"sql_result": final_response, "current_agent": "synthesize_response"}

    except Exception as e:
        logger.error(f"Error in SQL Agent: {e}")
        return {
            "sql_result": "Sorry, I encountered a system error while trying to query the loan database.",
            "current_agent": "synthesize_response"
        }
