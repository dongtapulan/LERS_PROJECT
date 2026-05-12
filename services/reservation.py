from datetime import datetime
from database.db_config import query_db

class ReservationService:
    @staticmethod
    def create_reservation(user_id, equip_id, start_time, end_time, purpose, requested_qty=1):
        # 1. Parse dates and times
        try:
            borrow_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            return_dt = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            return False, "Invalid date or time format."

        # 2. Duration Check
        duration = return_dt - borrow_dt
        if duration.total_seconds() > (3 * 24 * 60 * 60):
            return False, "Borrowing limit exceeded. Maximum 3 days."
        if duration.total_seconds() < 0:
            return False, "Return time cannot be earlier than borrow time."

        # 3. Active Reservation Limit Check
        active_count = query_db("""
            SELECT COUNT(*) as count FROM reservations 
            WHERE user_id = %s AND status IN ('pending', 'approved')
            AND is_hidden_by_user = FALSE
        """, (user_id,), one=True)
        
        if active_count and int(active_count['count']) >= 2:
            return False, "You have reached the limit of 2 active reservations."

        # 4. Fetch State
        equip = query_db("SELECT status, available_quantity FROM equipment WHERE equip_id = %s", (equip_id,), one=True)
        if not equip:
            return False, "Equipment not found."

        current_qty = int(equip['available_quantity'])
        req_qty = int(requested_qty) 

        # 6. Logic Calculation
        new_quantity = current_qty - req_qty
        
        # CHANGED: 'unavailable' -> 'out_of_stock'
        # This is the most common ENUM value for zero-quantity items.
        new_status = 'out_of_stock' if new_quantity == 0 else 'available'

        try:
            # 7. Update Equipment
            query_db("""
                UPDATE equipment 
                SET available_quantity = %s, status = %s 
                WHERE equip_id = %s
            """, (new_quantity, new_status, equip_id))

            # 8. Record Reservation
            query_db("""
                INSERT INTO reservations (user_id, equip_id, borrow_date, return_date, purpose, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (user_id, equip_id, borrow_dt, return_dt, purpose))
            
            return True, "Reservation submitted successfully!"
            
        except Exception as e:
            print(f"Database Error: {e}")
            return False, "System error during resource allocation."
    
    @staticmethod
    def get_user_reservations(user_id):
        """Fetches active and recently updated reservations that HAVE NOT been dismissed by the student"""
        return query_db("""
            SELECT 
                r.res_id, r.borrow_date, r.return_date, r.purpose, r.status, r.created_at,
                COALESCE(e.name, 'Unknown Equipment') AS equip_name, 
                COALESCE(e.category, 'General') AS category
            FROM reservations r 
            LEFT JOIN equipment e ON r.equip_id = e.equip_id 
            WHERE r.user_id = %s AND r.is_hidden_by_user = FALSE
            ORDER BY r.created_at DESC
        """, (user_id,))

    @staticmethod
    def get_all_for_admin():
        """Returns ALL reservations (including cancelled) so professors have an audit trail"""
        return query_db("""
            SELECT 
                r.res_id, r.user_id, r.borrow_date, r.return_date, r.purpose, r.created_at, r.status,
                u.first_name || ' ' || u.last_name AS full_name, 
                u.username AS student_id,
                e.name AS equip_name,
                e.category
            FROM reservations r
            JOIN users u ON r.user_id = u.user_id
            JOIN equipment e ON r.equip_id = e.equip_id
            ORDER BY r.created_at DESC
        """)

    @staticmethod
    def get_all_pending():
        """Used for the Admin's 'To-Do' list - Filters out items the admin has hidden"""
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
            WHERE r.status = 'pending' AND r.is_hidden_by_admin = FALSE
            ORDER BY r.created_at ASC
        """)

    @staticmethod
    def get_borrowing_history(user_id):
        """Shows the student their past finalized activity"""
        return query_db("""
            SELECT 
                r.res_id, r.borrow_date, r.return_date, r.purpose, r.status, r.created_at,
                r.approved_by_name,
                e.name AS equip_name
            FROM reservations r 
            LEFT JOIN equipment e ON r.equip_id = e.equip_id 
            WHERE r.user_id = %s AND r.status NOT IN ('pending')
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
    
    @staticmethod
    def cancel_reservation(reservation_id):
        # 1. Get the reservation details first
        res = query_db("SELECT equip_id, status FROM reservations WHERE res_id = %s", (reservation_id,), one=True)
        if not res:
            return False, "Reservation not found."
        
        # Only allow cancellation of 'pending' or 'approved' reservations
        if res['status'] not in ['pending', 'approved']:
            return False, "This reservation cannot be cancelled."

        equip_id = res['equip_id']

        try:
            # 2. Update the Equipment (Return the stock)
            # We increment the quantity and set status back to 'available'
            query_db("""
                UPDATE equipment 
                SET available_quantity = available_quantity + 1,
                    status = 'available'
                WHERE equip_id = %s
            """, (equip_id,))

            # 3. Update the Reservation status
            # We mark it as 'cancelled' instead of deleting it so the Admin can still see the history
            query_db("UPDATE reservations SET status = 'cancelled' WHERE res_id = %s", (reservation_id,))

            return True, "Reservation cancelled and equipment restocked."
            
        except Exception as e:
            print(f"Cancellation Error: {e}")
            return False, "System error during cancellation."