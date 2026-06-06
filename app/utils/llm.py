import os
from langchain_google_genai import ChatGoogleGenerativeAI
import logging

logger = logging.getLogger(__name__)

# Note: Requires GOOGLE_APPLICATION_CREDENTIALS and GCP Project configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def get_llm():
    """
    Initializes and returns the Gemini LLM instance.
    Defaults to ChatGoogleGenerativeAI with Vertex AI in production (GCP), with a graceful fallback 
    to ChatGoogleGenerativeAI (Google AI Studio) if GCP_PROJECT_ID is not configured.
    """
    try:
        if PROJECT_ID:
            logger.info("Initializing ChatGoogleGenerativeAI with Vertex AI backend for GCP production...")
            return ChatGoogleGenerativeAI(
                model=MODEL_NAME,
                project=PROJECT_ID,
                location=LOCATION,
                vertexai=True,
                temperature=0.2  # Low temperature for factual consistency
            )
        else:
            logger.info("GCP_PROJECT_ID not set. Initializing ChatGoogleGenerativeAI for local dev...")
            return ChatGoogleGenerativeAI(
                model=MODEL_NAME,
                temperature=0.2
            )
    except Exception as e:
        logger.error(f"Failed to initialize LLM client: {e}")
        raise
