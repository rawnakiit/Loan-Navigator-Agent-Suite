import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "data/loan_database.sqlite")

def get_db_connection():
    """
    Returns a connection to the SQLite database.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQLite DB: {e}")
        raise

def execute_query(query: str, params: tuple = ()) -> list:
    """
    Executes a read-only query against the database.
    WARNING: Ensure the query is parameterized and whitelisted in production.
    """
    # TODO: Implement SQL validation to prevent SQL injection or destructive operations
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
