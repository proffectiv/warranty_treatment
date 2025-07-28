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
from warranty_form_data import WarrantyFormData

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

# Old field parsing functions removed - now using WarrantyFormData methods

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

def create_conway_notification_email(form_data: WarrantyFormData):
    """Create Conway notification email content using WarrantyFormData object"""
    
    # Get data from form_data object
    data = form_data.to_dict()
    fecha_creacion = data['fecha_creacion']
    ticket_id = form_data.ticket_id
    
    # Conway-specific data extraction
    empresa = form_data.empresa
    nif_cif = form_data.nif_cif
    email = form_data.email
    marca = form_data.brand
    modelo = form_data.modelo
    talla = form_data.talla
    año = form_data.año
    estado = 'New' if form_data.estado.lower() == 'nuevo' else 'Used'
    
    # Keep original Spanish text and translated English text
    problema_raw = form_data.problema
    solucion_raw = form_data.solucion
    problema = translate_text(form_data.problema)
    solucion = translate_text(form_data.solucion)
    
    # Determine if invoices are attached
    factura_compra = 'Yes' if len(form_data.factura_compra) > 0 else 'No'
    factura_venta = 'Yes' if len(form_data.factura_venta) > 0 else 'No'
    fotos_problema = 'Yes' if len(form_data.fotos_problema) > 0 else 'No'
    videos_problema = 'Yes' if len(form_data.videos_problema) > 0 else 'No'

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
                <li><strong>Images:</strong> {fotos_problema}</li>
                <li><strong>Videos:</strong> {videos_problema}</li>
            </ul>
        </div>

        
        <p>This message has been automatically generated by the PROFFECTIV warranty management system.</p>
        <p>If you have any questions, please contact us at <a href="mailto:info@proffectiv.com">info@proffectiv.com</a>.</p>
    </body>
    </html>
    """
    
    return html_content

def send_conway_notification_email(form_data: WarrantyFormData):
    downloaded_files = []
    try:
        html_content = create_conway_notification_email(form_data)
        
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
        
        # Get empresa and ticket_id from form_data
        empresa = form_data.empresa
        ticket_id = form_data.ticket_id
        
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = f"PROFFECTIV - New Conway Warranty Request - Ticket: {ticket_id}"
        msg['From'] = smtp_username
        msg['To'] = conway_notification_email
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Download and attach files from form_data (invoices, images, videos)
        try:
            # Get all files from form_data (invoices, images, videos)
            all_files = []
            for file_info in form_data.factura_compra:
                all_files.append({'url': file_info.url, 'name': file_info.name})
            for file_info in form_data.factura_venta:
                all_files.append({'url': file_info.url, 'name': file_info.name})
            for file_info in form_data.fotos_problema:
                all_files.append({'url': file_info.url, 'name': file_info.name})
            for file_info in form_data.videos_problema:
                all_files.append({'url': file_info.url, 'name': file_info.name})
            
            # Process each file
            for file_info in all_files:
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
        except Exception as e:
            logger.warning(f"Error processing file attachments: {str(e)}")
        
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
        form_data = WarrantyFormData(webhook_data, "test-ticket-123")
        send_conway_notification_email(form_data)