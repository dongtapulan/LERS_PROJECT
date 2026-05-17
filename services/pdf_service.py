from fpdf import FPDF
import os

class SlipGenerator:
    @staticmethod
    def generate_reservation_slip(reservation_data):
        # Set format to A5 for a smaller, professional 'slip' feel
        pdf = FPDF(format='A5') 
        pdf.add_page()
        
        # --- Draw Outer Border ---
        pdf.set_line_width(0.5)
        pdf.rect(5, 5, 138, 200) 
        
        # --- Header Section ---
        pdf.set_font("Arial", 'B', 14)
        pdf.set_y(15)
        pdf.cell(130, 10, "LERS OFFICIAL RESERVATION SLIP", ln=True, align='C')
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(130, 5, "Cebu Technological University - Laboratory Dept.", ln=True, align='C')
        pdf.ln(5)
        
        # Decorative divider line
        pdf.line(15, 32, 133, 32)
        pdf.ln(8)

        # --- Reservation Details ---
        pdf.set_font("Arial", 'B', 10)
        pdf.set_x(15)
        pdf.cell(40, 7, "Reservation ID:", ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.cell(90, 7, f"RES-{reservation_data['res_id']}", ln=1)

        pdf.set_font("Arial", 'B', 10)
        pdf.set_x(15)
        pdf.cell(40, 7, "Student Name:", ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.cell(90, 7, f"{reservation_data['full_name']}", ln=1)

        pdf.set_font("Arial", 'B', 10)
        pdf.set_x(15)
        pdf.cell(40, 7, "Equipment:", ln=0)
        pdf.set_font("Arial", '', 10)
        # Explicitly showing quantity for accountability
        qty = reservation_data.get('requested_qty', 1)
        pdf.cell(90, 7, f"{reservation_data['equip_name']} (Quantity: {qty})", ln=1)

        pdf.ln(4)

        # --- Due Date Highlight ---
        pdf.set_fill_color(240, 240, 240) 
        pdf.set_x(15)
        pdf.set_font("Arial", 'B', 11)
        # Using a distinct background to ensure the return date isn't missed
        pdf.cell(118, 10, f"DUE FOR RETURN: {reservation_data['return_date']}", border=1, ln=1, align='C', fill=True)
        pdf.ln(6)

        # --- WAIVER & PENALTY SECTION ---
        pdf.set_font("Arial", 'B', 9)
        pdf.set_x(15)
        pdf.cell(118, 5, "WAIVER & TERMS OF USE:", ln=1)
        pdf.set_font("Arial", size=7.5)
        pdf.set_x(15)
        
        # Standard liability text
        waiver_text = (
            "I hereby acknowledge receipt of the equipment listed above in good working condition. "
            "I assume full responsibility for its proper use and safekeeping. I agree to return the "
            "item(s) on or before the due date specified above."
        )
        pdf.multi_cell(118, 4, waiver_text, border=0, align='J')
        pdf.ln(3)

        # Realistic Penalty Schedule
        pdf.set_font("Arial", 'B', 8)
        pdf.set_x(15)
        pdf.cell(118, 5, "PENALTY SCHEDULE:", ln=1)
        pdf.set_font("Arial", size=7.5)
        pdf.set_x(15)
        
        penalty_text = (
            "1. LATE RETURN: A fine of PHP 50.00 per day or suspension of laboratory privileges.\n"
            "2. DAMAGE: Cost of repair or 100% replacement cost if non-repairable.\n"
            "3. LOSS: Immediate replacement of the same brand/model or current market value payout.\n"
            "4. NON-COMPLIANCE: Referral to the Department Head for disciplinary action."
        )
        pdf.multi_cell(118, 4, penalty_text, border=0, align='L')

        pdf.ln(10)

        # --- Signatures ---
        pdf.set_font("Arial", size=9)
        # Student signature line
        pdf.set_x(15)
        pdf.cell(50, 10, "____________________", ln=0)
        # Admin signature line
        pdf.set_x(85)
        pdf.cell(50, 10, "____________________", ln=1)
        
        pdf.set_font("Arial", 'B', 8)
        pdf.set_x(15)
        pdf.cell(50, 5, "Borrower Signature", ln=0)
        pdf.set_x(85)
        
        # Pulls the actual tech's name if available, otherwise defaults
        approver = reservation_data.get('approved_by_name') or "Lab Technician"
        pdf.cell(50, 5, f"Issued By: {approver}", ln=1)

        # --- File Generation ---
        # Storing in static/slips for easy retrieval by the frontend
        file_name = f"slip_{reservation_data['res_id']}.pdf"
        file_path = os.path.join("static", "slips", file_name)
        
        os.makedirs("static/slips", exist_ok=True)
        pdf.output(file_path)
        return file_path