from datetime import datetime
from database.db_config import query_db

class ReservationService:
    @staticmethod
    def create_reservation(user_id, equip_id, start_time, end_time, purpose):
        # 1. Parse dates and times
        try:
            borrow_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            return_dt = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        except ValueError:
            return False, "Invalid date or time format."

        # 2. Precise Duration Check (Max 72 Hours)
        duration = return_dt - borrow_dt
        if duration.total_seconds() > (3 * 24 * 60 * 60):
            return False, "Borrowing limit exceeded. Maximum allowed is 3 days (72 hours)."
        if duration.total_seconds() < 0:
            return False, "Return time cannot be earlier than the borrow time."

        # 3. Check User's Active Reservation Limit (Max 2)
        active_count = query_db("""
            SELECT COUNT(*) as count FROM reservations 
            WHERE user_id = %s AND status IN ('pending', 'approved')
        """, (user_id,), one=True)
        
        if active_count and active_count['count'] >= 2:
            return False, "You have reached the limit of 2 active reservations."

        # 4. CRITICAL: Check Equipment Quantity and Status
        equip = query_db("""
            SELECT status, available_quantity 
            FROM equipment WHERE equip_id = %s
        """, (equip_id,), one=True)

        if not equip:
            return False, "Equipment not found."

        # Block if Admin marked as Out of Order
        if equip['status'] == 'out_of_order':
            return False, "This equipment is currently out of order for maintenance."

        # Block if no physical units are left
        if equip['available_quantity'] <= 0:
            return False, "Item is currently out of stock/all units are borrowed."

        # 5. Insert Reservation as Pending
        query_db("""
            INSERT INTO reservations (user_id, equip_id, borrow_date, return_date, purpose, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """, (user_id, equip_id, borrow_dt, return_dt, purpose))
        
        return True, "Reservation submitted successfully! Awaiting admin approval."

    @staticmethod
    def get_user_reservations(user_id):
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
                r.approved_by_name,
                e.name AS equip_name
            FROM reservations r 
            LEFT JOIN equipment e ON r.equip_id = e.equip_id 
            WHERE r.user_id = %s AND r.status != 'pending'
            ORDER BY r.created_at DESC
        """, (user_id,))

    @staticmethod
    def get_reservation_by_id(res_id):
        return query_db("""
            SELECT 
                r.*, 
                e.name as equip_name, 
                u.first_name || ' ' || u.last_name as full_name
            FROM reservations r
            JOIN equipment e ON r.equip_id = e.equip_id
            JOIN users u ON r.user_id = u.user_id
            WHERE r.res_id = %s
        """, (res_id,), one=True)