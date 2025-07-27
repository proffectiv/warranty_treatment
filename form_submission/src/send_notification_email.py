import os
import json
import smtplib
import sys
import requests
import tempfile
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv

# Import logging filter from root directory
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

load_dotenv()

# Set up secure logging
logger = setup_secure_logging('notification_email')

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

def get_file_urls_from_field(fields, field_name):
    """Extract file URLs from a field if it contains file uploads"""
    value = fields.get(field_name)
    urls = []
    
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and 'url' in item:
                urls.append({
                    'url': item['url'],
                    'name': item.get('name', 'file')
                })
    
    return urls

def download_file_from_url(url, filename):
    """Download file from URL and save to temporary file"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        
        # Write content to temporary file
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        
        temp_file.close()
        
        logger.info(f"Downloaded file: {filename} from {url}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Failed to download file {filename} from {url}: {str(e)}")
        return None

def create_notification_email(webhook_data):
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
    
    # Initialize all variables with defaults
    modelo = 'No especificado'
    talla = 'No aplicable'
    año = 'No aplicable'
    estado = 'No especificado'
    problema = 'No especificado'
    solucion = 'No aplicable'
    factura_compra = 'No'
    factura_venta = 'No'
    
    # Brand-specific fields using human-readable field names
    if marca == 'Conway':
        modelo = get_field_value_by_name(fields, 'Conway - Por favor, indica el nombre completo del modelo (ej. Cairon C 2.0 500)')
        talla = get_field_value_by_name(fields, 'Conway - Talla')
        año = get_field_value_by_name(fields, 'Conway - Año de fabricación')
        estado = get_field_value_by_name(fields, 'Conway - Estado de la bicicleta')
        problema = get_field_value_by_name(fields, 'Conway - Descripción del problema')
        solucion = get_field_value_by_name(fields, 'Conway - Solución o reparación propuesta y presupuesto aproximado')
        factura_compra = 'Sí' if get_field_value_by_name(fields, 'Conway - Adjunta la factura de compra a Hartje') != 'No especificado' else 'No'
        factura_venta = 'Sí' if get_field_value_by_name(fields, 'Conway - Adjunta la factura de venta') != 'No especificado' else 'No'
    elif marca == 'Cycplus':
        modelo = get_field_value_by_name(fields, 'Cycplus - Modelo')
        estado = get_field_value_by_name(fields, 'Cycplus - Estado del Producto')
        problema = get_field_value_by_name(fields, 'Cycplus - Descripción del problema')
        factura_compra = 'Sí' if get_field_value_by_name(fields, 'Adjunta la factura de compra') != 'No especificado' else 'No'
        factura_venta = 'Sí' if get_field_value_by_name(fields, 'Cycplus - Adjunta la factura de venta') != 'No especificado' else 'No'
        talla = 'No aplicable'
        año = 'No aplicable'
        solucion = 'No aplicable'
    elif marca == 'Dare':
        modelo = get_field_value_by_name(fields, 'Dare - Modelo')
        talla = get_field_value_by_name(fields, 'Dare - Talla')
        año = get_field_value_by_name(fields, 'Dare - Año de fabricación')
        estado = get_field_value_by_name(fields, 'Dare - Estado de la bicicleta')
        problema = get_field_value_by_name(fields, 'Dare - Descripción del problema')
        solucion = get_field_value_by_name(fields, 'Dare - Solución o reparación propuesta y presupuesto aproximado')
        factura_compra = 'Sí' if get_field_value_by_name(fields, 'Dare - Adjunta la factura de compra') != 'No especificado' else 'No'
        factura_venta = 'Sí' if get_field_value_by_name(fields, 'Dare - Adjunta la factura de venta') != 'No especificado' else 'No'
    else:
        # Handle unknown brands or missing brand info
        logger.warning(f"Unknown brand: {marca}. Using default values.")
    
    # Get creation date
    fecha_creacion = datetime.now().strftime('%d/%m/%Y %H:%M')

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
        <h2>Nueva Solicitud de Garantía Recibida</h2>

        <h3><a href="https://www.dropbox.com/home/GARANTIAS?preview=GARANTIAS_PROFFECTIV.xlsx">Acceder al documento de gestión de garantías</a></h3>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #1976D2; margin: 20px 0;">
            <h3>Ticket de Garantía</h3>
            <p><strong style="font-size: 18px; color: #1976D2;">Ticket ID: {ticket_id}</strong></p>
        </div>
        
        <div style="background-color: #e8f4fd; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0;">
            <h3>Información General</h3>
            <ul>
                <li><strong>Fecha y Hora:</strong> {fecha_creacion}</li>
                <li><strong>Empresa:</strong> {empresa}</li>
                <li><strong>NIF/CIF/VAT:</strong> {nif_cif}</li>
                <li><strong>Email:</strong> {email}</li>
            </ul>
        </div>
        
        <div style="background-color: #fff3e0; padding: 15px; border-left: 4px solid #FF9800; margin: 20px 0;">
            <h3>Información del Producto</h3>
            <ul>
                <li><strong>Marca:</strong> {marca}</li>
                <li><strong>Modelo:</strong> {modelo}</li>
                {"<li><strong>Talla:</strong> " + str(talla) + "</li>" if talla != 'No aplicable' else ""}
                {"<li><strong>Año de fabricación:</strong> " + str(año) + "</li>" if año != 'No aplicable' else ""}
                <li><strong>Estado del producto:</strong> {estado}</li>
            </ul>
        </div>
        
        <div style="background-color: #ffebee; padding: 15px; border-left: 4px solid #f44336; margin: 20px 0;">
            <h3>Problema Reportado</h3>
            <p>{problema}</p>
            {"<h3>Solución Propuesta:</h3><p>" + str(solucion) + "</p>" if solucion != 'No aplicable' and solucion != 'No especificado' else ""}
        </div>
        
        <div style="background-color: #f3e5f5; padding: 15px; border-left: 4px solid #9c27b0; margin: 20px 0;">
            <h3>Documentación</h3>
            <ul>
                <li><strong>Factura de compra:</strong> {factura_compra}</li>
                <li><strong>Factura de venta:</strong> {factura_venta}</li>
            </ul>
        </div>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-left: 4px solid #4caf50; margin: 20px 0;">
            <h3>Acciones Realizadas</h3>
            <ul>
                <li>✓ Notificación de nuevo ticket generada</li>
                <li>✓ Email de confirmación enviado al cliente</li>
                {"<li>✓ Solicitud de garantía enviada a Conway" if marca == 'Conway' else ""}
                <li>✓ Registro añadido al archivo de Excel en Dropbox</li>   
            </ul>
        </div>
        
        <hr>
        
        <p>Este mensaje ha sido generado automáticamente por el sistema de gestión de garantías de PROFFECTIV.</p>
    </body>
    </html>
    """
    
    return html_content

