import os
from langchain_google_vertexai import ChatVertexAI
import logging

logger = logging.getLogger(__name__)

# Note: Requires GOOGLE_APPLICATION_CREDENTIALS and GCP Project configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

def get_llm():
    """
    Initializes and returns the Gemini LLM instance via Vertex AI.
    """
    try:
        llm = ChatVertexAI(
            model_name=MODEL_NAME,
            project=PROJECT_ID,
            location=LOCATION,
            temperature=0.2 # Low temperature for factual consistency
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI LLM: {e}")
        raise
