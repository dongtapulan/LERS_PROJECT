-- Create Enum for cleaner Role management
CREATE TYPE user_role AS ENUM ('student', 'teacher', 'admin');
CREATE TYPE reservation_status AS ENUM ('pending', 'approved', 'rejected', 'borrowed', 'returned', 'cancelled');
CREATE TYPE equipment_status AS ENUM ('available', 'maintenance', 'out_of_stock');

-- 1. Users Table (Students, Teachers, and Technicians)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,      -- ID Number or Email
    password_hash TEXT NOT NULL,
    
    -- Name Formatting: Last Name, First Name M.I.
    last_name VARCHAR(50) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    middle_initial VARCHAR(2),                 -- Optional
    
    role user_role NOT NULL,                   -- Admin (Tech/Staff), Teacher, or Student
    department VARCHAR(100),                   -- e.g., 'Information Technology', 'Engineering'
    contact_number VARCHAR(15),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Equipment Table
CREATE TABLE equipment (
    equip_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),                      -- e.g., 'Electronics', 'Chemicals'
    description TEXT,
    image_url TEXT,                            -- Path to file on Disk E:
    
    status equipment_status DEFAULT 'available',
    total_stock INTEGER DEFAULT 1,
    available_stock INTEGER DEFAULT 1,         -- Track actual quantity available
    
    added_by INTEGER REFERENCES users(user_id) -- Tracks which Technician added this
);

-- 3. Reservations Table (The Workflow Hub)
CREATE TABLE reservations (
    res_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    equip_id INTEGER REFERENCES equipment(equip_id) ON DELETE CASCADE,
    
    -- Schedule
    borrow_date TIMESTAMP NOT NULL,
    return_date TIMESTAMP NOT NULL,
    
    purpose TEXT,                              -- e.g., 'Class Lab Exercise 1'
    status reservation_status DEFAULT 'pending',
    
    -- Slip & Tracking
    slip_path TEXT,                            -- Location of generated PDF slip on Disk E:
    processed_by INTEGER REFERENCES users(user_id), -- The Technician who approved/rejected
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. System Logs (For "OS Awareness" and Audit Trail)
CREATE TABLE system_logs (
    log_id SERIAL PRIMARY KEY,
    event_type VARCHAR(50),
    description TEXT,
    user_id INTEGER REFERENCES users(user_id),
    ip_address VARCHAR(45),
    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);