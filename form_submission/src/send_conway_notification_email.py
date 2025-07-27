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
from googletrans import Translator
from urllib.parse import urlparse

# Import logging filter from root directory
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

load_dotenv()

# Set up secure logging
logger = setup_secure_logging('conway_notification_email')

# Initialize translator
translator = Translator()

def translate_text(text, target_lang='en'):
    """Translate text to target language with error handling"""
    try:
        if not text or text.strip() == 'Not specified':
            return text
        
        # Detect source language and translate if not already English
        detection = translator.detect(text)
        if detection.lang != target_lang:
            result = translator.translate(text, dest=target_lang)
            logger.info(f"Translated text from {detection.lang} to {target_lang}")
            return result.text
        else:
            logger.info(f"Text already in {target_lang}, no translation needed")
            return text
    except Exception as e:
        logger.warning(f"Translation failed: {str(e)}, returning original text")
        return text

def get_field_value_by_name(fields, field_name):
    """Get field value using human-readable field name from new webhook structure"""
    value = fields.get(field_name)
    
    if value is None:
        return 'Not specified'
    
    # Handle different value types
    if isinstance(value, list):
        if len(value) > 0:
            # For dropdown selections, return the first value
            if isinstance(value[0], dict):
                # File upload - return file info
                return f"Attached file: {value[0].get('name', 'file')}"
            else:
                # Dropdown selection - return the selected value
                return str(value[0])
        else:
            return 'Not specified'
    elif isinstance(value, str):
        return value if value.strip() else 'Not specified'
    else:
        return str(value) if value else 'Not specified'

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

