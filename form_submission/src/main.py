#!/usr/bin/env python3
"""
Warranty Form Submission Processor
Handles webhook data from Tally forms and processes warranty submissions
"""

import json
import sys
import uuid

# Import logging filter from root directory
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

from send_confirmation_email import send_confirmation_email
from send_notification_email import send_notification_email
from send_conway_notification_email import send_conway_notification_email
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
    
    # Handle different webhook structures
    if 'fields' in webhook_data and 'fieldsById' in webhook_data:
        # GitHub action webhook structure (direct client_payload)
        logger.info(f"Event Type: {webhook_data.get('eventType', 'N/A')}")
        event_type = webhook_data.get('eventType', 'form-submission')
    elif 'client_payload' in webhook_data:
        # GitHub webhook structure with client_payload
        logger.info(f"Event Type: {webhook_data.get('event_type', 'N/A')}")
        event_type = webhook_data.get('event_type', 'form-submission')
    else:
        # Old structure
        logger.info(f"Event ID: {webhook_data.get('eventId', 'N/A')}")
        logger.info(f"Event Type: {webhook_data.get('eventType', 'N/A')}")
        event_type = webhook_data.get('eventType', 'form-submission')
    
    valid_event_types = ['form-submission', 'FORM_RESPONSE']
    if event_type not in valid_event_types:
        logger.error(f"Invalid event type. Expected one of: {valid_event_types}")
        return False
    
    # Generate unique ticket ID
    ticket_id = str(uuid.uuid4())
    logger.info(f"Generated Ticket ID: {ticket_id}")
    
    # Add ticket ID to webhook data for other functions to use
    webhook_data['ticket_id'] = ticket_id
    
    # Extract brand for Conway-specific logic using the same logic as other email functions
    if 'fields' in webhook_data and 'fieldsById' in webhook_data:
        fields = webhook_data['fields']
    elif 'client_payload' in webhook_data:
        fields = webhook_data['client_payload']['fields']
    else:
        form_data = webhook_data.get('data', webhook_data)
        fields = {field['label']: field['value'] for field in form_data.get('fields', [])}
    
    # Get brand from fields using the same function as email modules
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
    
    brand = get_field_value_by_name(fields, 'Marca del Producto')
    logger.info(f"Processing warranty for brand: {brand}")
    
    results = {
        'confirmation_email': False,
        'excel_update': False,
        'notification_email': False,
        'conway_notification': False
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
    
    # Step 4: Send Conway-specific notification email if brand is Conway
    if brand == 'Conway':
        logger.info("Sending Conway-specific notification email")
        try:
            results['conway_notification'] = send_conway_notification_email(webhook_data)
            if results['conway_notification']:
                logger.info("Conway notification email sent successfully")
            else:
                logger.error("Failed to send Conway notification email")
        except Exception as e:
            logger.error(f"Error sending Conway notification email: {str(e)}")
    else:
        logger.info(f"Brand is '{brand}', skipping Conway notification email")
        results['conway_notification'] = True  # Mark as successful since it's not needed
    
    # Summary
    successful_tasks = sum(results.values())
    total_tasks = len(results)
    
    logger.info("Processing Summary:")
    logger.info(f"Confirmation Email: {'SUCCESS' if results['confirmation_email'] else 'FAILED'}")
    logger.info(f"Excel Update: {'SUCCESS' if results['excel_update'] else 'FAILED'}")
    logger.info(f"Notification Email: {'SUCCESS' if results['notification_email'] else 'FAILED'}")
    if brand == 'Conway':
        logger.info(f"Conway Notification Email: {'SUCCESS' if results['conway_notification'] else 'FAILED'}")
    logger.info(f"{successful_tasks}/{total_tasks} tasks completed successfully")
    
    if successful_tasks == total_tasks:
        logger.info("All warranty processing tasks completed successfully!")
        return True
    else:
        logger.warning("Some tasks failed. Check previous log entries for details.")
        return False

def validate_webhook_structure(webhook_data):
    """
    Validate webhook data structure and log relevant information.
    """
    logger.info(f"Input webhook keys: {list(webhook_data.keys())}")
    
    if 'fields' in webhook_data and 'fieldsById' in webhook_data:
        logger.info("Detected GitHub action webhook structure (direct client_payload)")
        fields = webhook_data['fields']
        logger.info(f"Found {len(fields)} fields in payload")
        return True
    elif 'client_payload' in webhook_data and 'fields' in webhook_data['client_payload']:
        logger.info("Detected GitHub webhook structure with client_payload")
        fields = webhook_data['client_payload']['fields']
        logger.info(f"Found {len(fields)} fields in payload")
        return True
    elif 'data' in webhook_data and 'fields' in webhook_data['data']:
        logger.info("Detected old webhook structure with data.fields")
        fields = webhook_data['data']['fields']
        logger.info(f"Found {len(fields)} fields in payload")
        return True
    else:
        logger.error("Unknown webhook structure")
        return False

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
        
        # Validate webhook data structure
        if not validate_webhook_structure(webhook_data):
            logger.error("Invalid webhook structure")
            sys.exit(1)
        
        success = process_warranty_form(webhook_data)
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