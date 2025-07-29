import os
import json
import requests
import pandas as pd
import sys
from datetime import datetime, timedelta
from io import BytesIO
from dotenv import load_dotenv
# SequenceMatcher removed - no longer needed
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation

# Import logging filter from root directory
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging
from warranty_form_data import WarrantyFormData

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

# Remove the old field parsing function since we now use WarrantyFormData

# Duplicate detection functions removed as requested

# Remove the old prepare_row_data function since we now use WarrantyFormData.to_excel_row()

def find_column_index(worksheet, column_name):
    """Find the column index for a given column name in the header row"""
    for col_idx, cell in enumerate(worksheet[1], 1):
        if cell.value == column_name:
            return col_idx
    return None

def find_first_empty_row_within_validation(worksheet, column_index):
    """Find the first empty row within the existing data validation range"""
    try:
        # Find the data validation range for our column
        validation_end_row = None
        
        for dv in worksheet.data_validations:
            for range_obj in dv.ranges:
                if range_obj.min_col <= column_index <= range_obj.max_col:
                    validation_end_row = range_obj.max_row
                    logger.info(f"Found data validation range ending at row {validation_end_row} for column {column_index}")
                    break
            if validation_end_row:
                break
        
        if not validation_end_row:
            logger.warning(f"No data validation found for column {column_index}")
            return None
            
        # Find the first empty row within the validation range
        # Check from row 2 (after headers) to the end of validation range
        for row in range(2, validation_end_row + 1):
            # Check if this row is empty (no ticket ID)
            ticket_id_cell = worksheet.cell(row=row, column=1)  # Assuming Ticket ID is in column 1
            if not ticket_id_cell.value or not str(ticket_id_cell.value).strip():
                logger.info(f"Found empty row {row} within validation range (ends at {validation_end_row})")
                return row
                
        # If no empty row found within range, we need to extend the validation
        logger.warning(f"No empty rows found within validation range (2-{validation_end_row})")
        return None
        
    except Exception as e:
        logger.error(f"Error finding empty row within validation range: {str(e)}")
        return None

