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
from warranty_form_data import WarrantyFormData

load_dotenv()

# Set up secure logging
logger = setup_secure_logging('notification_email')

def get_file_urls_from_form_data(file_list):
    """Extract file URLs from WarrantyFormData file list"""
    urls = []
    for file_info in file_list:
        urls.append({
            'url': file_info.url,
            'name': file_info.name
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

def create_notification_email(form_data: WarrantyFormData):
    """Create notification email content using WarrantyFormData object"""
    
    # Get data from form_data object
    data = form_data.to_dict()
    fecha_creacion = data['fecha_creacion']
    
    # Determine if invoices are attached
    factura_compra = 'Sí' if len(form_data.factura_compra) > 0 else 'No'
    factura_venta = 'Sí' if len(form_data.factura_venta) > 0 else 'No'
    fotos_problema = 'Sí' if len(form_data.fotos_problema) > 0 else 'No'
    videos_problema = 'Sí' if len(form_data.videos_problema) > 0 else 'No'

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

        <h3><a href="https://www.dropbox.com/home/GARANTIAS">Acceder al documento de gestión de garantías</a></h3>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-left: 4px solid #1976D2; margin: 20px 0;">
            <h3>Ticket de Garantía</h3>
            <p><strong style="font-size: 18px; color: #1976D2;">Ticket ID: {form_data.ticket_id}</strong></p>
        </div>
        
        <div style="background-color: #e8f4fd; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0;">
            <h3>Información General</h3>
            <ul>
                <li><strong>Fecha y Hora:</strong> {fecha_creacion}</li>
                <li><strong>Empresa:</strong> {form_data.empresa}</li>
                <li><strong>NIF/CIF/VAT:</strong> {form_data.nif_cif}</li>
                <li><strong>Email:</strong> {form_data.email}</li>
            </ul>
        </div>
        
        <div style="background-color: #fff3e0; padding: 15px; border-left: 4px solid #FF9800; margin: 20px 0;">
            <h3>Información del Producto</h3>
            <ul>
                <li><strong>Marca:</strong> {form_data.brand}</li>
                <li><strong>Modelo:</strong> {form_data.modelo}</li>
                {"<li><strong>Talla:</strong> " + form_data.talla + "</li>" if form_data.talla != 'No aplicable' else ""}
                {"<li><strong>Año de fabricación:</strong> " + form_data.año + "</li>" if form_data.año != 'No aplicable' else ""}
                <li><strong>Estado del producto:</strong> {form_data.estado}</li>
            </ul>
        </div>
        
        <div style="background-color: #ffebee; padding: 15px; border-left: 4px solid #f44336; margin: 20px 0;">
            <h3>Problema Reportado</h3>
            <p>{form_data.problema if form_data.problema != 'No especificado' else ''}</p>
            {"<h3>Solución Propuesta:</h3><p>" + form_data.solucion + "</p>" if form_data.solucion != 'No aplicable' else ""}
        </div>
        
        <div style="background-color: #f3e5f5; padding: 15px; border-left: 4px solid #9c27b0; margin: 20px 0;">
            <h3>Documentación</h3>
            <ul>
                <li><strong>Factura de compra:</strong> {factura_compra}</li>
                <li><strong>Factura de venta:</strong> {factura_venta}</li>
                <li><strong>Imágenes:</strong> {fotos_problema}</li>
                <li><strong>Vídeos:</strong> {videos_problema}</li>
            </ul>
        </div>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-left: 4px solid #4caf50; margin: 20px 0;">
            <h3>Acciones Realizadas</h3>
            <ul>
                <li>✓ Notificación de nuevo ticket generada</li>
                <li>✓ Email de confirmación enviado al cliente</li>
                {"<li>✓ Solicitud de garantía enviada a Conway</li>" if form_data.is_conway() else ""}
                <li>✓ Registro añadido al archivo de Excel en Dropbox</li>   
            </ul>
        </div>
        
        <hr>
        
        <p>Este mensaje ha sido generado automáticamente por el sistema de gestión de garantías de PROFFECTIV.</p>
    </body>
    </html>
    """
    
    return html_content

def send_notification_email(form_data: WarrantyFormData):
    """Send notification email to admin using WarrantyFormData object"""
    downloaded_files = []
    try:
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
        
        # Get empresa and ticket_id from form_data
        empresa = form_data.empresa
        ticket_id = form_data.ticket_id
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Nueva Solicitud de Garantía: {empresa} - Ticket: {ticket_id}"
        msg['From'] = smtp_username
        msg['To'] = notification_email
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Download and attach files from form_data
        try:
            # Get all files from form_data (invoices, images, videos)
            all_files = []
            all_files.extend(get_file_urls_from_form_data(form_data.factura_compra))
            all_files.extend(get_file_urls_from_form_data(form_data.factura_venta))
            all_files.extend(get_file_urls_from_form_data(form_data.fotos_problema))
            all_files.extend(get_file_urls_from_form_data(form_data.videos_problema))
            
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
        form_data = WarrantyFormData(webhook_data, "test-ticket-123")
        send_notification_email(form_data)