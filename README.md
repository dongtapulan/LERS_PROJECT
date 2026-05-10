LERS: Laboratory Equipment Reservation System

LERS is a specialized web application developed for a University Department to manage, track, and reserve laboratory hardware. The system emphasizes physical accountability through automated document generation and strict borrowing policies.

Project Overview
LERS transitions from general scheduling to a domain-specific solution for educational technology. It handles the lifecycle of laboratory equipment—from inventory registration to maintenance and student borrowing.

Key Features
Inventory Management: Admin control for adding, editing, and deleting equipment with categorized tracking.

Smart Reservations:Automated checks for borrowing limits (max 3 days) and active reservation caps (max 2 items).

Automated Slip Generation:Generates professional PDF Reservation Slips with approval and signature lines.

System Analytics: Admin dashboard providing real-time stats on active loans and inventory health.

Technical Stack
* Backend:Python 3.13 / Flask
* Database: PostgreSQL
* Document Engine: FPDF (Portable Document Format generation)
* Environment:OS-aware configuration using `python-dotenv`

## OS Concepts & Implementation
This project was designed with core Operating System principles in mind:

Environment Isolation: Sensitive credentials (DB passwords) are abstracted into the OS environment store using `.env` files.

File System Management:The application manages persistent storage for equipment images and generated PDFs, handling OS-level pathing and directory permissions.

Concurrency Control: Utilizes Database Transactions (Commit/Rollback) to prevent race conditions during simultaneous reservations.

Network Binding:Configured for local network visibility via `0.0.0.0` binding, allowing for multi-device testing.

Installation & Setup

1.  Clone the Repository
    ```bash
    git clone [your-repo-link]
    cd LERS_PROJECT
    ```

2.  Install Dependencies
    ```bash
    pip install -r requirements.txt
    ```

3.  Environment Configuration
    Copy `.env.example` to a new file named `.env`.
    Update the `DB_PASS` and other variables to match your local PostgreSQL setup.

4.  Database Setup
    * Create a database named `lers_db` in pgAdmin or psql.
    * Run the provided `schema.sql` script to initialize the tables.

5.  Run the Application
    ```bash
    python app.py
    ```
    The system will be available at `http://localhost:8080`.

