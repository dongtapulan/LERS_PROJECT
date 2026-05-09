import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Database Credentials
DB_SETTINGS = {
    'dbname': 'lers_db',
    'user': 'postgres',
    'password': '102405', 
    'host': 'localhost',
    'port': '5432'
}

def get_connection():
    try:
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
        
        # ALWAYS commit after every execute, regardless of SELECT or INSERT
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