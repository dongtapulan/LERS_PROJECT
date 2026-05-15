from fpdf import FPDF
import os

class SlipGenerator:
    @staticmethod
    def generate_reservation_slip(reservation_data):
        # Set format to A5 for a smaller 'slip' feel
        pdf = FPDF(format='A5') 
        pdf.add_page()
        
        # --- Draw Border ---
        pdf.set_line_width(0.5)
        pdf.rect(5, 5, 138, 200) 
        
        # --- Header ---
        pdf.set_font("Arial", 'B', 14)
        pdf.set_y(15)
        pdf.cell(130, 10, "LERS OFFICIAL RESERVATION SLIP", ln=True, align='C')
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(130, 5, " Laboratory Dept.", ln=True, align='C')
        pdf.ln(5)
        
        pdf.line(15, 32, 133, 32)
        pdf.ln(10)

        # --- Content Section ---
        pdf.set_font("Arial", 'B', 10)
        pdf.set_x(15)
        pdf.cell(40, 8, "Reservation ID:", ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.cell(90, 8, f"{reservation_data['res_id']}", ln=1)

        pdf.set_font("Arial", 'B', 10)
        pdf.set_x(15)
        pdf.cell(40, 8, "Student Name:", ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.cell(90, 8, f"{reservation_data['full_name']}", ln=1)

        # NEW: Added Item and Quantity clearly
        pdf.set_font("Arial", 'B', 10)
        pdf.set_x(15)
        pdf.cell(40, 8, "Equipment:", ln=0)
        pdf.set_font("Arial", '', 10)
        # Showing Name and Quantity on the same line for clarity
        item_text = f"{reservation_data['equip_name']} (Qty: {reservation_data.get('requested_qty', 1)})"
        pdf.cell(90, 8, item_text, ln=1)

        pdf.ln(5)

        # --- Due Date Highlight ---
        pdf.set_fill_color(240, 240, 240) 
        pdf.set_x(15)
        pdf.set_font("Arial", 'B', 11)
        # Formatting the date for better readability
        pdf.cell(118, 10, f"DUE DATE: {reservation_data['return_date']}", border=1, ln=1, align='C', fill=True)
        pdf.ln(5)

        # --- WAIVER STATEMENT (Real-World Accountability) ---
        pdf.set_font("Arial", 'B', 9)
        pdf.set_x(15)
        pdf.cell(118, 5, "WAIVER & AGREEMENT:", ln=1)
        pdf.set_font("Arial", size=7)
        pdf.set_x(15)
        # Standard university-style liability text
        waiver_text = (
            "I hereby acknowledge receipt of the equipment listed above in good working condition. "
            "I assume full responsibility for its proper use and safekeeping. In the event of loss, "
            "damage, or late return, I agree to abide by the CTU Laboratory policies, which may include "
            "replacement costs or suspension of laboratory privileges."
        )
        pdf.multi_cell(118, 3.5, waiver_text, border=0, align='J')

        pdf.ln(10)

        # --- Signature Section ---
        pdf.set_font("Arial", size=9)
        pdf.set_x(15)
        pdf.cell(50, 10, "____________________", ln=0)
        pdf.set_x(85)
        pdf.cell(50, 10, "____________________", ln=1)
        
        pdf.set_font("Arial", 'B', 8)
        pdf.set_x(15)
        pdf.cell(50, 5, "Borrower Signature", ln=0)
        pdf.set_x(85)
        approver = reservation_data.get('approved_by_name') or "Lab Technician"
        pdf.cell(50, 5, f"Issued By: {approver}", ln=1)

        # Save
        file_path = f"static/slips/slip_{reservation_data['res_id']}.pdf"
        os.makedirs("static/slips", exist_ok=True)
        pdf.output(file_path)
        return file_path