from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from app.supervisor import run_supervisor
import logging

# ====================================================================
# GOOGLE CLOUD OPERATIONS SUITE (LOGGING & MONITORING) INTEGRATION
# ====================================================================
try:
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler
    
    log_client = google.cloud.logging.Client()
    cloud_handler = CloudLoggingHandler(log_client)
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logging.getLogger().addHandler(cloud_handler)
    logging.info("Backend Boot: Successfully attached Google Cloud Logging!")
except Exception as e:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.warning(f"Running backend with standard local logging. GCP logger not attached: {e}")

logger = logging.getLogger(__name__)

import os
from dotenv import load_dotenv, find_dotenv

# --- CRITICAL FIX: Load environment variables first ---
# This ensures GOOGLE_API_KEY is available to all agents
env_path = find_dotenv(filename="app/.env")
if env_path:
    load_dotenv(env_path)
else:
    # Fallback in case running from the app directory directly
    load_dotenv(find_dotenv(filename=".env"))
# ------------------------------------------------------

from app.supervisor import run_supervisor

# The rest of your FastAPI code remains exactly the same below...
# app = FastAPI(title="Loan Navigator Agent Suite API")


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
    
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Validates the incoming X-API-Key against Google Secret Manager/Env config."""
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        logger.warning("API_KEY environment variable is not set. Allowing request in local mock mode.")
        return None
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Could not validate credentials: Invalid X-API-Key.")
    return api_key

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, api_key: str = Depends(verify_api_key)):
    """
    Endpoint to process natural language queries through the Supervisor Agent.
    """
    logger.info(f"Received query from user {request.user_id}: {request.query}")
    try:
        # Pass the query to the LangGraph supervisor
        result = run_supervisor(request.query)
        
        status = "success"
        if result.get("clarification_needed"):
            status = "clarification_needed"

        return QueryResponse(
            response=result.get("final_response", "Sorry, I couldn't process that."),
            status=status
        )
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# # uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
