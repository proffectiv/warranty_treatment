import os
import json
import requests
import pandas as pd
import sys
from datetime import datetime, timedelta
from io import BytesIO
from dotenv import load_dotenv
from difflib import SequenceMatcher

# Import logging filter from root directory
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

load_dotenv()

# Set up secure logging
logger = setup_secure_logging('excel_dropbox')

def get_dropbox_access_token():
    """Get access token from refresh token"""
    refresh_token = os.getenv('DROPBOX_REFRESH_TOKEN')
    app_key = os.getenv('DROPBOX_APP_KEY')
    app_secret = os.getenv('DROPBOX_APP_SECRET')
    
    url = 'https://api.dropbox.com/oauth2/token'
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': app_key,
        'client_secret': app_secret
    }
    
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Failed to get access token: {response.text}")

def download_excel_from_dropbox(access_token, file_path):
    """Download Excel file from Dropbox"""
    url = 'https://content.dropboxapi.com/2/files/download'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Dropbox-API-Arg': json.dumps({'path': file_path})
    }
    
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        raise Exception(f"Failed to download file: {response.text}")

def upload_excel_to_dropbox(access_token, file_path, excel_data):
    """Upload Excel file to Dropbox"""
    url = 'https://content.dropboxapi.com/2/files/upload'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Dropbox-API-Arg': json.dumps({
            'path': file_path,
            'mode': 'overwrite',
            'autorename': False
        }),
        'Content-Type': 'application/octet-stream'
    }
    
    response = requests.post(url, headers=headers, data=excel_data)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to upload file: {response.text}")

def get_field_value_by_name(fields, field_name):
    """Get field value using human-readable field name from new webhook structure"""
    value = fields.get(field_name)
    
    if value is None:
        return ''
    
    # Handle different value types
    if isinstance(value, list):
        if len(value) > 0:
            # For dropdown selections, return the first value
            if isinstance(value[0], dict):
                # File upload - return URL
                return value[0].get('url', '')
            else:
                # Dropdown selection - return the selected value
                return str(value[0])
        else:
            return ''
    elif isinstance(value, str):
        return value if value.strip() else ''
    else:
        return str(value) if value else ''

def text_similarity(text1, text2):
    """Calculate similarity between two texts using SequenceMatcher"""
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, str(text1).lower(), str(text2).lower()).ratio()

