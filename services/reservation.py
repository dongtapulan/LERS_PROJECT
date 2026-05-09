from database.db_config import query_db

class ReservationService:
    @staticmethod
    def create_reservation(user_id, equip_id, start_time, end_time, purpose):
        # 1. Double check availability
        check = query_db("SELECT status FROM equipment WHERE equip_id = %s", (equip_id,), one=True)
        if not check or check['status'] != 'available':
            return False, "Equipment is no longer available."

        # 2. FIXED: Use borrow_date and return_date to match your pgAdmin schema
        query_db("""
            INSERT INTO reservations (user_id, equip_id, borrow_date, return_date, purpose, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """, (user_id, equip_id, start_time, end_time, purpose))
        
        return True, "Reservation submitted successfully! Awaiting admin approval."

    @staticmethod
    def get_user_reservations(user_id):
        # FIXED: Updated column names to borrow_date and return_date
        return query_db("""
            SELECT 
                r.res_id, r.borrow_date, r.return_date, r.purpose, r.status, r.created_at,
                COALESCE(e.name, 'Unknown Equipment') AS equip_name, 
                COALESCE(e.category, 'General') AS category
            FROM reservations r 
            LEFT JOIN equipment e ON r.equip_id = e.equip_id 
            WHERE r.user_id = %s 
            ORDER BY r.created_at DESC
        """, (user_id,))

    @staticmethod
    def get_all_pending():
        # FIXED: Updated column names and used JOINs to match admin template requirements
        return query_db("""
            SELECT 
                r.res_id, r.user_id, r.borrow_date, r.return_date, r.purpose, r.created_at,
                u.first_name || ' ' || u.last_name AS full_name, 
                u.username AS student_id,
                e.name AS equip_name,
                e.category
            FROM reservations r
            JOIN users u ON r.user_id = u.user_id
            JOIN equipment e ON r.equip_id = e.equip_id
            WHERE r.status = 'pending'
            ORDER BY r.created_at ASC
        """)
    @staticmethod
    def get_borrowing_history(user_id):
        return query_db("""
            SELECT 
                r.res_id, r.borrow_date, r.return_date, r.purpose, r.status, r.created_at,
                e.name AS equip_name
            FROM reservations r 
            LEFT JOIN equipment e ON r.equip_id = e.equip_id 
            WHERE r.user_id = %s AND r.status != 'pending'
            ORDER BY r.created_at DESC
        """, (user_id,))
    @staticmethod
    def get_reservation_by_id(res_id):
        return query_db("""
            SELECT r.*, e.name as equip_name, u.first_name || ' ' || u.last_name as full_name
            FROM reservations r
            JOIN equipment e ON r.equip_id = e.equip_id
            JOIN users u ON r.user_id = u.user_id
            WHERE r.res_id = %s
        """, (res_id,), one=True)