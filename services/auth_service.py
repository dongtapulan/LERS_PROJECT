from database.db_config import query_db

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

        query_db("""
            INSERT INTO users (username, password_hash, first_name, last_name, middle_initial, role, department)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, password, first_name, last_name, mi, role, dept))
        return True, "Registration successful!"