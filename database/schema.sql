-- LERS Database Schema
-- Last Updated: 2026-05-13

-- Drop types if they exist (useful for clean reinstalls)
DROP TYPE IF EXISTS user_role CASCADE;
DROP TYPE IF EXISTS reservation_status CASCADE;
DROP TYPE IF EXISTS equipment_status CASCADE;

-- Create Enums for strict data integrity
CREATE TYPE user_role AS ENUM ('student', 'teacher', 'admin');
CREATE TYPE reservation_status AS ENUM ('pending', 'approved', 'rejected', 'borrowed', 'returned', 'cancelled');

-- FIXED: Includes 'out_of_stock' to match your working code
CREATE TYPE equipment_status AS ENUM ('available', 'maintenance', 'out_of_stock');

-- 1. Users Table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,      -- ID Number or Email
    password_hash TEXT NOT NULL,
    
    last_name VARCHAR(50) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    middle_initial VARCHAR(2),
    
    role user_role NOT NULL,
    department VARCHAR(100),                   -- e.g., 'Information Technology'
    contact_number VARCHAR(15),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Equipment Table
CREATE TABLE equipment (
    equip_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    image_url TEXT,                            -- Filename stored in static/uploads
    
    status equipment_status DEFAULT 'available',
    total_quantity INTEGER DEFAULT 1,
    -- FIXED: Using available_quantity to match your ReservationService Python code
    available_quantity INTEGER DEFAULT 1, 
    
    added_by INTEGER REFERENCES users(user_id)
);

-- 3. Reservations Table
CREATE TABLE reservations (
    res_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    equip_id INTEGER REFERENCES equipment(equip_id) ON DELETE CASCADE,
    
    borrow_date TIMESTAMP NOT NULL,
    return_date TIMESTAMP NOT NULL,
    
    purpose TEXT,
    status reservation_status DEFAULT 'pending',
    
    -- Features for later:
    is_hidden_by_user BOOLEAN DEFAULT FALSE,   -- For "clearing" history from UI
    slip_path TEXT,                            -- Path to generated PDF slip
    processed_by INTEGER REFERENCES users(user_id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. System Logs (Audit Trail)
CREATE TABLE system_logs (
    log_id SERIAL PRIMARY KEY,
    event_type VARCHAR(50),
    description TEXT,
    user_id INTEGER REFERENCES users(user_id),
    ip_address VARCHAR(45),
    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SEED DATA (Optional: Give your teammates something to see immediately)
-- INSERT INTO equipment (name, category, description, available_quantity, total_quantity, status)
-- VALUES ('Oscilloscope', 'Electronics', 'Digital storage oscilloscope', 1, 1, 'available');