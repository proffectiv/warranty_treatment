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

load_dotenv()

# Set up secure logging
logger = setup_secure_logging('confirmation_email')

def get_brand_display_name(brand_id, options):
    """Get display text from dropdown options based on ID"""
    for option in options:
        if option['id'] == brand_id:
            return option['text']
    return 'No especificado'

def get_field_value(fields, key):
    for field in fields:
        if field['key'] == key:
            if field['type'] == 'DROPDOWN' and field['value']:
                if isinstance(field['value'], list) and len(field['value']) > 0:
                    # For all dropdown fields, get the display text from options
                    return get_brand_display_name(field['value'][0], field.get('options', []))
                return field['value']
            return field['value'] if field['value'] else 'No especificado'
    return 'No especificado'

def create_confirmation_email(form_data):
    fields = form_data['fields']
    ticket_id = form_data.get('ticket_id', 'No disponible')
    
    empresa = get_field_value(fields, 'question_59JjXb')
    nif_cif = get_field_value(fields, 'question_d0OabN')
    email = get_field_value(fields, 'question_oRq2oM')
    marca = get_field_value(fields, 'question_YG10j0')
    
    # Initialize all variables with defaults to prevent 'desconocido' returns
    modelo = 'No especificado'
    talla = 'No aplicable'
    año = 'No aplicable' 
    estado = 'No especificado'
    problema = 'No especificado'
    
    # Brand-specific fields
    if marca == 'Conway':
        modelo = get_field_value(fields, 'question_Dpjkqp')
        talla = get_field_value(fields, 'question_lOxea6')
        año = get_field_value(fields, 'question_RoAMWP')
        estado = get_field_value(fields, 'question_oRqe9M')
        problema = get_field_value(fields, 'question_GpZ9ez')
    elif marca == 'Cycplus':
        modelo = get_field_value(fields, 'question_2Apa7p')
        estado = get_field_value(fields, 'question_xDAMvG')
        problema = get_field_value(fields, 'question_RoAMkp')
        talla = 'No aplicable'
        año = 'No aplicable'
    elif marca == 'Dare':
        modelo = get_field_value(fields, 'question_GpZ952')
        talla = get_field_value(fields, 'question_OX64kp')
        año = get_field_value(fields, 'question_VPKQNE')
        estado = get_field_value(fields, 'question_P971rd')
        problema = get_field_value(fields, 'question_El2d6q')
    elif marca == 'Kogel':
        # Kogel specific handling if needed
        modelo = 'No especificado'
        talla = 'No aplicable'
        año = 'No aplicable'
        estado = 'No especificado'
        problema = 'No especificado'
    else:
        # Handle unknown brands - use defaults already set above
        logger.warning(f"Unknown brand: {marca}. Using default values.")
    
    fecha_creacion = datetime.fromisoformat(form_data['createdAt'].replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M')
    
    html_content = f"""
    <html>
    <body>
        <h2>Solicitud de Garantía Registrada Correctamente</h2>
        
        <div style="background-color: #e8f4fd; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0;">
            <h3>Número de Ticket</h3>
            <p><strong style="font-size: 18px; color: #1976D2;">{ticket_id}</strong></p>
            <p><em>Guarde este número para futuras consultas sobre su caso.</em></p>
        </div>
        
        <p>Hemos recibido correctamente su solicitud de garantía. A continuación le mostramos un resumen de la información enviada:</p>
        
        <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3>Datos de la Empresa</h3>
            <ul>
                <li><strong>Empresa:</strong> {empresa}</li>
                <li><strong>NIF/CIF/VAT:</strong> {nif_cif}</li>
                <li><strong>Email:</strong> {email}</li>
                <li><strong>Fecha de solicitud:</strong> {fecha_creacion}</li>
            </ul>
            
            <h3>Información del Producto</h3>
            <ul>
                <li><strong>Marca:</strong> {marca}</li>
                <li><strong>Modelo:</strong> {modelo}</li>
                {"<li><strong>Talla:</strong> " + talla + "</li>" if talla != 'No aplicable' else ""}
                {"<li><strong>Año de fabricación:</strong> " + año + "</li>" if año != 'No aplicable' else ""}
                <li><strong>Estado:</strong> {estado}</li>
                <li><strong>Descripción del problema:</strong> {problema}</li>
            </ul>
        </div>
        
        <p>Nuestro equipo revisará su solicitud y nos pondremos en contacto con usted lo antes posible para informarle sobre el estado de su caso y los próximos pasos a seguir.</p>
        
        <p>Si tiene alguna duda, no dude en contactarnos.</p>
        
        <br>
        <p>Saludos cordiales,<p>
        <p>El equipo de PROFFECTIV</p>
        
        <hr>
    </body>
    </html>
    """
    
    return html_content, email, empresa

def send_confirmation_email(webhook_data):
    try:
        form_data = webhook_data['data']
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
        send_confirmation_email(webhook_data)