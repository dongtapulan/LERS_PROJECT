import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load variables from the .env file into the system environment
load_dotenv()

# Database Credentials pulled from the OS environment for security
DB_SETTINGS = {
    'dbname': os.getenv('DB_NAME', 'lers_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASS'), # No default for password for security
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

def get_connection():
    try:
        # Pass the dictionary as keyword arguments
        conn = psycopg2.connect(**DB_SETTINGS)
        return conn
    except Exception as e:
        print(f"CRITICAL: Database connection failed. {e}")
        return None

def query_db(query, args=(), one=False):
    """Universal function to run queries, commit changes, and return results"""
    conn = get_connection()
    if not conn:
        return None
    
    # Set autocommit to False to ensure we control the transaction
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute(query, args)
        
        # Determine if it's a data-returning query
        result = None
        if cur.description:
            result = cur.fetchall()
        
        # Commit after execution to ensure data persistence
        conn.commit()
        
        if result is not None:
            return (result[0] if result else None) if one else result
        return True
            
    except Exception as e:
        print(f"Query Error: {e}")
        if conn:
            conn.rollback() 
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
