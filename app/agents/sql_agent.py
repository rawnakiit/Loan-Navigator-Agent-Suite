import logging
from app.state import AgentState
from app.utils.llm import get_llm
from app.utils.db import get_sql_database_tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.monitoring import record_agent_invocation, record_fallback_event

logger = logging.getLogger(__name__)

def sql_agent_node(state: AgentState) -> dict:
    logger.info("SQL Agent: Node started.")
    record_agent_invocation("sql_agent")
    
    question = state["messages"][-1].content
    try:
        llm = get_llm()
        db = get_sql_database_tool()
        
        # --- FINAL, SIMPLIFIED PROMPT ---
        schema_prompt = """You are a SQL writer. Your only job is to write a valid SQL query for a database.
        The database contains one table named 'loan_data'.

        SCHEMA:
        - "loan_id" INTEGER
        - "customer_id" INTEGER
        - "loan_amount" REAL
        - "amount_paid" REAL
        - "status" TEXT
        - "topup_eligible" INTEGER

        RULES:
        - To calculate 'outstanding balance', use the formula: (loan_amount - amount_paid).
        - If a user provides a loan ID like 'LN2003', use only the integer part (2003) in the WHERE clause.
        - Output ONLY the raw SQL query. Do not add explanations, markdown, or the word 'SQLite'.
        - Crucially, if the user query does NOT provide a specific loan ID (e.g. LN2003) or customer ID (e.g. 101), do NOT generate any SQL query. Instead, output exactly: MISSING_IDENTIFIER
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", schema_prompt),
            ("human", "Question: {question}\n\nSQL Query:")
        ])
        # ---------------------------------
        
        sql_chain = prompt | llm | StrOutputParser()
        generated_sql = sql_chain.invoke({"question": question})
        cleaned_sql = generated_sql.strip().replace("```sql", "").replace("```", "").strip()
        
        if "MISSING_IDENTIFIER" in cleaned_sql:
            record_fallback_event("sql_agent", "missing_identifier")
            logger.warning("SQL Agent: No specific loan or customer identifier provided in query.")
            return {
                "sql_result": "No data found",
                "current_agent": "clarification_node",
                "clarification_needed": True
            }

        logger.info(f"SQL Agent: Executing SQL: '{cleaned_sql}'")
        result = db.run(cleaned_sql)
        logger.info(f"SQL Agent: Raw query result: '{result}'")

        if not result or len(result.strip()) == 0 or result.strip() == '[]':
            record_fallback_event("sql_agent", "no_db_results")
            final_response = "I couldn't find any specific information for that query."
            logger.warning("SQL Agent: No results found in DB, triggering fallback.")
        else:
            final_response = f"Database Data Retrieved: {result}"
            
        logger.info(f"SQL Agent: Prepared response for synthesizer: '{final_response}'")
        return {"sql_result": final_response, "current_agent": "synthesize_response"}

    except Exception as e:
        record_fallback_event("sql_agent", "system_error")
        logger.error(f"SQL Agent: Encountered a system error - {str(e)}", exc_info=True)
        return {
            "sql_result": "Sorry, I encountered a system error querying the database.",
            "current_agent": "synthesize_response"
        }
