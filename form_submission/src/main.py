#!/usr/bin/env python3
"""
Warranty Form Submission Processor
Handles webhook data from Tally forms and processes warranty submissions
"""

import json
import sys
import uuid
from datetime import datetime

# Import logging filter from root directory
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

from send_confirmation_email import send_confirmation_email
from send_notification_email import send_notification_email
from update_excel_dropbox import update_excel_file

# Initialize logger
logger = setup_secure_logging('main')

def process_warranty_form(webhook_data):
    """
    Process warranty form submission by:
    1. Generating unique ticket ID
    2. Sending confirmation email to client
    3. Updating Excel file in Dropbox
    4. Sending notification email to admin
    """
    
    logger.info("Starting warranty form processing")
    logger.info(f"Event ID: {webhook_data.get('eventId', 'N/A')}")
    logger.info(f"Event Type: {webhook_data.get('eventType', 'N/A')}")
    
    valid_event_types = ['form-submission', 'FORM_RESPONSE']
    if webhook_data.get('eventType') not in valid_event_types:
        logger.error(f"Invalid event type. Expected one of: {valid_event_types}")
        return False
    
    # Generate unique ticket ID
    ticket_id = str(uuid.uuid4())
    logger.info(f"Generated Ticket ID: {ticket_id}")
    
    # Add ticket ID to webhook data for other functions to use
    webhook_data['data']['ticket_id'] = ticket_id
    
    results = {
        'confirmation_email': False,
        'excel_update': False,
        'notification_email': False
    }
    
    # Step 1: Send confirmation email to client
    logger.info("Sending confirmation email to client")
    try:
        results['confirmation_email'] = send_confirmation_email(webhook_data)
        if results['confirmation_email']:
            logger.info("Confirmation email sent successfully")
        else:
            logger.error("Failed to send confirmation email")
    except Exception as e:
        logger.error(f"Error sending confirmation email: {str(e)}")
    
    # Step 2: Update Excel file in Dropbox
    logger.info("Updating Excel file in Dropbox")
    try:
        results['excel_update'] = update_excel_file(webhook_data)
        if results['excel_update']:
            logger.info("Excel file updated successfully")
        else:
            logger.error("Failed to update Excel file")
    except Exception as e:
        logger.error(f"Error updating Excel file: {str(e)}")
    
    # Step 3: Send notification email to admin
    logger.info("Sending notification email to admin")
    try:
        results['notification_email'] = send_notification_email(webhook_data)
        if results['notification_email']:
            logger.info("Notification email sent successfully")
        else:
            logger.error("Failed to send notification email")
    except Exception as e:
        logger.error(f"Error sending notification email: {str(e)}")
    
    # Summary
    successful_tasks = sum(results.values())
    total_tasks = len(results)
    
    logger.info("Processing Summary:")
    logger.info(f"Confirmation Email: {'SUCCESS' if results['confirmation_email'] else 'FAILED'}")
    logger.info(f"Excel Update: {'SUCCESS' if results['excel_update'] else 'FAILED'}")
    logger.info(f"Notification Email: {'SUCCESS' if results['notification_email'] else 'FAILED'}")
    logger.info(f"{successful_tasks}/{total_tasks} tasks completed successfully")
    
    if successful_tasks == total_tasks:
        logger.info("All warranty processing tasks completed successfully!")
        return True
    else:
        logger.warning("Some tasks failed. Check previous log entries for details.")
        return False