def calculate_duplicate_probability(webhook_data, existing_df):
    """
    Calculate the probability that this form submission is a duplicate
    Returns probability (0.0-1.0) and the most similar existing record
    """
    # Extract fields from webhook structure
    if 'fields' in webhook_data and 'fieldsById' in webhook_data:
        # GitHub action webhook structure (direct client_payload)
        fields = webhook_data['fields']
    elif 'client_payload' in webhook_data:
        fields = webhook_data['client_payload']['fields']
    else:
        # Fallback to old structure
        form_data = webhook_data.get('data', webhook_data)
        fields = {field['label']: field['value'] for field in form_data.get('fields', [])}
    
    current_nif = get_field_value_by_name(fields, 'NIF/CIF/VAT').strip().upper()
    current_email = get_field_value_by_name(fields, 'Email').strip().lower()
    current_brand = get_field_value_by_name(fields, 'Marca del Producto')
    current_time = datetime.now()
    
    # Get current submission details based on brand
    if current_brand == 'Conway':
        current_model = get_field_value_by_name(fields, 'Conway - Por favor, indica el nombre completo del modelo (ej. Cairon C 2.0 500)')
        current_size = get_field_value_by_name(fields, 'Conway - Talla')
    elif current_brand == 'Cycplus':
        current_model = get_field_value_by_name(fields, 'Cycplus - Modelo')
        current_size = 'N/A'  # No size for Cycplus
    elif current_brand == 'Dare':
        current_model = get_field_value_by_name(fields, 'Dare - Modelo')
        current_size = get_field_value_by_name(fields, 'Dare - Talla')
    elif current_brand == 'Kogel':
        current_model = ''
        current_size = 'N/A'  # No size for Kogel
    else:
        return 0.0, None
    
    # Filter existing records for same NIF
    if existing_df.empty:
        return 0.0, None
    
    # Look for records with same NIF
    same_nif_records = existing_df[existing_df['NIF/CIF/VAT'].str.upper().str.strip() == current_nif]
    
    if same_nif_records.empty:
        return 0.0, None
    
    max_probability = 0.0
    most_similar_record = None
    
    for _, record in same_nif_records.iterrows():
        probability_factors = []
        
        # 1. Email similarity (20% weight)
        email_similarity = text_similarity(current_email, str(record.get('Email', '')).strip().lower())
        probability_factors.append(('email', email_similarity, 0.20))
        
        # 2. Brand exact match (25% weight) - brands are in separate sheets, so this is always 1.0
        brand_match = 1.0  # Since we're checking within the same brand sheet
        probability_factors.append(('brand', brand_match, 0.25))
        
        # 3. Model similarity (20% weight)
        model_similarity = text_similarity(current_model, str(record.get('Modelo', '')))
        probability_factors.append(('model', model_similarity, 0.20))
        
        # 4. Size similarity (10% weight for Conway/Dare, 0% for others)
        if current_brand in ['Conway', 'Dare']:
            size_similarity = text_similarity(current_size, str(record.get('Talla', '')))
            probability_factors.append(('size', size_similarity, 0.10))
        
        # 5. Time proximity (25% weight)
        try:
            record_time = datetime.strptime(str(record.get('Fecha de creación', '')), '%d/%m/%Y')
            # Add current time to make comparison fair (assume submitted at similar time)
            record_time = record_time.replace(hour=current_time.hour, minute=current_time.minute)
            time_diff = abs((current_time - record_time).total_seconds())
            
            # Calculate time similarity (closer = higher probability)
            # 1 hour = 0.9, 6 hours = 0.7, 24 hours = 0.3, 48 hours = 0.1
            if time_diff <= 3600:  # 1 hour
                time_similarity = 0.95
            elif time_diff <= 21600:  # 6 hours
                time_similarity = 0.80
            elif time_diff <= 86400:  # 24 hours
                time_similarity = 0.40
            elif time_diff <= 172800:  # 48 hours
                time_similarity = 0.15
            else:
                time_similarity = 0.05
                
        except:
            time_similarity = 0.0
            
        probability_factors.append(('time', time_similarity, 0.25))
        
        # Calculate weighted probability
        total_probability = sum(score * weight for _, score, weight in probability_factors)
        
        # Bonus for very high individual scores
        high_individual_scores = [score for _, score, _ in probability_factors if score > 0.9]
        if len(high_individual_scores) >= 3:
            total_probability += 0.1  # 10% bonus
        
        if total_probability > max_probability:
            max_probability = total_probability
            most_similar_record = {
                'record': record,
                'factors': probability_factors,
                'total_score': total_probability
            }
    
    return min(max_probability, 1.0), most_similar_record

def check_for_duplicates(webhook_data):
    """
    Check if the current submission is likely a duplicate
    Returns (is_duplicate, probability, details)
    """
    try:
        # Extract fields from webhook structure
        if 'fields' in webhook_data and 'fieldsById' in webhook_data:
            # GitHub action webhook structure (direct client_payload)
            fields = webhook_data['fields']
        elif 'client_payload' in webhook_data:
            fields = webhook_data['client_payload']['fields']
        else:
            # Fallback to old structure
            form_data = webhook_data.get('data', webhook_data)
            fields = {field['label']: field['value'] for field in form_data.get('fields', [])}
        
        brand = get_field_value_by_name(fields, 'Marca del Producto')
        
        if not brand or brand == 'No especificado':
            return False, 0.0, "Could not determine brand"
        
        # Download and check Excel file
        access_token = get_dropbox_access_token()
        folder_path = os.getenv('DROPBOX_FOLDER_PATH')
        file_path = f"{folder_path}/GARANTIAS_PROFFECTIV.xlsx"
        
        try:
            excel_file = download_excel_from_dropbox(access_token, file_path)
            df = pd.read_excel(excel_file, sheet_name=brand)
        except Exception as e:
            # If file doesn't exist or sheet doesn't exist, no duplicates possible
            logger.warning(f"Could not read Excel file for duplicate check: {str(e)}")
            return False, 0.0, f"Could not access existing records: {str(e)}"
        
        # Calculate duplicate probability
        probability, similar_record = calculate_duplicate_probability(webhook_data, df)
        
        # Define threshold for considering it a duplicate
        DUPLICATE_THRESHOLD = 0.75  # 75% similarity threshold
        
        is_duplicate = probability >= DUPLICATE_THRESHOLD
        
        details = {
            'probability': probability,
            'threshold': DUPLICATE_THRESHOLD,
            'brand': brand,
            'similar_record': similar_record
        }
        
        return is_duplicate, probability, details
        
    except Exception as e:
        logger.error(f"Error during duplicate check: {str(e)}")
        return False, 0.0, f"Error during duplicate check: {str(e)}"