def send_notification_email(webhook_data):
    downloaded_files = []
    try:
        html_content = create_notification_email(webhook_data)
        
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
        
        # Get empresa from webhook data
        if 'fields' in webhook_data and 'fieldsById' in webhook_data:
            empresa = get_field_value_by_name(webhook_data['fields'], 'Empresa')
            ticket_id = webhook_data.get('ticket_id', 'N/A')
        elif 'client_payload' in webhook_data:
            empresa = get_field_value_by_name(webhook_data['client_payload']['fields'], 'Empresa')
            ticket_id = webhook_data.get('ticket_id', 'N/A')
        else:
            # Fallback for old structure
            form_data = webhook_data.get('data', webhook_data)
            empresa = 'N/A'
            for field in form_data.get('fields', []):
                if field.get('key') == 'question_59JjXb':
                    empresa = field.get('value', 'N/A')
                    break
            ticket_id = form_data.get('ticket_id', 'N/A')
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Nueva Solicitud de Garantía: {empresa} - Ticket: {ticket_id}"
        msg['From'] = smtp_username
        msg['To'] = notification_email
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Get fields for file attachments
        if 'fields' in webhook_data and 'fieldsById' in webhook_data:
            fields = webhook_data['fields']
        elif 'client_payload' in webhook_data:
            fields = webhook_data['client_payload']['fields']
        else:
            form_data = webhook_data.get('data', webhook_data)
            fields = {field['label']: field['value'] for field in form_data.get('fields', [])}
        
        # Get brand to determine which file fields to check
        brand = get_field_value_by_name(fields, 'Marca del Producto')
        
        # Download and attach files based on brand
        try:
            # Define file fields based on brand
            file_fields = []
            if brand == 'Conway':
                file_fields = [
                    'Conway - Adjunta la factura de compra a Hartje',
                    'Conway - Adjunta la factura de venta'
                ]
            elif brand == 'Dare':
                file_fields = [
                    'Dare - Adjunta la factura de compra',
                    'Dare - Adjunta la factura de venta'
                ]
            elif brand == 'Cycplus':
                file_fields = [
                    'Adjunta la factura de compra',
                    'Cycplus - Adjunta la factura de venta'
                ]
            else:
                # Generic file fields for other brands
                file_fields = [
                    'Adjunta la factura de compra',
                    'Adjunta la factura de venta'
                ]
            
            # Process each file field
            for field_name in file_fields:
                file_urls = get_file_urls_from_field(fields, field_name)
                for file_info in file_urls:
                    temp_file_path = download_file_from_url(file_info['url'], file_info['name'])
                    if temp_file_path:
                        downloaded_files.append(temp_file_path)
                        
                        # Attach file to email
                        with open(temp_file_path, 'rb') as attachment:
                            # Guess the content type based on the file's name
                            ctype, encoding = mimetypes.guess_type(temp_file_path)
                            if ctype is None or encoding is not None:
                                ctype = 'application/octet-stream'
                            
                            maintype, subtype = ctype.split('/', 1)
                            
                            part = MIMEBase(maintype, subtype)
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {file_info["name"]}'
                            )
                            msg.attach(part)
                            
                            logger.info(f"Attached file: {file_info['name']} from field: {field_name}")
        
        except Exception as e:
            logger.warning(f"Error processing file attachments: {str(e)}")
        
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
    finally:
        # Clean up downloaded temporary files
        for temp_file_path in downloaded_files:
            try:
                os.unlink(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_file_path}: {str(e)}")

if __name__ == "__main__":
    # Test with sample data
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            webhook_data = json.load(f)
        send_notification_email(webhook_data)