def adapt_webhook_structure(webhook_data):
    """
    Adapt webhook data structure for compatibility between old and new formats.
    """
    logger.info(f"Input webhook keys: {list(webhook_data.keys())}")
    
    # Determine webhook structure and extract fields
    fields = None
    event_id = None
    
    if 'client_payload' in webhook_data and 'fields' in webhook_data['client_payload']:
        logger.info("Detected GitHub webhook structure with client_payload")
        fields = webhook_data['client_payload']['fields']
        event_id = webhook_data.get('event_type', 'github-webhook')
    elif 'eventType' in webhook_data and 'fields' in webhook_data and isinstance(webhook_data['fields'], dict):
        logger.info("Detected direct fields webhook structure")
        fields = webhook_data['fields']
        event_id = webhook_data.get('eventId', 'direct-webhook')
    else:
        logger.info("Using original webhook data structure (old format)")
        return webhook_data
    
    # Convert new format to old format
    adapted = {
        'eventId': event_id,
        'eventType': 'form-submission',
        'createdAt': datetime.now().isoformat() + 'Z',
        'data': {
            'fields': [],
            'createdAt': datetime.now().isoformat() + 'Z',
            'responseId': 'GITHUB-' + str(hash(str(fields)))[-8:],
            'submissionId': 'GITHUB-' + str(hash(str(fields)))[-8:],
            'respondentId': 'GitHubWebhook'
        }
    }
    
    # Field mapping for compatibility
    field_mapping = {
        'Empresa': 'question_59JjXb',
        'NIF/CIF/VAT': 'question_d0OabN',
        'Email': 'question_oRq2oM',
        'Marca del Producto': 'question_YG10j0',
        'Conway - Por favor, indica el nombre completo del modelo (ej. Cairon C 2.0 500)': 'question_Dpjkqp',
        'Conway - Talla': 'question_lOxea6',
        'Conway - Año de fabricación': 'question_RoAMWP',
        'Conway - Estado de la bicicleta': 'question_oRqe9M',
        'Conway - Descripción del problema': 'question_GpZ9ez',
        'Conway - Solución o reparación propuesta y presupuesto aproximado': 'question_OX64QA',
        'Cycplus - Modelo': 'question_2Apa7p',
        'Cycplus - Estado del Producto': 'question_xDAMvG',
        'Cycplus - Descripción del problema': 'question_RoAMkp',
        'Dare - Modelo': 'question_GpZ952',
        'Dare - Talla': 'question_OX64kp',
        'Dare - Año de fabricación': 'question_VPKQNE',
        'Dare - Estado de la bicicleta': 'question_P971rd',
        'Dare - Descripción del problema': 'question_El2d6q',
        'Dare - Solución o reparación propuesta y presupuesto aproximado': 'question_rOeaY5',
        'Adjunta la factura de compra': 'question_GpZlqz',
        'Conway - Adjunta la factura de compra a Hartje': 'question_VPKQpl',
        'Conway - Adjunta la factura de venta': 'question_P971R0',
        'Cycplus - Adjunta la factura de venta': 'question_oRqevX',
        'Dare - Adjunta la factura de compra': 'question_OX6GbA',
        'Dare - Adjunta la factura de venta': 'question_47MJOB'
    }
    
    # Convert fields to old format
    for key, value in fields.items():
        mapped_key = field_mapping.get(key, key)
        
        # Determine field type
        field_type = 'INPUT_TEXT'
        if 'Email' in key:
            field_type = 'INPUT_EMAIL'
        elif 'Descripción' in key or 'problema' in key or 'Solución' in key:
            field_type = 'TEXTAREA'
        elif 'Marca del Producto' in key or 'Modelo' in key or 'Estado' in key or 'Talla' in key:
            field_type = 'DROPDOWN'
        elif 'factura' in key.lower() or 'adjunta' in key.lower():
            field_type = 'FILE_UPLOAD'
        
        field_obj = {
            'key': mapped_key,
            'label': key,
            'type': field_type,
            'value': value
        }
        
        # Add options for brand field
        if key == 'Marca del Producto':
            field_obj['options'] = [
                {'id': 'Conway', 'text': 'Conway'},
                {'id': 'Cycplus', 'text': 'Cycplus'},
                {'id': 'Dare', 'text': 'Dare'},
                {'id': 'Kogel', 'text': 'Kogel'}
            ]
            
        adapted['data']['fields'].append(field_obj)
    
    return adapted

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        logger.error("Usage: python main.py <webhook_data.json>")
        logger.error("Example: python main.py webhook_data.json")
        sys.exit(1)
    
    webhook_file = sys.argv[1]
    
    try:
        with open(webhook_file, 'r', encoding='utf-8') as f:
            webhook_data = json.load(f)
        
        logger.info(f"Processing webhook data from file: {webhook_file}")
        
        # Adapt webhook data structure for compatibility
        adapted_data = adapt_webhook_structure(webhook_data)
        
        # Debug logging
        logger.info(f"Adapted data keys: {list(adapted_data.keys())}")
        if 'data' in adapted_data:
            logger.info(f"Data keys: {list(adapted_data['data'].keys())}")
        else:
            logger.error("Missing 'data' key in adapted webhook data!")
            logger.error(f"Full adapted structure: {adapted_data}")
            sys.exit(1)
        
        success = process_warranty_form(adapted_data)
        sys.exit(0 if success else 1)
        
    except FileNotFoundError:
        logger.error(f"File not found: {webhook_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {webhook_file}: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()