def create_conway_notification_email(webhook_data):
    # Extract fields from webhook structure
    if 'fields' in webhook_data and 'fieldsById' in webhook_data:
        # GitHub action webhook structure (direct client_payload)
        fields = webhook_data['fields']
        ticket_id = webhook_data.get('ticket_id', 'Not available')
    elif 'client_payload' in webhook_data:
        # GitHub webhook structure with client_payload
        fields = webhook_data['client_payload']['fields']
        ticket_id = webhook_data.get('ticket_id', 'Not available')
    else:
        # Fallback to old structure if needed
        form_data = webhook_data.get('data', webhook_data)
        fields = {field['label']: field['value'] for field in form_data.get('fields', [])}
        ticket_id = form_data.get('ticket_id', 'Not available')
    
    # Get basic info using human-readable field names
    empresa = get_field_value_by_name(fields, 'Empresa')
    nif_cif = get_field_value_by_name(fields, 'NIF/CIF/VAT')
    email = get_field_value_by_name(fields, 'Email')
    marca = get_field_value_by_name(fields, 'Marca del Producto')
    
    # Initialize Conway-specific variables
    modelo = get_field_value_by_name(fields, 'Conway - Por favor, indica el nombre completo del modelo (ej. Cairon C 2.0 500)')
    talla = get_field_value_by_name(fields, 'Conway - Talla')
    año = get_field_value_by_name(fields, 'Conway - Año de fabricación')
    estado = 'New' if get_field_value_by_name(fields, 'Conway - Estado de la bicicleta') == 'Nueva' else 'Used'
    problema_raw = get_field_value_by_name(fields, 'Conway - Descripción del problema')
    solucion_raw = get_field_value_by_name(fields, 'Conway - Solución o reparación propuesta y presupuesto aproximado')
    factura_compra = 'Yes' if get_field_value_by_name(fields, 'Conway - Adjunta la factura de compra a Hartje') != 'Not specified' else 'No'
    factura_venta = 'Yes' if get_field_value_by_name(fields, 'Conway - Adjunta la factura de venta') != 'Not specified' else 'No'
    
    # Translate the problem and solution fields to English
    problema = translate_text(problema_raw)
    solucion = translate_text(solucion_raw)
    
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
        <h2>New Conway Warranty Request</h2>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #1976D2; margin: 20px 0;">
            <h3>Warranty Ticket</h3>
            <p><strong style="font-size: 18px; color: #1976D2;">Ticket ID: {ticket_id}</strong></p>
        </div>
        
        <div style="background-color: #e8f4fd; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0;">
            <h3>Client Information</h3>
            <ul>
                <li><strong>Date and Time:</strong> {fecha_creacion}</li>
                <li><strong>Company:</strong> {empresa}</li>
                <li><strong>NIF/CIF/VAT:</strong> {nif_cif}</li>
                <li><strong>Email:</strong> {email}</li>
            </ul>
        </div>
        
        <div style="background-color: #fff3e0; padding: 15px; border-left: 4px solid #FF9800; margin: 20px 0;">
            <h3>Product Information</h3>
            <ul>
                <li><strong>Brand:</strong> {marca}</li>
                <li><strong>Model:</strong> {modelo}</li>
                {"<li><strong>Size:</strong> " + str(talla) + "</li>" if talla != 'Not specified' else ""}
                {"<li><strong>Manufacturing Year:</strong> " + str(año) + "</li>" if año != 'Not specified' else ""}
                <li><strong>Product Condition:</strong> {estado}</li>
            </ul>
        </div>
        
        <div style="background-color: #ffebee; padding: 15px; border-left: 4px solid #f44336; margin: 20px 0;">
            <h3>Reported Problem</h3>
            <h4>Spanish:</h4>
            <p>{problema_raw}</p>
            <h4>English:</h4>
            <p>{problema}</p>
            <h3>Proposed Solution:</h3>
            <h4>Spanish:</h4>
            <p>{solucion_raw if solucion_raw != 'Not specified' else ''}</p>
            <h4>English:</h4>
            <p>{solucion if solucion != 'Not specified' else ''}</p>
        </div>
        
        <div style="background-color: #f3e5f5; padding: 15px; border-left: 4px solid #9c27b0; margin: 20px 0;">
            <h3>Documentation</h3>
            <ul>
                <li><strong>Purchase invoice:</strong> {factura_compra}</li>
                <li><strong>Sales invoice:</strong> {factura_venta}</li>
            </ul>
        </div>

        
        <p>This message has been automatically generated by the PROFFECTIV warranty management system.</p>
        <p>If you have any questions, please contact us at <a href="mailto:info@proffectiv.com">info@proffectiv.com</a>.</p>
    </body>
    </html>
    """
    
    return html_content

def send_conway_notification_email(webhook_data):
    downloaded_files = []
    try:
        html_content = create_conway_notification_email(webhook_data)
        
        # Email configuration
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        conway_notification_email = os.getenv('CONWAY_NOTIFICATION_EMAIL')
        
        # Debug email configuration
        logger.info(f"Conway email config - Host: {smtp_host}, Port: {smtp_port}, Notification email: {conway_notification_email}")
        
        # Check for missing configuration
        if not all([smtp_host, smtp_port, smtp_username, smtp_password, conway_notification_email]):
            missing = [k for k, v in {
                'SMTP_HOST': smtp_host,
                'SMTP_PORT': smtp_port, 
                'SMTP_USERNAME': smtp_username,
                'SMTP_PASSWORD': smtp_password,
                'CONWAY_NOTIFICATION_EMAIL': conway_notification_email
            }.items() if not v]
            raise Exception(f"Missing email configuration: {missing}")
        
        # Get empresa and fields from webhook data
        if 'fields' in webhook_data and 'fieldsById' in webhook_data:
            fields = webhook_data['fields']
            empresa = get_field_value_by_name(fields, 'Empresa')
            ticket_id = webhook_data.get('ticket_id', 'N/A')
        elif 'client_payload' in webhook_data:
            fields = webhook_data['client_payload']['fields']
            empresa = get_field_value_by_name(fields, 'Empresa')
            ticket_id = webhook_data.get('ticket_id', 'N/A')
        else:
            # Fallback for old structure
            form_data = webhook_data.get('data', webhook_data)
            fields = {field['label']: field['value'] for field in form_data.get('fields', [])}
            empresa = 'N/A'
            for field in form_data.get('fields', []):
                if field.get('key') == 'question_59JjXb':
                    empresa = field.get('value', 'N/A')
                    break
            ticket_id = form_data.get('ticket_id', 'N/A')
        
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = f"PROFFECTIV - New Conway Warranty Request - Ticket: {ticket_id}"
        msg['From'] = smtp_username
        msg['To'] = conway_notification_email
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Download and attach files from Conway fields
        file_fields = [
            'Conway - Adjunta la factura de compra a Hartje',
            'Conway - Adjunta la factura de venta'
        ]
        
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
                        
                        logger.info(f"Attached file: {file_info['name']}")
        
        # Send email
        logger.info("Attempting to send Conway notification email...")
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
            
        logger.info(f"Conway notification email sent successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error sending Conway notification email: {str(e)}")
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
        send_conway_notification_email(webhook_data)