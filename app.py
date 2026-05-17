from flask import Flask, render_template, request, redirect, url_for, session, flash
from database.db_config import query_db
from services.reservation import ReservationService
from services.auth_service import AuthService
from werkzeug.utils import secure_filename
from flask import send_file
from services.pdf_service import SlipGenerator
import os

app = Flask(__name__)
app.secret_key = 'lers_secret_key_2026'

UPLOAD_FOLDER = 'static/uploads/equipment'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def process_inventory_restock(res_id, new_status):
    """
    Core logic to return items to the shelf and update the slip status.
    """
    res = query_db("SELECT equip_id, requested_qty FROM reservations WHERE res_id = %s", (res_id,), one=True)
    
    if res:
        # 1. Update the SLIP status (e.g., to 'cancelled' or 'returned')
        query_db("UPDATE reservations SET status = %s WHERE res_id = %s", (new_status, res_id))
        
        # 2. Update the EQUIPMENT table
        # We add the quantity and force status to 'available' since we are restocking
        query_db("""
            UPDATE equipment 
            SET available_quantity = available_quantity + %s,
                status = 'available'
            WHERE equip_id = %s
        """, (res['requested_qty'], res['equip_id']))
        
        print(f"Inventory Sync: Restored {res['requested_qty']} units to Equip ID {res['equip_id']}")
        return True
        
    return False

# --- AUTH ROUTES ---

@app.route('/')
def index():
    # If the user is logged in, redirect them to their respective dashboard
    if 'user_id' in session and 'role' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    # Otherwise, clear session to prevent ghost logins and show login page
    session.clear()
    return render_template('auth/login.html')
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = AuthService.authenticate(username, password)
    
    if user:
        session['user_id'] = int(user['user_id'])
        session['role'] = str(user['role'])
        session['full_name'] = f"{user['first_name']} {user['last_name']}"
        
        # Add a success message here
        flash(f"Welcome back, {user['first_name']}!", "success")
        
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    # Use 'danger' category for errors
    flash('Invalid credentials, please try again.', "danger")
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        success, message = AuthService.register_user(
            request.form.get('username'),
            request.form.get('password'),
            request.form.get('first_name'),
            request.form.get('last_name'),
            request.form.get('mi'),
            request.form.get('role'),
            request.form.get('department')
        )
        
        # 1. Determine the category based on the success boolean
        category = "success" if success else "danger"
        
        # 2. Flash the message with its specific category
        flash(message, category)
        
        if success:
            # Redirect to login page or index after a successful account creation
            return redirect(url_for('index'))
            
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- ADMIN ROUTES ---
@app.route('/admin/confirm-return/<int:res_id>')
def confirm_return(res_id):
    # Security check: Ensure only admins/techs can run this
    if session.get('role') != 'admin':
        flash("Unauthorized access.")
        return redirect(url_for('index'))
    
    # Admins usually return items that are 'approved' or 'borrowed'
    res = query_db("SELECT status FROM reservations WHERE res_id = %s", (res_id,), one=True)
    
    if res and res['status'] in ['approved', 'borrowed']:
        if process_inventory_restock(res_id, 'returned'):
            flash("Item successfully returned to inventory.")
        else:
            flash("Error processing return.")
    else:
        flash("This reservation cannot be returned (it may already be returned or cancelled).")
        
    # Redirect back to wherever your admin manages reservations
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    # NEW: Fetch everything that isn't 'cancelled' or 'returned' 
    # so the Admin can see both Pending and currently Active loans
    active_items = ReservationService.get_active_admin_list()
    
    stats = query_db("""
        SELECT 
            (SELECT COUNT(*) FROM equipment) as total_equip,
            (SELECT COUNT(*) FROM reservations WHERE status = 'pending') as pending_count,
            (SELECT COUNT(*) FROM reservations WHERE status = 'approved') as active_loans
    """, one=True)
    
    # Update the template variable name to reflect the new combined list
    return render_template('admin/dashboard.html', stats=stats, active_reservations=active_items)

@app.route('/admin/manage-equipment')
def manage_equipment():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    # System Monitor: Fetching the current state of all hardware resources
    all_equipment = query_db("SELECT * FROM equipment ORDER BY equip_id DESC")
    return render_template('admin/manage_equipment.html', equipment=all_equipment)

