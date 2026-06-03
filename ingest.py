import os
import logging
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# Use the modern, recommended Google GenAI embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv, find_dotenv

# Automatically find and load the .env file
env_path = find_dotenv(filename="app/.env")
if env_path:
    load_dotenv(env_path)
else:
    print("Warning: .env file not found. Relying on system environment variables.")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
CHROMA_PATH = "data/chroma_db"
DATA_PATH = "data/policy_docs"

def main():
    # --- Pre-run Checks & Diagnostics ---
    gcp_project = os.getenv("GCP_PROJECT_ID")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    
    logger.info(f"Loaded .env from: {env_path}")
    logger.info(f"Targeting GCP Project: '{gcp_project}'")
    
    if not gcp_project and not google_api_key:
         logger.error("❌ CRITICAL: No credentials found! Please set either 'GCP_PROJECT_ID' (for Vertex AI) or 'GOOGLE_API_KEY' (for Google AI Studio) in your app/.env file.")
         return
    
    # 1. Load the PDFs from the directory
    loader = PyPDFDirectoryLoader(DATA_PATH)
    documents = loader.load()
    if not documents:
        logger.error(f"❌ No PDFs found in '{DATA_PATH}'. Please ensure your files are there.")
        return
    logger.info(f"Loaded {len(documents)} pages from your policy PDFs.")

    # 2. Chunking Strategy
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, 
        chunk_overlap=200,
        separators=["\n\n", "\n", "•", ".", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Split documents into {len(chunks)} text chunks.")

    # 3. Initialize Embeddings (Using the new, stable library)
    try:
        # This uses the latest "models/text-embedding-004"
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
                                                   
    except Exception as e:
        logger.error(f"❌ Failed to initialize Google GenAI Embeddings: {e}")
        return

    # 4. Save to ChromaDB
    if os.path.exists(CHROMA_PATH):
        import shutil
        shutil.rmtree(CHROMA_PATH)
        logger.info(f"Cleared old ChromaDB at {CHROMA_PATH}")
        
    logger.info("Generating embeddings and saving to ChromaDB... This may take a minute.")
    
    vector_store = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=CHROMA_PATH
    )
    
    logger.info("✅ Ingestion Complete!")
    logger.info(f"Vector DB saved at: {CHROMA_PATH} with {vector_store._collection.count()} chunks.")

if __name__ == "__main__":
    main()

