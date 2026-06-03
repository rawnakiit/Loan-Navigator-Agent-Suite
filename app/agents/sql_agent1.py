# from app.state import AgentState
# import logging
#
# logger = logging.getLogger(__name__)
#
# def sql_agent_node(state: AgentState) -> dict:
#     """
#     Agent responsible for Text-to-SQL operations.
#     Converts natural language questions into secure SQL queries
#     and fetches data from the SQLite database.
#     """
#     logger.info("SQL Agent processing...")
#
#     query = state["messages"][-1].content
#
#     # TODO: Implement NLP to SQL conversion using Vertex AI
#     # TODO: Execute query via app.utils.db
#     # TODO: Handle fallbacks or empty results
#
#     # Mock result
#     mock_result = f"Mock SQL Result: Balance for your loan is 50,000 INR."
#
#     return {"sql_result": mock_result, "current_agent": "synthesize_response"}

import logging
from app.state import AgentState
from app.utils.llm import get_llm
from app.utils.db import get_sql_database_tool

# Correct, modern import path for the SQL query chain
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool

logger = logging.getLogger(__name__)



def sql_agent_node(state: AgentState) -> dict:
    """
    Agent responsible for Text-to-SQL operations.
    Converts natural language questions into secure SQL queries and fetches data.
    """
    logger.info("SQL Agent: Processing query...")

    # Get the latest message from the user
    question = state["messages"][-1].content

    try:
        # 1. Initialize tools
        llm = get_llm()
        db = get_sql_database_tool()

        # 2. Create the SQL generation chain (automatically injects your DB schema)
        generate_query_chain = create_sql_query_chain(llm, db)

        # 3. Tool to execute the generated SQL
        execute_query_tool = QuerySQLDataBaseTool(db=db)

        # 4. Generate the query
        logger.info(f"Generating SQL query for: {question}")
        generated_sql = generate_query_chain.invoke({"question": question})

        # Clean up any markdown formatting the LLM might add (e.g., ```sql ... ```)
        cleaned_sql = generated_sql.strip().replace("```sql", "").replace("```", "").strip()
        logger.info(f"Executing SQL: {cleaned_sql}")

        # 5. Execute the query
        result = execute_query_tool.invoke(cleaned_sql)
        logger.info(f"Query Result: {result}")

        # 6. Format the output
        if not result or result.strip() == "":
            final_response = "I couldn't find any specific information in the database for your query."
        else:
            final_response = f"Database Data Retrieved: {result}"

        # Return the result and instruct the graph to move to the synthesizer next
        return {"sql_result": final_response, "current_agent": "synthesize_response"}

    except Exception as e:
        logger.error(f"Error in SQL Agent: {e}")
        return {
            "sql_result": "Sorry, I encountered an error while querying the loan database.",
            "current_agent": "synthesize_response"
        }
