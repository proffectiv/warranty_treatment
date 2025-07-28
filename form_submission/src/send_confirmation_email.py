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

def get_field_value_by_name(fields, field_name):
    """Get field value using human-readable field name from new webhook structure"""
    value = fields.get(field_name)
    
    if value is None:
        return 'No especificado'
    
    # Handle different value types
    if isinstance(value, list):
        if len(value) > 0:
            # For dropdown selections, return the first value
            if isinstance(value[0], dict):
                # File upload - return file info
                return f"Archivo adjunto: {value[0].get('name', 'archivo')}"
            else:
                # Dropdown selection - return the selected value
                return str(value[0])
        else:
            return 'No especificado'
    elif isinstance(value, str):
        return value if value.strip() else 'No especificado'
    else:
        return str(value) if value else 'No especificado'

def create_confirmation_email(webhook_data):
    # Extract fields from webhook structure
    if 'fields' in webhook_data and 'fieldsById' in webhook_data:
        # GitHub action webhook structure (direct client_payload)
        fields = webhook_data['fields']
        ticket_id = webhook_data.get('ticket_id', 'No disponible')
    elif 'client_payload' in webhook_data:
        # GitHub webhook structure with client_payload
        fields = webhook_data['client_payload']['fields']
        ticket_id = webhook_data.get('ticket_id', 'No disponible')
    else:
        # Fallback to old structure if needed
        form_data = webhook_data.get('data', webhook_data)
        fields = {field['label']: field['value'] for field in form_data.get('fields', [])}
        ticket_id = form_data.get('ticket_id', 'No disponible')
    
    # Get basic info using human-readable field names
    empresa = get_field_value_by_name(fields, 'Empresa')
    nif_cif = get_field_value_by_name(fields, 'NIF/CIF/VAT')
    email = get_field_value_by_name(fields, 'Email')
    marca = get_field_value_by_name(fields, 'Marca del Producto')
    
    # Initialize all variables with defaults to prevent 'desconocido' returns
    modelo = 'No especificado'
    talla = 'No aplicable'
    año = 'No aplicable' 
    estado = 'No especificado'
    problema = 'No especificado'
    
    # Brand-specific fields using human-readable field names
    if marca == 'Conway':
        modelo = get_field_value_by_name(fields, 'Conway - Por favor, indica el nombre completo del modelo (ej. Cairon C 2.0 500)')
        talla = get_field_value_by_name(fields, 'Conway - Talla')
        año = get_field_value_by_name(fields, 'Conway - Año de fabricación')
        estado = get_field_value_by_name(fields, 'Conway - Estado de la bicicleta')
        problema = get_field_value_by_name(fields, 'Conway - Descripción del problema')
    elif marca == 'Cycplus':
        modelo = get_field_value_by_name(fields, 'Cycplus - Modelo')
        estado = get_field_value_by_name(fields, 'Cycplus - Estado del Producto')
        problema = get_field_value_by_name(fields, 'Cycplus - Descripción del problema')
        talla = 'No aplicable'
        año = 'No aplicable'
    elif marca == 'Dare':
        modelo = get_field_value_by_name(fields, 'Dare - Modelo')
        talla = get_field_value_by_name(fields, 'Dare - Talla')
        año = get_field_value_by_name(fields, 'Dare - Año de fabricación')
        estado = get_field_value_by_name(fields, 'Dare - Estado de la bicicleta')
        problema = get_field_value_by_name(fields, 'Dare - Descripción del problema')
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
    
    fecha_creacion = datetime.now().strftime('%d/%m/%Y %H:%M')
    
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
                {"<li><strong>Talla:</strong> " + str(talla) + "</li>" if talla != 'No aplicable' else ""}
                {"<li><strong>Año de fabricación:</strong> " + str(año) + "</li>" if año != 'No aplicable' else ""}
                <li><strong>Estado:</strong> {estado}</li>
                <li><strong>Descripción del problema:</strong> {problema}</li>
            </ul>
        </div>
        
        <p>Nuestro equipo revisará su solicitud y nos pondremos en contacto con usted lo antes posible para informarle sobre el estado de su incidencia</p>
        
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
        html_content, client_email, empresa = create_confirmation_email(webhook_data)
        
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