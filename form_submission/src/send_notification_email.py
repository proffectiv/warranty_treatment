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
logger = setup_secure_logging('notification_email')

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

def create_notification_email(form_data):
    fields = form_data['fields']
    ticket_id = form_data.get('ticket_id', 'No disponible')
    
    empresa = get_field_value(fields, 'question_59JjXb')
    nif_cif = get_field_value(fields, 'question_d0OabN')
    email = get_field_value(fields, 'question_oRq2oM')
    marca = get_field_value(fields, 'question_YG10j0')
    
    # Initialize all variables with defaults
    modelo = 'No especificado'
    talla = 'No aplicable'
    año = 'No aplicable'
    estado = 'No especificado'
    problema = 'No especificado'
    solucion = 'No aplicable'
    factura_compra = 'No'
    factura_venta = 'No'
    
    # Brand-specific fields
    if marca == 'Conway':
        modelo = get_field_value(fields, 'question_Dpjkqp')
        talla = get_field_value(fields, 'question_lOxea6')
        año = get_field_value(fields, 'question_RoAMWP')
        estado = get_field_value(fields, 'question_oRqe9M')
        problema = get_field_value(fields, 'question_GpZ9ez')
        solucion = get_field_value(fields, 'question_OX64QA')
        factura_compra = 'Sí' if get_field_value(fields, 'question_VPKQpl') != 'No especificado' else 'No'
        factura_venta = 'Sí' if get_field_value(fields, 'question_P971R0') != 'No especificado' else 'No'
    elif marca == 'Cycplus':
        modelo = get_field_value(fields, 'question_2Apa7p')
        estado = get_field_value(fields, 'question_xDAMvG')
        problema = get_field_value(fields, 'question_RoAMkp')
        factura_compra = 'Sí' if get_field_value(fields, 'question_GpZlqz') != 'No especificado' else 'No'
        factura_venta = 'Sí' if get_field_value(fields, 'question_oRqevX') != 'No especificado' else 'No'
        talla = 'No aplicable'
        año = 'No aplicable'
        solucion = 'No aplicable'
        
    elif marca == 'Dare':
        modelo = get_field_value(fields, 'question_GpZ952')
        talla = get_field_value(fields, 'question_OX64kp')
        año = get_field_value(fields, 'question_VPKQNE')
        estado = get_field_value(fields, 'question_P971rd')
        problema = get_field_value(fields, 'question_El2d6q')
        solucion = get_field_value(fields, 'question_rOeaY5')
        factura_compra = 'Sí' if get_field_value(fields, 'question_OX6GbA') != 'No especificado' else 'No'
        factura_venta = 'Sí' if get_field_value(fields, 'question_47MJOB') != 'No especificado' else 'No'
    else:
        # Handle unknown brands or missing brand info - use defaults already set above
        logger.warning(f"Unknown brand: {marca}. Using default values.")
    
    fecha_creacion = datetime.fromisoformat(form_data['createdAt'].replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M')

    style = """
    <style>
        body {
            color: #000000;
        }
    </style>
    """
    
    html_content = f"""
    <html>
    {style}
    <body>
        <h2>🚨 Nueva Solicitud de Garantía Recibida</h2>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #1976D2; margin: 20px 0;">
            <h3>🎫 Ticket de Garantía</h3>
            <p><strong style="font-size: 18px; color: #1976D2;">Ticket ID: {ticket_id}</strong></p>
        </div>
        
        <div style="background-color: #e8f4fd; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0;">
            <h3>📋 Información General</h3>
            <ul>
                <li><strong>Fecha y Hora:</strong> {fecha_creacion}</li>
                <li><strong>Empresa:</strong> {empresa}</li>
                <li><strong>NIF/CIF/VAT:</strong> {nif_cif}</li>
                <li><strong>Email:</strong> {email}</li>
            </ul>
        </div>
        
        <div style="background-color: #fff3e0; padding: 15px; border-left: 4px solid #FF9800; margin: 20px 0;">
            <h3>🛠️ Información del Producto</h3>
            <ul>
                <li><strong>Marca:</strong> {marca}</li>
                <li><strong>Modelo:</strong> {modelo}</li>
                {"<li><strong>Talla:</strong> " + talla + "</li>" if talla != 'No aplicable' else ""}
                {"<li><strong>Año de fabricación:</strong> " + año + "</li>" if año != 'No aplicable' else ""}
                <li><strong>Estado del producto:</strong> {estado}</li>
            </ul>
        </div>
        
        <div style="background-color: #ffebee; padding: 15px; border-left: 4px solid #f44336; margin: 20px 0;">
            <h3>⚠️ Problema Reportado</h3>
            <p><strong>{problema}</strong></p>
            {"<h4>💡 Solución Propuesta:</h4><p>" + solucion + "</p>" if solucion != 'No aplicable' and solucion != 'No especificado' else ""}
        </div>
        
        <div style="background-color: #f3e5f5; padding: 15px; border-left: 4px solid #9c27b0; margin: 20px 0;">
            <h3>📄 Documentación</h3>
            <ul>
                <li><strong>Factura de compra:</strong> {factura_compra}</li>
                <li><strong>Factura de venta:</strong> {factura_venta}</li>
            </ul>
        </div>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-left: 4px solid #4caf50; margin: 20px 0;">
            <h3>✅ Acciones Realizadas</h3>
            <ul>
                <li>✓ Email de confirmación enviado al cliente</li>
                <li>✓ Registro añadido al archivo de Excel en Dropbox</li>
                <li>✓ Notificación de nuevo ticket generada</li>
            </ul>
        </div>
        
        <hr>
        <p><strong>👉 Próximos pasos:</strong></p>
        <ol>
            <li>Revisar la solicitud de garantía</li>
            <li>Evaluar la documentación adjunta</li>
            <li>Contactar con el cliente para dar seguimiento</li>
            <li>Actualizar el estado en el sistema de seguimiento</li>
        </ol>
        
        <p>Este mensaje ha sido generado automáticamente por el sistema de gestión de garantías.</p>
    </body>
    </html>
    """
    
    return html_content

def send_notification_email(webhook_data):
    try:
        form_data = webhook_data['data']
        html_content = create_notification_email(form_data)
        
        # Email configuration
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        notification_email = os.getenv('NOTIFICATION_EMAIL')
        
        # Debug email configuration
        logger.info(f"Email config - Host: {smtp_host}, Port: {smtp_port}, Notification email: {notification_email}")
        
        # Check for missing configuration
        if not all([smtp_host, smtp_port, smtp_username, smtp_password, notification_email]):
            missing = [k for k, v in {
                'SMTP_HOST': smtp_host,
                'SMTP_PORT': smtp_port, 
                'SMTP_USERNAME': smtp_username,
                'SMTP_PASSWORD': smtp_password,
                'NOTIFICATION_EMAIL': notification_email
            }.items() if not v]
            raise Exception(f"Missing email configuration: {missing}")
        
        empresa = None
        for field in form_data['fields']:
            if field['key'] == 'question_59JjXb':
                empresa = field['value']
                break
        
        # Create message
        msg = MIMEMultipart('alternative')
        ticket_id = form_data.get('ticket_id', 'N/A')
        msg['Subject'] = f"🔔 Nueva Garantía: {empresa} - Ticket: {ticket_id}"
        msg['From'] = smtp_username
        msg['To'] = notification_email
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Send email
        logger.info("Attempting to send notification email...")
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            logger.info("SMTP connection established")
            server.login(smtp_username, smtp_password)
            logger.info("SMTP login successful")
            
            send_result = server.send_message(msg)
            logger.info(f"SMTP send_message result: {send_result}")
            
            # Check if send_message returned any failed recipients
            if send_result:
                logger.warning(f"Some recipients failed: {send_result}")
            else:
                logger.info("All recipients accepted successfully")
            
        logger.info(f"Notification email sent successfully to admin")
        return True
        
    except Exception as e:
        logger.error(f"Error sending notification email: {str(e)}")
        return False

if __name__ == "__main__":
    # Test with sample data
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            webhook_data = json.load(f)
        send_notification_email(webhook_data)