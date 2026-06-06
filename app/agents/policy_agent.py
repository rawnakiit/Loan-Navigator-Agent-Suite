import logging
import os
from app.state import AgentState
from app.utils.llm import get_llm
from app.utils.vector_store import get_vector_store

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.monitoring import record_agent_invocation, record_fallback_event


logger = logging.getLogger(__name__)


def policy_agent_node(state: AgentState) -> dict:
    """
    Agent responsible for answering policy-related queries using the PDF Corpus.
    """
    record_agent_invocation("policy_agent") # Metric call
    logger.info("Policy Agent: Processing query...")
    query = state["messages"][-1].content

    try:
        vector_store = get_vector_store()

        # Retrieve the top 4 chunks with similarity scores
        results = vector_store.similarity_search_with_score(query, k=4)
        
        # Filter out retrieved documents where the similarity score does not meet a predefined threshold.
        # Note: ChromaDB returns distance by default (lower is better). 
        # A distance <= 0.75 is considered a match.
        threshold = 0.75
        docs = [doc for doc, score in results if score <= threshold]

        if not docs:
            record_fallback_event("policy_agent") # Metric call for fallback
            retries = state.get("policy_retries", 0) + 1
            from langchain_core.messages import SystemMessage
            system_note = (
                f"System Note: No policy documents matched the query with high confidence. "
                f"This is retry #{retries}. Please rewrite the query or ask the user for clarification."
            )
            if retries >= 2:
                return {
                    "messages": [SystemMessage(content=system_note)],
                    "policy_retries": retries,
                    "current_agent": "clarification_node",
                    "clarification_needed": True,
                    "policy_result": "I couldn't find specific rules regarding this in the policy manuals."
                }
            return {
                "messages": [SystemMessage(content=system_note)],
                "policy_retries": retries,
                "current_agent": "supervisor",
                "clarification_needed": False,
                "policy_result": "I couldn't find specific rules regarding this in the policy manuals."
            }

        # Format the retrieved chunks and include the PDF Source Name
        context_list = []
        for doc in docs:
            # Extract just the filename (e.g., BlueLoans4all_Topup_and_Upgrade_Policy.pdf)
            source_file = os.path.basename(doc.metadata.get("source", "Unknown Document"))
            page_num = doc.metadata.get("page", "Unknown")
            context_list.append(f"[Source: {source_file}, Page: {page_num}]\n{doc.page_content}")

        formatted_context = "\n\n---\n\n".join(context_list)
        logger.info(f"Retrieved {len(docs)} relevant policy chunks.")

        # Strict Compliance Prompt
        system_prompt = """
        You are the Chief Compliance & Policy Advisor for BlueLoans4all. 
        Answer the user's question accurately based ONLY on the provided policy context below.

        Rules:
        - Ground your response STRICTLY in the context provided.
        - Cite the specific PDF document name and page number when explaining rules.
        - If the context does not contain enough information, state clearly that the policy manuals do not cover this specific edge case.
        - Format your response cleanly using bullet points if listing out eligibility criteria or steps.

        ---
        POLICY CONTEXT:
        {context}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])

        llm = get_llm()
        rag_chain = prompt | llm | StrOutputParser()

        answer = rag_chain.invoke({"context": formatted_context, "question": query})

        return {"policy_result": answer, "current_agent": "synthesize_response"}

    except Exception as e:
        record_fallback_event("policy_agent", "system_error") # <-- METRIC: Error Fallback

        logger.error(f"Error in Policy Agent: {e}")
        return {
            "policy_result": "I am having trouble accessing the policy database right now.",
            "current_agent": "synthesize_response"
        }
