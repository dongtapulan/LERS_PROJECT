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
        
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    flash('Invalid credentials, please try again.')
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
        flash(message)
        if success:
            return redirect(url_for('index'))
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- ADMIN ROUTES ---

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    # Keep the dashboard clean by only showing the actual 'To-Do' items (Pending)
    pending_list = ReservationService.get_all_pending()
    
    stats = query_db("""
        SELECT 
            (SELECT COUNT(*) FROM equipment) as total_equip,
            (SELECT COUNT(*) FROM reservations WHERE status = 'pending') as pending_count,
            (SELECT COUNT(*) FROM reservations WHERE status = 'approved') as active_loans
    """, one=True)
    
    return render_template('admin/dashboard.html', stats=stats, pending_reservations=pending_list)

@app.route('/admin/manage-equipment')
def manage_equipment():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    all_equipment = query_db("SELECT * FROM equipment ORDER BY equip_id DESC")
    return render_template('admin/manage_equipment.html', equipment=all_equipment)

@app.route('/admin/add-equipment', methods=['POST'])
def add_equipment():
    if session.get('role') != 'admin': 
        return redirect(url_for('index'))

    file = request.files.get('image')
    filename = secure_filename(file.filename) if file and allowed_file(file.filename) else None
    if filename: 
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    query_db("""
        INSERT INTO equipment (name, description, category, image_url, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (request.form.get('name'), request.form.get('description'), 
          request.form.get('category'), filename, 'available'))

    flash("Equipment added to inventory.")
    return redirect(url_for('manage_equipment'))

@app.route('/admin/toggle-maintenance/<int:equip_id>', methods=['GET', 'POST']) # Add methods here
def toggle_maintenance(equip_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    item = query_db("SELECT status FROM equipment WHERE equip_id = %s", (equip_id,), one=True)
    if item:
        # Toggle between available and out_of_order
        new_status = 'available' if item['status'] == 'out_of_order' else 'out_of_order'
        query_db("UPDATE equipment SET status = %s WHERE equip_id = %s", (new_status, equip_id))
        flash(f"Equipment status updated to {new_status.replace('_', ' ')}.")
    
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
        success, message = ReservationService.create_reservation(
            user_id=session['user_id'],
            equip_id=item_id,
            start_time=request.form.get('start_time'),
            end_time=request.form.get('end_time'),
            purpose=request.form.get('purpose')
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

    name = request.form.get('name')
    total_qty = int(request.form.get('total_quantity'))
    status = request.form.get('status') # 'available', 'out_of_order'
    
    # Logic: Available quantity cannot exceed total quantity
    query_db("""
        UPDATE equipment 
        SET name = %s, total_quantity = %s, status = %s,
            available_quantity = CASE WHEN %s < available_quantity THEN %s ELSE available_quantity END
        WHERE equip_id = %s
    """, (name, total_qty, status, total_qty, total_qty, equip_id))

    flash("Inventory updated successfully.")
    return redirect(url_for('manage_equipment'))

@app.route('/user/cancel-reservation/<int:res_id>')
def cancel_reservation(res_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    # Verify ownership and status
    res = query_db("SELECT status, user_id FROM reservations WHERE res_id = %s", (res_id,), one=True)
    
    if res and res['user_id'] == session['user_id'] and res['status'] == 'pending':
        # CHANGE: Update status instead of DELETE
        query_db("UPDATE reservations SET status = 'cancelled' WHERE res_id = %s", (res_id,))
        flash("Reservation cancelled successfully.")
    else:
        flash("Unable to cancel this reservation.")
        
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)