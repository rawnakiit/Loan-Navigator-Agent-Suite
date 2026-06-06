import os
from langchain_community.utilities import SQLDatabase
import logging

logger = logging.getLogger(__name__)

# Pointing to your specific database file
DB_PATH = os.getenv("DB_PATH", "data/LoanDB_BlueLoans4all.sqlite")


def get_sql_database_tool():
    """
    Initializes and returns the LangChain SQLDatabase connection.
    This dynamically fetches the table schemas so Gemini knows exactly what columns exist.
    """
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file not found at {DB_PATH}.")
        raise FileNotFoundError(f"Database file not found at {DB_PATH}")

    try:
        # Connects to SQLite and automatically fetches the schema
        db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to SQLite DB: {e}")
        raise
