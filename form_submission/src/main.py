#!/usr/bin/env python3
"""
Main orchestrator script for warranty form automation
This script processes webhook data from Tally forms and performs all necessary actions
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
from update_excel_dropbox import update_excel_file, check_for_duplicates

# Set up secure logging
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
    
    if webhook_data.get('eventType') != 'form-submission':
        logger.error("Invalid event type. Expected 'form-submission'")
        return False
    
    # Check for duplicates before processing
    logger.info("Checking for duplicate submissions")
    is_duplicate, probability, details = check_for_duplicates(webhook_data)
    
    if is_duplicate:
        logger.warning(f"DUPLICATE DETECTED! Probability: {probability:.2%}")
        logger.info(f"Threshold: {details['threshold']:.2%}")
        logger.info(f"Brand: {details['brand']}")
        
        if details['similar_record']:
            logger.info("Most similar record factors:")
            for factor_name, score, weight in details['similar_record']['factors']:
                logger.info(f"Factor {factor_name}: {score:.1%} (weight: {weight:.1%})")
        
        logger.warning("Automation STOPPED - Duplicate submission detected")
        return False
    else:
        logger.info(f"No duplicates found (probability: {probability:.2%})")
    
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
    logger.info("Processing Summary:")
    logger.info(f"Confirmation Email: {'SUCCESS' if results['confirmation_email'] else 'FAILED'}")
    logger.info(f"Excel Update: {'SUCCESS' if results['excel_update'] else 'FAILED'}")
    logger.info(f"Notification Email: {'SUCCESS' if results['notification_email'] else 'FAILED'}")
    
    success_count = sum(results.values())
    logger.info(f"{success_count}/3 tasks completed successfully")
    
    if success_count == 3:
        logger.info("All warranty processing tasks completed successfully!")
        return True
    else:
        logger.warning("Some tasks failed. Check previous log entries for details.")
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