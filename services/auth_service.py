from database.db_config import query_db
import secrets
from datetime import datetime, timedelta

class AuthService:
    @staticmethod
    def authenticate(username, password):
        user = query_db("""
            SELECT * FROM users 
            WHERE username = %s AND password_hash = %s
        """, (username, password), one=True)
        return user

    @staticmethod
    def register_user(username, password, first_name, last_name, mi, role, dept):
        existing = query_db("SELECT * FROM users WHERE username = %s", (username,), one=True)
        if existing:
            return False, "ID Number already registered."

        # FIXED: Changed the accidental WHERE clause to a proper VALUES statement
        query_db("""
            INSERT INTO users (username, password_hash, first_name, last_name, middle_initial, role, department)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, password, first_name, last_name, mi, role, dept))
        return True, "Registration successful!"

    @staticmethod
    def create_password_reset_token(username):
        """
        Validates the user and generates a cryptographically secure token valid for 15 minutes.
        Supports deployment scaling by returning both the token and user record.
        """
        # Look up user details (grabbing user_id and email for deployment mail servers)
        user = query_db("SELECT user_id, username FROM users WHERE username = %s", (username,), one=True)
        if not user:
            # Defensive check against user enumeration attacks
            return False, "If the account exists, a reset link has been processed."

        user_id = user['user_id']
        
        # Generate secure URL-safe token and expiration timestamp
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=15)

        # Insert token into tracking table
        query_db("""
            INSERT INTO password_resets (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (user_id, token, expires_at))
        
        # Return success status, the token string, and the user dictionary mapping
        return True, {"token": token, "user": user}

    @staticmethod
    def verify_reset_token(token):
        """
        Validates token integrity and checks the expiration deadline window.
        """
        reset_entry = query_db("""
            SELECT user_id FROM password_resets 
            WHERE token = %s AND expires_at > %s
        """, (token, datetime.now()), one=True)
        
        return reset_entry  # Returns row dict containing user_id if valid, else None

    @staticmethod
    def reset_user_password(user_id, new_password):
        """
        Updates the target user's password string and purges active tokens to prevent reuse.
        """
        # 1. Update the password on the targeted user row
        query_db("UPDATE users SET password_hash = %s WHERE user_id = %s", (new_password, user_id))
        
        # 2. Clear out used tokens for this user (Enforce single-use token lifecycle)
        query_db("DELETE FROM password_resets WHERE user_id = %s", (user_id,))
        
        return True, "Password updated successfully!"