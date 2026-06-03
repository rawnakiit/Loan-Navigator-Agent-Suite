import os
import logging
from langchain_community.vectorstores import Chroma
# from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings


logger = logging.getLogger(__name__)

# Path to the persistent ChromaDB folder you generated earlier
CHROMA_PATH = os.getenv("CHROMA_PATH", "data/chroma_db")

# Optional: Ensure GCP project is set, otherwise default credentials apply
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")


def get_vector_store():
    """
    Initializes and returns the connection to the ChromaDB vector store
    using Google Vertex AI Embeddings.
    """
    if not os.path.exists(CHROMA_PATH):
        logger.error(f"ChromaDB directory not found at {CHROMA_PATH}. Did you run the ingestion script?")
        raise FileNotFoundError(f"ChromaDB directory not found at {CHROMA_PATH}")

    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

        # Initialize Vertex AI embeddings model for retrieval
        # embeddings = VertexAIEmbeddings(
        #     model_name=EMBEDDING_MODEL,
        #     project=PROJECT_ID,
        #     location=LOCATION
        # )

        # Load existing Chroma DB from the persistent directory
        vector_store = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings
        )

        logger.info(f"Successfully connected to Chroma Vector Store at {CHROMA_PATH}")
        return vector_store

    except Exception as e:
        logger.error(f"Failed to load Vector Store: {e}")
        raise