def prepare_row_data(webhook_data, brand):
    """Prepare row data based on brand"""
    # Extract fields from webhook structure
    if 'fields' in webhook_data and 'fieldsById' in webhook_data:
        # GitHub action webhook structure (direct client_payload)
        fields = webhook_data['fields']
        ticket_id = webhook_data.get('ticket_id', 'No disponible')
    elif 'client_payload' in webhook_data:
        fields = webhook_data['client_payload']['fields']
        ticket_id = webhook_data.get('ticket_id', 'No disponible')
    else:
        # Fallback to old structure
        form_data = webhook_data.get('data', webhook_data)
        fields = {field['label']: field['value'] for field in form_data.get('fields', [])}
        ticket_id = form_data.get('ticket_id', 'No disponible')
    
    fecha_creacion = datetime.now().strftime('%d/%m/%Y')
    
    # Common fields
    empresa = get_field_value_by_name(fields, 'Empresa')
    nif_cif = get_field_value_by_name(fields, 'NIF/CIF/VAT')
    email = get_field_value_by_name(fields, 'Email')
    
    if brand == 'Conway':
        row_data = {
            'Ticket ID': ticket_id,
            'Estado': 'Recibida',
            'Fecha de creación': fecha_creacion,
            'Empresa': empresa,
            'NIF/CIF/VAT': nif_cif,
            'Email': email,
            'Modelo': get_field_value_by_name(fields, 'Conway - Por favor, indica el nombre completo del modelo (ej. Cairon C 2.0 500)'),
            'Talla': get_field_value_by_name(fields, 'Conway - Talla'),
            'Año de fabricación': get_field_value_by_name(fields, 'Conway - Año de fabricación'),
            'Estado de la bicicleta': get_field_value_by_name(fields, 'Conway - Estado de la bicicleta'),
            'Descripción del problema': get_field_value_by_name(fields, 'Conway - Descripción del problema'),
            'Solución y/o reparación propuesta y presupuesto': get_field_value_by_name(fields, 'Conway - Solución o reparación propuesta y presupuesto aproximado'),
            'Factura de compra': get_field_value_by_name(fields, 'Conway - Adjunta la factura de compra a Hartje'),
            'Factura de venta': get_field_value_by_name(fields, 'Conway - Adjunta la factura de venta')
        }
    elif brand == 'Cycplus':
        row_data = {
            'Ticket ID': ticket_id,
            'Estado': 'Recibida',
            'Fecha de creación': fecha_creacion,
            'Empresa': empresa,
            'NIF/CIF/VAT': nif_cif,
            'Email': email,
            'Modelo': get_field_value_by_name(fields, 'Cycplus - Modelo'),
            'Estado del producto': get_field_value_by_name(fields, 'Cycplus - Estado del Producto'),
            'Descripción del problema': get_field_value_by_name(fields, 'Cycplus - Descripción del problema'),
            'Solución y/o reparación propuesta y presupuesto': '',  # Not applicable for Cycplus
            'Factura de compra': get_field_value_by_name(fields, 'Adjunta la factura de compra'),
            'Factura de venta': get_field_value_by_name(fields, 'Cycplus - Adjunta la factura de venta')
        }
    elif brand == 'Dare':
        row_data = {
            'Ticket ID': ticket_id,
            'Estado': 'Recibida',
            'Fecha de creación': fecha_creacion,
            'Empresa': empresa,
            'NIF/CIF/VAT': nif_cif,
            'Email': email,
            'Modelo': get_field_value_by_name(fields, 'Dare - Modelo'),
            'Talla': get_field_value_by_name(fields, 'Dare - Talla'),
            'Estado de la bicicleta': get_field_value_by_name(fields, 'Dare - Estado de la bicicleta'),
            'Descripción del problema': get_field_value_by_name(fields, 'Dare - Descripción del problema'),
            'Solución y/o reparación propuesta y presupuesto': get_field_value_by_name(fields, 'Dare - Solución o reparación propuesta y presupuesto aproximado'),
            'Factura de compra': get_field_value_by_name(fields, 'Dare - Adjunta la factura de compra'),
            'Factura de venta': get_field_value_by_name(fields, 'Dare - Adjunta la factura de venta')
        }
    elif brand == 'Kogel':
        # Kogel structure similar to others - add if needed
        row_data = {
            'Ticket ID': ticket_id,
            'Estado': 'Recibida',
            'Fecha de creación': fecha_creacion,
            'Empresa': empresa,
            'NIF/CIF/VAT': nif_cif,
            'Email': email,
            'Modelo': '',
            'Estado del producto': '',
            'Descripción del problema': '',
            'Solución y/o reparación propuesta y presupuesto': '',
            'Factura de compra': '',
            'Factura de venta': ''
        }
    
    return row_data

