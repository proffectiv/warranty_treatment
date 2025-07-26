import os
import json
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

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

def get_brand_display_name(brand_id, options):
    """Get brand display name from options"""
    for option in options:
        if option['id'] == brand_id:
            return option['text']
    return 'Desconocida'

def get_field_value(fields, key):
    """Extract field value from form fields"""
    for field in fields:
        if field['key'] == key:
            if field['type'] == 'DROPDOWN' and field['value']:
                if isinstance(field['value'], list) and len(field['value']) > 0:
                    return get_brand_display_name(field['value'][0], field.get('options', []))
                return field['value']
            elif field['type'] == 'FILE_UPLOAD' and field['value']:
                if isinstance(field['value'], list) and len(field['value']) > 0:
                    return field['value'][0]['url']
                return 'Archivo adjunto'
            return field['value'] if field['value'] else ''
    return ''

def prepare_row_data(form_data, brand):
    """Prepare row data based on brand"""
    fields = form_data['fields']
    fecha_creacion = datetime.fromisoformat(form_data['createdAt'].replace('Z', '+00:00')).strftime('%d/%m/%Y')
    ticket_id = form_data.get('ticket_id', 'No disponible')
    
    # Common fields
    empresa = get_field_value(fields, 'question_59JjXb')
    nif_cif = get_field_value(fields, 'question_d0OabN')
    email = get_field_value(fields, 'question_oRq2oM')
    
    if brand == 'Conway':
        row_data = {
            'Ticket ID': ticket_id,
            'Estado': 'Abierto',
            'Fecha de creación': fecha_creacion,
            'Empresa': empresa,
            'NIF/CIF/VAT': nif_cif,
            'Email': email,
            'Modelo': get_field_value(fields, 'question_Dpjkqp'),
            'Talla': get_field_value(fields, 'question_lOxea6'),
            'Año de fabricación': get_field_value(fields, 'question_RoAMWP'),
            'Estado de la bicicleta': get_field_value(fields, 'question_oRqe9M'),
            'Descripción del problema': get_field_value(fields, 'question_GpZ9ez'),
            'Solución y/o reparación propuesta y presupuesto': get_field_value(fields, 'question_OX64QA'),
            'Factura de compra': get_field_value(fields, 'question_VPKQpl'),
            'Factura de venta': get_field_value(fields, 'question_P971R0')
        }
    elif brand == 'Cycplus':
        row_data = {
            'Ticket ID': ticket_id,
            'Estado': 'Abierto',
            'Fecha de creación': fecha_creacion,
            'Empresa': empresa,
            'NIF/CIF/VAT': nif_cif,
            'Email': email,
            'Modelo': get_field_value(fields, 'question_2Apa7p'),
            'Estado del producto': get_field_value(fields, 'question_xDAMvG'),
            'Descripción del problema': get_field_value(fields, 'question_RoAMkp'),
            'Solución y/o reparación propuesta y presupuesto': '',  # Not applicable for Cycplus
            'Factura de compra': get_field_value(fields, 'question_GpZlqz'),
            'Factura de venta': get_field_value(fields, 'question_oRqevX')
        }
    elif brand == 'Dare':
        row_data = {
            'Ticket ID': ticket_id,
            'Estado': 'Abierto',
            'Fecha de creación': fecha_creacion,
            'Empresa': empresa,
            'NIF/CIF/VAT': nif_cif,
            'Email': email,
            'Modelo': get_field_value(fields, 'question_GpZ952'),
            'Talla': get_field_value(fields, 'question_OX64kp'),
            'Estado de la bicicleta': get_field_value(fields, 'question_P971rd'),
            'Descripción del problema': get_field_value(fields, 'question_El2d6q'),
            'Solución y/o reparación propuesta y presupuesto': get_field_value(fields, 'question_rOeaY5'),
            'Factura de compra': get_field_value(fields, 'question_OX6GbA'),
            'Factura de venta': get_field_value(fields, 'question_47MJOB')
        }
    elif brand == 'Kogel':
        # Kogel structure similar to others - add if needed
        row_data = {
            'Ticket ID': ticket_id,
            'Estado': 'Abierto',
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
        form_data = webhook_data['data']
        
        # Get brand from form
        brand = None
        for field in form_data['fields']:
            if field['key'] == 'question_YG10j0':
                if field['value'] and isinstance(field['value'], list):
                    brand = get_brand_display_name(field['value'][0], field.get('options', []))
                break
        
        if not brand:
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
        new_row = prepare_row_data(form_data, brand)
        
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
        
        print(f"Excel file updated successfully. New row added to {brand} sheet.")
        print(f"File uploaded to Dropbox: {upload_result.get('path_display', file_path)}")
        
        return True
        
    except Exception as e:
        print(f"Error updating Excel file: {str(e)}")
        return False

if __name__ == "__main__":
    # Test with sample data
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            webhook_data = json.load(f)
        update_excel_file(webhook_data)