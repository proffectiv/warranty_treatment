import os
import json
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# Import logging filter from root directory
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging
from warranty_form_data import WarrantyFormData

load_dotenv()

# Set up secure logging
logger = setup_secure_logging('confirmation_email')

def set_brand_logo(form_data: WarrantyFormData):
    if form_data.brand == 'Conway':
        return "<img src='https://conwaybikes.cstatic.io/media/image/96/76/e1/conway-top-logo.png' alt='Conway Logo' style='width: auto; height: 40px; padding-bottom: 10px;'>"
    elif form_data.brand == 'Cycplus':
        return "<img src='https://www.cycplus.com/cdn/shop/files/logo_1c8cfa7d-c3c4-447d-8b41-1da8d976a77e_180x.png?v=1715742533' alt='Cycplus Logo' style='width: auto; height: 20px; padding-bottom: 10px;'>"
    elif form_data.brand == 'Dare':
        return "<img src='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSlZuL0-8gO2x88dlm4OZEMLmFUtXJJdTOGuA&s' alt='Dare Logo' style='width: auto; height: 40px; padding-bottom: 10px;'>"
    elif form_data.brand == 'Kogel':
        return "<img src='https://www.kogel.cc/cdn/shop/files/Kogel_Logo_2.svg?v=1710877689&width=270' alt='Kogel Logo' style='width: auto; height: 40px; padding-bottom: 10px;'>"
    else:
        return "<img src='https://static.wixstatic.com/media/3744a0_1a3cb44fb2dd4e029d937ba13930e693~mv2.png' alt='Proffectiv Logo' style='width: auto; height: 40px; padding-bottom: 10px;'>"

def create_confirmation_email(form_data: WarrantyFormData):
    """Create confirmation email content using WarrantyFormData object"""
    
    # Get all data from the form_data object
    data = form_data.to_dict()
    
    fecha_creacion = data['fecha_creacion']
    
    html_content = f"""
    <html>
    <body>
        <h2>Solicitud de Garantía Registrada Correctamente</h2>
        
        <div style="background-color: #e8f4fd; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0;">
            <h3>Número de Ticket</h3>
            <p><strong style="font-size: 18px; color: #1976D2;">{form_data.ticket_id}</strong></p>
            <p><em>Guarde este número para futuras consultas sobre su incidencia.</em></p>
        </div>
        
        <p>Hemos recibido correctamente su solicitud de garantía. A continuación le mostramos un resumen de la información enviada:</p>
        
        <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3>Datos de la Empresa</h3>
            <ul>
                <li><strong>Empresa:</strong> {form_data.empresa}</li>
                <li><strong>NIF/CIF/VAT:</strong> {form_data.nif_cif}</li>
                <li><strong>Email:</strong> {form_data.email}</li>
                <li><strong>Fecha de solicitud:</strong> {fecha_creacion}</li>
            </ul>
            
            <h3>Información del Producto</h3>
            <ul>
                {set_brand_logo(form_data)}
                <li><strong>Marca:</strong> {form_data.brand}</li>
                <li><strong>Modelo:</strong> {form_data.modelo}</li>
                {"<li><strong>Talla:</strong> " + form_data.talla + "</li>" if form_data.talla != 'No aplicable' else ""}
                {"<li><strong>Año de fabricación:</strong> " + form_data.año + "</li>" if form_data.año != 'No aplicable' else ""}
                <li><strong>Estado:</strong> {form_data.estado}</li>
                <li><strong>Descripción del problema:</strong> {form_data.problema}</li>
                {"<li><strong>Solución propuesta:</strong> " + form_data.solucion + "</li>" if form_data.solucion != 'No aplicable' else ""}
            </ul>
        </div>
        
        <p>Nuestro equipo revisará su solicitud y nos pondremos en contacto con usted lo antes posible para informarle sobre el estado de su incidencia</p>
        
        <p>Si tiene alguna duda, no dude en contactarnos.</p>
        
        <br>
        <p>Saludos cordiales,<p>
        <p>El equipo de PROFFECTIV</p>
        
        <hr style="margin-top: 50px;">
        <img src="https://static.wixstatic.com/media/3744a0_dbf4e7e3b00047e5ba0d6e0a1c5d41d1~mv2.png" alt="Proffectiv Logo" style="width: auto; height: 40px; padding: 20px;">
        <p>Proffectiv S.L.</p>
        <p>Crta. de Caldes, 31, 08420 Canovelles</p>
        <p>Barcelona, España</p>
        <p>NIF: B67308452</p>
    </body>
    </html>
    """
    
    return html_content, form_data.email, form_data.empresa

def send_confirmation_email(form_data: WarrantyFormData):
    """Send confirmation email to client using WarrantyFormData object"""
    try:
        html_content, client_email, empresa = create_confirmation_email(form_data)
        
        # Email configuration
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"✅ Solicitud de Garantía Registrada Correctamente"
        msg['From'] = smtp_username
        msg['To'] = client_email
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            
        logger.info(f"Confirmation email sent successfully to client")
        return True
        
    except Exception as e:
        logger.error(f"Error sending confirmation email: {str(e)}")
        return False

if __name__ == "__main__":
    # Test with sample data
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            webhook_data = json.load(f)
        form_data = WarrantyFormData(webhook_data, "test-ticket-123")
        send_confirmation_email(form_data)