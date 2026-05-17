import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load variables from the .env file into the system environment (for local development)
load_dotenv()

# Check for Render's complete cloud connection URL first
CLOUD_DATABASE_URL = os.getenv('DATABASE_URL')

# Individual Database Credentials fallback for local hosting
DB_SETTINGS = {
    'dbname': os.getenv('DB_NAME', 'lers_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASS'), # No default for password for security
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

def get_connection():
    try:
        if CLOUD_DATABASE_URL:
            # If running on Render, connect directly using the single URL string
            conn = psycopg2.connect(CLOUD_DATABASE_URL)
        else:
            # If running locally, unpack individual settings
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