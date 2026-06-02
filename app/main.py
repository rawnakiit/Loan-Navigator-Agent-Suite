from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from app.supervisor import run_supervisor
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Loan Navigator Agent Suite API",
    description="Multi-agent system for resolving loan queries using LangGraph and Vertex AI.",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    query: str
    user_id: str = "anonymous"

class QueryResponse(BaseModel):
    response: str
    status: str
    
@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Endpoint to process natural language queries through the Supervisor Agent.
    """
    logger.info(f"Received query from user {request.user_id}: {request.query}")
    try:
        # Pass the query to the LangGraph supervisor
        result = run_supervisor(request.query)
        
        return QueryResponse(
            response=result.get("final_response", "Sorry, I couldn't process that."),
            status="success"
        )
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
