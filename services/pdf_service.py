from fpdf import FPDF
import os

class SlipGenerator:
    @staticmethod
    def generate_reservation_slip(reservation_data):
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "LERS - Equipment Reservation Slip", ln=True, align='C')
        pdf.ln(10)
        
        # Table-like content
        pdf.set_font("Arial", size=12)
        content = [
            f"Reservation ID: {reservation_data['res_id']}",
            f"Student Name: {reservation_data['full_name']}",
            f"Equipment: {reservation_data['equip_name']}",
            f"Borrow Date: {reservation_data['borrow_date']}",
            f"Return Date: {reservation_data['return_date']}",
            f"Purpose: {reservation_data['purpose']}",
            f"Status: {reservation_data['status'].upper()}"
        ]
        
        for line in content:
            pdf.cell(200, 10, line, ln=True)
            
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(200, 10, "Note: Please present this slip to the laboratory technician.", ln=True, align='C')

        # Save to a temporary folder
        file_path = f"static/slips/slip_{reservation_data['res_id']}.pdf"
        os.makedirs("static/slips", exist_ok=True)
        pdf.output(file_path)
        return file_path