def update_excel_file(webhook_data):
    """Main function to update Excel file in Dropbox"""
    try:
        # Extract fields from webhook structure
        if 'fields' in webhook_data and 'fieldsById' in webhook_data:
            # GitHub action webhook structure (direct client_payload)
            fields = webhook_data['fields']
        elif 'client_payload' in webhook_data:
            fields = webhook_data['client_payload']['fields']
        else:
            # Fallback to old structure
            form_data = webhook_data.get('data', webhook_data)
            fields = {field['label']: field['value'] for field in form_data.get('fields', [])}
        
        brand = get_field_value_by_name(fields, 'Marca del Producto')
        
        if not brand or brand == 'No especificado':
            raise Exception("Brand not found in form data")
        
        # Get Dropbox credentials
        access_token = get_dropbox_access_token()
        folder_path = os.getenv('DROPBOX_FOLDER_PATH')
        file_path = f"{folder_path}/GARANTIAS_PROFFECTIV.xlsx"
        
        # Download existing Excel file
        excel_file = download_excel_from_dropbox(access_token, file_path)
        
        # Load Excel file
        excel_data = pd.ExcelFile(excel_file)
        
        # Check if brand sheet exists
        if brand not in excel_data.sheet_names:
            raise Exception(f"Sheet '{brand}' not found in Excel file")
        
        # Load the specific brand sheet
        df = pd.read_excel(excel_file, sheet_name=brand)
        
        # Prepare new row data
        new_row = prepare_row_data(webhook_data, brand)
        
        # Add new row to dataframe
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Save all sheets back to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write all existing sheets
            for sheet_name in excel_data.sheet_names:
                if sheet_name == brand:
                    # Write updated sheet
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    # Write original sheet
                    original_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    original_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        
        # Upload updated file back to Dropbox
        upload_result = upload_excel_to_dropbox(access_token, file_path, output.getvalue())
        
        logger.info(f"Excel file updated successfully. New row added to {brand} sheet.")
        logger.info(f"File uploaded to Dropbox: {upload_result.get('path_display', file_path)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating Excel file: {str(e)}")
        return False

if __name__ == "__main__":
    # Test with sample data
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            webhook_data = json.load(f)
        update_excel_file(webhook_data)