def extend_data_validation_range(worksheet, column_index, new_row):
    """Extend existing data validation range to include the new row"""
    try:
        # Find all data validation rules that include our column
        validations_to_update = []
        
        for dv in list(worksheet.data_validations):
            for range_obj in dv.ranges:
                # Check if this range includes our Estado column
                if range_obj.min_col <= column_index <= range_obj.max_col:
                    validations_to_update.append((dv, range_obj))
                    logger.info(f"Found validation range: {range_obj.coord} (rows {range_obj.min_row}-{range_obj.max_row})")
                    break
        
        if not validations_to_update:
            logger.warning(f"No data validation found for column {column_index}")
            return
        
        # Update each validation rule
        for dv, matching_range in validations_to_update:
            # Check if new_row is already within the range
            if matching_range.min_row <= new_row <= matching_range.max_row:
                logger.info(f"Row {new_row} is already within validation range {matching_range.coord}")
                continue
                
            # Remove the old validation
            worksheet.data_validations.remove(dv)
            
            # Create new validation with same properties
            new_dv = DataValidation(
                type=dv.type,
                formula1=dv.formula1,
                formula2=dv.formula2,
                showDropDown=dv.showDropDown,
                showInputMessage=dv.showInputMessage,
                showErrorMessage=dv.showErrorMessage,
                errorTitle=dv.errorTitle,
                error=dv.error,
                promptTitle=dv.promptTitle,
                prompt=dv.prompt
            )
            
            # Add all ranges, extending the one that matches our column
            for range_obj in dv.ranges:
                if range_obj == matching_range:
                    # Extend this range to include the new row
                    start_col = range_obj.min_col
                    end_col = range_obj.max_col
                    start_row = range_obj.min_row
                    end_row = max(range_obj.max_row, new_row)
                    
                    # Create extended range string
                    start_cell = worksheet.cell(row=start_row, column=start_col).coordinate
                    end_cell = worksheet.cell(row=end_row, column=end_col).coordinate
                    extended_range = f"{start_cell}:{end_cell}"
                    
                    new_dv.add(extended_range)
                    logger.info(f"Extended data validation range from {range_obj.coord} to: {extended_range}")
                else:
                    # Keep original range for other columns
                    new_dv.add(range_obj.coord)
            
            # Add the updated validation rule
            worksheet.add_data_validation(new_dv)
            logger.info(f"Updated data validation for column {column_index}")
            
    except Exception as e:
        logger.error(f"Error extending data validation range: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def update_excel_file(form_data: WarrantyFormData):
    """Main function to update Excel file in Dropbox using WarrantyFormData object with openpyxl to preserve formatting"""
    try:
        brand = form_data.brand
        
        if not brand or brand == 'No especificado':
            raise Exception("Brand not found in form data")
        
        logger.info(f"Processing Excel update for brand: {brand}")
        logger.info(f"Form data ticket ID: {form_data.ticket_id}")
        
        # Get Dropbox credentials
        access_token = get_dropbox_access_token()
        folder_path = os.getenv('DROPBOX_FOLDER_PATH')
        file_path = f"{folder_path}/GARANTIAS_PROFFECTIV.xlsx"
        
        logger.info(f"Downloading Excel file from: {file_path}")
        
        # Download existing Excel file
        excel_file = download_excel_from_dropbox(access_token, file_path)
        
        # Load workbook with openpyxl to preserve formatting and data validation
        workbook = load_workbook(excel_file, data_only=False)
        
        logger.info(f"Available sheets in workbook: {workbook.sheetnames}")
        
        # Check if brand sheet exists
        if brand not in workbook.sheetnames:
            raise Exception(f"Sheet '{brand}' not found in Excel file")
        
        # Get the specific brand worksheet
        worksheet = workbook[brand]
        
        # Get column headers from first row to map data correctly
        headers = {}
        for col_idx, cell in enumerate(worksheet[1], 1):
            if cell.value:
                headers[cell.value] = col_idx
        
        logger.info(f"Excel headers found: {list(headers.keys())}")
        
        # Find all rows with ticket ID data to understand the data structure
        ticket_id_col = headers.get('Ticket ID', 1)
        estado_col = headers.get('Estado')
        
        # First, try to find an empty row within the existing data validation range
        next_row = None
        if estado_col:
            next_row = find_first_empty_row_within_validation(worksheet, estado_col)
        
        if next_row:
            logger.info(f"Found empty row {next_row} within existing data validation range")
        else:
            # Fallback to the original logic: find actual data rows and add after them
            data_rows = []
            
            # Scan a reasonable range to find actual data (not the full max_row which includes formatting)
            scan_range = min(worksheet.max_row + 1, 2000)  # Limit scan to prevent performance issues
            
            for row in range(2, scan_range):
                ticket_id = worksheet.cell(row=row, column=ticket_id_col).value
                if ticket_id and str(ticket_id).strip():
                    data_rows.append(row)
            
            if not data_rows:
                # No existing data, start at row 2
                next_row = 2
                logger.info("No existing data found, starting at row 2")
            else:
                # Find the last row with data and add after it
                actual_last_row = max(data_rows)
                first_data_row = min(data_rows)
                total_data_rows = len(data_rows)
                
                logger.info(f"Found {total_data_rows} data rows, range: {first_data_row}-{actual_last_row}")
                next_row = actual_last_row + 1
        
        current_max_row = worksheet.max_row
        
        logger.info(f"Worksheet max_row: {current_max_row}")
        logger.info(f"Will write to row: {next_row}")
        
        # Double-check that we're not overwriting existing data
        test_cell = worksheet.cell(row=next_row, column=ticket_id_col)
        if test_cell.value is not None:
            logger.warning(f"Row {next_row} already has data! Ticket ID: {test_cell.value}")
            # Find the actual next empty row
            for row in range(next_row, worksheet.max_row + 100):
                if worksheet.cell(row=row, column=ticket_id_col).value is None:
                    next_row = row
                    logger.info(f"Found actual empty row: {next_row}")
                    break
        
        # Prepare new row data using form_data
        new_row_data = form_data.to_excel_row(brand)
        
        logger.info(f"New row data keys: {list(new_row_data.keys())}")
        logger.info(f"New row data values: {list(new_row_data.values())}")
        
        # Write new row data to worksheet
        cells_written = 0
        estado_col_idx = None
        for column_name, value in new_row_data.items():
            if column_name in headers:
                col_idx = headers[column_name]
                cell = worksheet.cell(row=next_row, column=col_idx)
                old_value = cell.value
                cell.value = value
                cells_written += 1
                
                # Remember Estado column for validation extension
                if column_name == 'Estado':
                    estado_col_idx = col_idx
                
                logger.info(f"Writing to cell {cell.coordinate} (row {next_row}, col {col_idx}): '{column_name}' = '{value}' (was: '{old_value}')")
            else:
                logger.warning(f"Column '{column_name}' not found in Excel headers")
        
        # After writing all data, extend data validation for Estado column if needed
        if estado_col_idx:
            extend_data_validation_range(worksheet, estado_col_idx, next_row)
        
        logger.info(f"Total cells written: {cells_written}")
        
        # Verify the data was written by checking a few key cells
        verification_cells = ['Ticket ID', 'Estado', 'Empresa']
        for col_name in verification_cells:
            if col_name in headers:
                col_idx = headers[col_name]
                cell_value = worksheet.cell(row=next_row, column=col_idx).value
                logger.info(f"Verification - {col_name}: '{cell_value}'")
        
        # Check new max row after writing
        new_max_row = worksheet.max_row
        logger.info(f"New max row after writing: {new_max_row} (should be {next_row})")
        
        # Save workbook to BytesIO
        logger.info("Saving workbook to BytesIO...")
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        
        # Get size of saved data
        saved_size = len(output.getvalue())
        logger.info(f"Saved Excel file size: {saved_size} bytes")
        
        if saved_size == 0:
            raise Exception("Saved Excel file is empty!")
        
        # Upload updated file back to Dropbox
        logger.info("Uploading file to Dropbox...")
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
        form_data = WarrantyFormData(webhook_data, "test-ticket-123")
        update_excel_file(form_data)