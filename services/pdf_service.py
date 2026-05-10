from fpdf import FPDF
import os
from datetime import datetime

class SlipGenerator:
    @staticmethod
    def generate_reservation_slip(reservation_data):
        # Set format to A5 for a smaller 'slip' feel
        pdf = FPDF(format='A5') 
        pdf.add_page()
        
        # --- Draw Border ---
        # Draw a rectangle slightly smaller than the page (A5 is ~148x210mm)
        pdf.set_line_width(0.5)
        pdf.rect(5, 5, 138, 200) 
        
        # --- Header ---
        pdf.set_font("Arial", 'B', 14)
        pdf.set_y(15)
        pdf.cell(130, 10, "LERS RESERVATION SLIP", ln=True, align='C')
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(130, 5, "Cebu Technological University - Laboratory Dept.", ln=True, align='C')
        pdf.ln(5)
        
        # Draw a horizontal line under header
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

        pdf.set_font("Arial", 'B', 10)
        pdf.set_x(15)
        pdf.cell(40, 8, "Equipment Item:", ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.cell(90, 8, f"{reservation_data['equip_name']}", ln=1)

        pdf.ln(5)

        # --- Due Date Highlight ---
        pdf.set_fill_color(240, 240, 240) # Light grey background
        pdf.set_x(15)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(118, 10, f"RETURN BY: {reservation_data['return_date']}", border=1, ln=1, align='C', fill=True)
        pdf.ln(10)

        # --- Policies ---
        pdf.set_font("Arial", 'B', 9)
        pdf.set_x(15)
        pdf.cell(118, 5, "REMINDERS:", ln=1)
        pdf.set_font("Arial", size=8)
        pdf.set_x(15)
        pdf.multi_cell(118, 4, "- Max 3-day borrowing limit strictly enforced.\n"
                               "- Items must be returned in original condition.\n"
                               "- Late returns result in temporary suspension of lab privileges.")

        pdf.ln(15)

        # --- Signature Section ---
        pdf.set_font("Arial", size=9)
        # Student signature
        pdf.set_x(15)
        pdf.cell(50, 10, "____________________", ln=0)
        # Admin signature area
        pdf.set_x(85)
        pdf.cell(50, 10, "____________________", ln=1)
        
        pdf.set_font("Arial", 'B', 8)
        pdf.set_x(15)
        pdf.cell(50, 5, "Student Signature", ln=0)
        pdf.set_x(85)
        # Using the name provided during approval
        approver = reservation_data.get('approved_by_name') or "Lab Technician"
        pdf.cell(50, 5, f"Approved By: {approver}", ln=1)

        # Save
        file_path = f"static/slips/slip_{reservation_data['res_id']}.pdf"
        os.makedirs("static/slips", exist_ok=True)
        pdf.output(file_path)
        return file_path