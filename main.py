#!/usr/bin/env python3
"""
Main orchestrator script for warranty form automation
This script processes webhook data from Tally forms and performs all necessary actions
"""

import json
import sys
import uuid
from datetime import datetime

from send_confirmation_email import send_confirmation_email
from send_notification_email import send_notification_email
from update_excel_dropbox import update_excel_file

def process_warranty_form(webhook_data):
    """
    Process warranty form submission by:
    1. Generating unique ticket ID
    2. Sending confirmation email to client
    3. Updating Excel file in Dropbox
    4. Sending notification email to admin
    """
    
    print("🚀 Starting warranty form processing...")
    print(f"Event ID: {webhook_data.get('eventId', 'N/A')}")
    print(f"Event Type: {webhook_data.get('eventType', 'N/A')}")
    
    if webhook_data.get('eventType') != 'FORM_RESPONSE':
        print("❌ Invalid event type. Expected 'FORM_RESPONSE'")
        return False
    
    # Generate unique ticket ID
    ticket_id = str(uuid.uuid4())
    print(f"🎫 Generated Ticket ID: {ticket_id}")
    
    # Add ticket ID to webhook data for other functions to use
    webhook_data['data']['ticket_id'] = ticket_id
    
    results = {
        'confirmation_email': False,
        'excel_update': False,
        'notification_email': False
    }
    
    # Step 1: Send confirmation email to client
    print("\n📧 Sending confirmation email to client...")
    try:
        results['confirmation_email'] = send_confirmation_email(webhook_data)
        if results['confirmation_email']:
            print("✅ Confirmation email sent successfully")
        else:
            print("❌ Failed to send confirmation email")
    except Exception as e:
        print(f"❌ Error sending confirmation email: {str(e)}")
    
    # Step 2: Update Excel file in Dropbox
    print("\n📊 Updating Excel file in Dropbox...")
    try:
        results['excel_update'] = update_excel_file(webhook_data)
        if results['excel_update']:
            print("✅ Excel file updated successfully")
        else:
            print("❌ Failed to update Excel file")
    except Exception as e:
        print(f"❌ Error updating Excel file: {str(e)}")
    
    # Step 3: Send notification email to admin
    print("\n🔔 Sending notification email to admin...")
    try:
        results['notification_email'] = send_notification_email(webhook_data)
        if results['notification_email']:
            print("✅ Notification email sent successfully")
        else:
            print("❌ Failed to send notification email")
    except Exception as e:
        print(f"❌ Error sending notification email: {str(e)}")
    
    # Summary
    print("\n📋 Processing Summary:")
    print(f"   Confirmation Email: {'✅' if results['confirmation_email'] else '❌'}")
    print(f"   Excel Update: {'✅' if results['excel_update'] else '❌'}")
    print(f"   Notification Email: {'✅' if results['notification_email'] else '❌'}")
    
    success_count = sum(results.values())
    print(f"\n🎯 {success_count}/3 tasks completed successfully")
    
    if success_count == 3:
        print("🎉 All warranty processing tasks completed successfully!")
        return True
    else:
        print("⚠️  Some tasks failed. Please check the logs above.")
        return False

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python main.py <webhook_data.json>")
        print("Example: python main.py webhook_data.json")
        sys.exit(1)
    
    webhook_file = sys.argv[1]
    
    try:
        with open(webhook_file, 'r', encoding='utf-8') as f:
            webhook_data = json.load(f)
        
        success = process_warranty_form(webhook_data)
        sys.exit(0 if success else 1)
        
    except FileNotFoundError:
        print(f"❌ Error: File '{webhook_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{webhook_file}': {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()