@app.route('/admin/add-equipment', methods=['POST'])
def add_equipment():
    if session.get('role') != 'admin': 
        return redirect(url_for('index'))

    # Resource Allocation: Define total capacity for this equipment type
    # We grab total_quantity from the form. If not provided, default to 1.
    try:
        total_qty = int(request.form.get('total_quantity', 1))
    except (ValueError, TypeError):
        total_qty = 1

    # OS-Aware Constraint: Bounded Buffer (Preventing system overflow)
    if total_qty > 50:
        flash("Error: Quantity exceeds laboratory capacity limit (Max 50).")
        return redirect(url_for('manage_equipment'))

    file = request.files.get('image')
    filename = secure_filename(file.filename) if file and allowed_file(file.filename) else None
    if filename: 
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Fix: Set available_quantity = total_quantity so it shows as 6/6, not 1/1
    query_db("""
        INSERT INTO equipment (name, description, category, image_url, total_quantity, available_quantity, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (request.form.get('name'), request.form.get('description'), 
          request.form.get('category'), filename, total_qty, total_qty, 'available'))

    flash(f"Equipment added to inventory with {total_qty} units available.")
    return redirect(url_for('manage_equipment'))

@app.route('/admin/toggle-maintenance/<int:equip_id>', methods=['GET', 'POST'])
def toggle_maintenance(equip_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    item = query_db("SELECT status, available_quantity FROM equipment WHERE equip_id = %s", (equip_id,), one=True)
    if item:
        # State Machine Logic:
        # If we restore an item from maintenance, we must check if it was previously 'fully_reserved'
        if item['status'] == 'out_of_order':
            # If units are > 0, it's available. If 0, it stays fully_reserved.
            new_status = 'available' if item['available_quantity'] > 0 else 'fully_reserved'
        else:
            # Manual override to lock the resource regardless of quantity
            new_status = 'out_of_order'
            
        query_db("UPDATE equipment SET status = %s WHERE equip_id = %s", (new_status, equip_id))
        flash(f"System State Update: Equipment is now {new_status.replace('_', ' ')}.")
    
    return redirect(url_for('manage_equipment'))

@app.route('/admin/reservations')
def admin_pending_reservations():
    if session.get('role') != 'admin': 
        return redirect(url_for('index'))
    
    # CHANGE: Use get_all_for_admin() instead of get_all_pending()
    # This ensures 'cancelled' and 'rejected' items also appear in the list
    all_activity = ReservationService.get_all_for_admin()
    
    return render_template('admin/pending_reservations.html', reservations=all_activity)

@app.route('/admin/reservation/<int:res_id>/<action>')
def update_reservation(res_id, action):
    if session.get('role') != 'admin': 
        return redirect(url_for('index'))

    new_status = 'approved' if action == 'approve' else 'rejected'
    query_db("UPDATE reservations SET status = %s WHERE res_id = %s", (new_status, res_id))
    
    if new_status == 'approved':
        query_db("""
            UPDATE equipment SET status = 'borrowed' 
            WHERE equip_id = (SELECT equip_id FROM reservations WHERE res_id = %s)
        """, (res_id,))

    flash(f"Reservation {new_status} successfully!")
    return redirect(url_for('admin_pending_reservations'))
# --- ADMIN REPORT & OS INTEGRATION ---
@app.route('/admin/reports')
def admin_reports():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    # Fetching fresh stats for the report
    stats = query_db("""
        SELECT 
            (SELECT COUNT(*) FROM equipment) as total_equip,
            (SELECT COUNT(*) FROM users WHERE role != 'admin') as total_users,
            (SELECT COUNT(*) FROM reservations WHERE status = 'approved') as active_loans,
            (SELECT COUNT(*) FROM reservations WHERE status = 'rejected') as rejected_total
    """, one=True)
    
    return render_template('admin/reports.html', stats=stats)

# --- USER MANAGEMENT ---
@app.route('/admin/users')
def user_management():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    users_list = query_db("SELECT user_id, username, first_name, last_name, role, department FROM users ORDER BY role DESC")
    return render_template('admin/user_management.html', users=users_list)

# --- USER ROUTES ---

@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') not in ['student', 'teacher']: 
        return redirect(url_for('index'))
    
    # Updated query to calculate "effective_qty" by subtracting pending reservations
    equipment_list = query_db("""
        SELECT e.*, 
        (e.available_quantity - (
            SELECT COUNT(*) FROM reservations r 
            WHERE r.equip_id = e.equip_id AND r.status = 'pending'
        )) as effective_qty
        FROM equipment e
    """)
    
    return render_template('user/dashboard.html', equipment=equipment_list, name=session.get('full_name'))

@app.route('/user/my-reservations')
def my_reservations():
    if 'user_id' not in session: 
        return redirect(url_for('index'))
    user_res = ReservationService.get_user_reservations(session['user_id'])
    return render_template('user/my_reservations.html', reservations=user_res)

@app.route('/reserve/<int:item_id>', methods=['GET', 'POST'])
def reserve(item_id):
    if 'user_id' not in session: 
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Extract the requested quantity from the form
        requested_qty = int(request.form.get('quantity', 1))

        success, message = ReservationService.create_reservation(
            user_id=session['user_id'],
            equip_id=item_id,
            start_time=request.form.get('start_time'),
            end_time=request.form.get('end_time'),
            purpose=request.form.get('purpose'),
            requested_qty=requested_qty
        )
        flash(message)
        return redirect(url_for('user_dashboard'))

    item = query_db("SELECT * FROM equipment WHERE equip_id = %s", (item_id,), one=True)
    return render_template('user/reserve.html', item=item)

@app.route('/user/history')
def borrowing_history():
    if 'user_id' not in session: 
        return redirect(url_for('index'))
    history = ReservationService.get_borrowing_history(session['user_id'])
    return render_template('user/history.html', history=history)

@app.route('/download-slip/<int:res_id>')
def download_slip(res_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    res_data = ReservationService.get_reservation_by_id(res_id)
    
    # Security check: only the owner or an admin can download
    if session['role'] != 'admin' and res_data['user_id'] != session['user_id']:
        return "Unauthorized", 403
        
    pdf_path = SlipGenerator.generate_reservation_slip(res_data)
    return send_file(pdf_path, as_attachment=True)

@app.route('/admin/delete-equipment/<int:equip_id>')
def delete_equipment(equip_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    # Optional: Delete the image file from the folder as well
    item = query_db("SELECT image_url FROM equipment WHERE equip_id = %s", (equip_id,), one=True)
    if item and item['image_url']:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], item['image_url']))
        except:
            pass # File might already be gone

    query_db("DELETE FROM equipment WHERE equip_id = %s", (equip_id,))
    flash("Equipment successfully removed from inventory.")
    return redirect(url_for('manage_equipment'))

@app.route('/admin/reservation/<int:res_id>/approve', methods=['POST'])
def approve_reservation(res_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    approver_name = request.form.get('approver_name') # Input from admin
    
    # Update Reservation
    query_db("""
        UPDATE reservations 
        SET status = 'approved', approved_by_name = %s 
        WHERE res_id = %s
    """, (approver_name, res_id))

    # Decrease Quantity & Update Status if empty
    res = query_db("SELECT equip_id FROM reservations WHERE res_id = %s", (res_id,), one=True)
    query_db("""
        UPDATE equipment 
        SET available_quantity = available_quantity - 1,
            status = CASE WHEN available_quantity - 1 <= 0 THEN 'borrowed'::equipment_status ELSE 'available'::equipment_status END
        WHERE equip_id = %s
    """, (res['equip_id'],))

    flash(f"Approved by {approver_name}. Inventory updated.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit-equipment/<int:equip_id>', methods=['POST'])
def edit_equipment(equip_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    # Read form inputs from the row
    name = request.form.get('name')
    status = request.form.get('status') # 'available', 'out_of_order'
    
    new_avail = int(request.form.get('available_quantity'))
    total_qty = int(request.form.get('total_quantity'))

    # CRITICAL SECURITY CHECK: Available stock cannot physically exceed total inventory capacity
    if new_avail > total_qty:
        flash(f"Error: Available quantity ({new_avail}) cannot exceed total stock ({total_qty})!", "danger")
        return redirect(url_for('manage_equipment'))
        
    if new_avail < 0:
        flash("Error: Available quantity cannot be negative.", "danger")
        return redirect(url_for('manage_equipment'))

    # If the admin manually sets available stock to 0, automatically flag status as fully reserved/unavailable
    # unless it's already explicitly marked as 'out_of_order'
    if new_avail == 0 and status != 'out_of_order':
        status = 'fully_reserved'
    elif new_avail > 0 and status == 'fully_reserved':
        status = 'available'

    # Update database row
    query_db("""
        UPDATE equipment 
        SET name = %s, total_quantity = %s, available_quantity = %s, status = %s
        WHERE equip_id = %s
    """, (name, total_qty, new_avail, status, equip_id))

    flash("Inventory pool capacity adjusted successfully.", "success")
    return redirect(url_for('manage_equipment'))

@app.route('/user/cancel-reservation/<int:res_id>')
def cancel_reservation(res_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    # Verify ownership and that it is still 'pending'
    res = query_db("SELECT status, user_id FROM reservations WHERE res_id = %s", (res_id,), one=True)
    
    if res and res['user_id'] == session['user_id'] and res['status'] == 'pending':
        if process_inventory_restock(res_id, 'cancelled'):
            flash("Reservation cancelled. Inventory restocked.")
        else:
            flash("Error updating inventory.")
    else:
        flash("Unauthorized or invalid request.")
        
    return redirect(url_for('my_reservations'))

@app.route('/hide-reservation/<int:res_id>')
def hide_reservation(res_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # 1. Update the database visibility flag
        if session.get('is_admin'):
            query_db("UPDATE reservations SET is_hidden_by_admin = TRUE WHERE res_id = %s", (res_id,))
            flash("Reservation dismissed from admin view.", "success")
            return redirect(url_for('admin_reservations')) # Redirect to admin list
        else:
            # We check user_id here for security so students can't hide other students' data
            query_db("UPDATE reservations SET is_hidden_by_user = TRUE WHERE res_id = %s AND user_id = %s", 
                     (res_id, session['user_id']))
            flash("Reservation cleared from your list.", "success")
            return redirect(url_for('my_reservations')) # Redirect to student list
            
    except Exception as e:
        print(f"Error hiding reservation: {e}")
        flash("Could not dismiss reservation. Please try again.", "error")
        return redirect(request.referrer or url_for('user_dashboard'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        
        # Call the updated hybrid-ready service layer
        success, data = AuthService.create_password_reset_token(username)
        
        if success:
            # Unpack the dictionary bundle safely
            token = data["token"]
            user_info = data["user"]
            
            # Dynamically build the external absolute URL pointing to your reset endpoint
            reset_link = url_for('reset_password', token=token, _external=True)
            
            # --- LOCAL SIMULATION LOGGING CHANNEL ---
            print(f"\n--- SIMULATED SYSTEM EMAIL ---")
            print(f"User ID / Account: {user_info['username']}")
            print(f"Reset URL Link: {reset_link}")
            print(f"------------------------------\n")
            
            flash("Password reset link has been generated! Check terminal console logs.", "info")
            
            # --- PRODUCTION LIVE DEPLOYMENT CHANNEL ---
            # Once you configure an SMTP server (like Gmail App Passwords or SendGrid) later,
            # you can comment out the print statements above and uncomment the lines below:
            #
            # send_production_email(recipient=f"{user_info['username']}@student.ctu.edu.ph", link=reset_link)
            # flash("An authenticated recovery link has been dispatched to your institutional email.", "info")
            
        else:
            # If user search fails, 'data' contains the defensive security string
            flash(data, "info")
            
        return redirect(url_for('index'))
        
    return render_template('auth/forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Call the service layer to confirm token validity
    reset_entry = AuthService.verify_reset_token(token)
    
    if not reset_entry:
        flash("Invalid or expired password reset token.", "danger")
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return render_template('auth/reset_password.html', token=token)
            
        # Execute password modification and consumption step via service
        AuthService.reset_user_password(reset_entry['user_id'], new_password)
        
        flash("Password updated successfully! You can now log in.", "success")
        return redirect(url_for('index'))
        
    return render_template('auth/reset_password.html', token=token)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)