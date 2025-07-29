#!/usr/bin/env python3
"""
Main Status Update Notification Automation
Daily automation to check warranty status changes and send client notifications
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Import logging filter from root directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

# Import local modules
from excel_reader import ExcelReader
from status_tracker import StatusTracker
from email_sender import EmailSender
from email_templates import get_supported_statuses

load_dotenv()

# Set up secure logging
logger = setup_secure_logging('status_update_main')

def main():
    """Main function to orchestrate status update notification process"""
    
    logger.info("=" * 60)
    logger.info("STARTING STATUS UPDATE NOTIFICATION AUTOMATION")
    logger.info(f"Execution time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        excel_reader = ExcelReader()
        status_tracker = StatusTracker()
        email_sender = EmailSender()
        
        # Test SMTP connection first
        logger.info("Testing SMTP connection...")
        if not email_sender.test_smtp_connection():
            logger.error("SMTP connection failed. Aborting automation.")
            return False
        
        logger.info("✅ All components initialized successfully")
        
        # Step 1: Read current ticket statuses from Excel
        logger.info("Step 1: Reading current ticket statuses from Excel...")
        current_tickets = excel_reader.get_all_tickets_status()
        
        if not current_tickets:
            logger.warning("No tickets found in Excel file. Exiting.")
            return True
        
        total_tickets = sum(len(tickets) for tickets in current_tickets.values())
        logger.info(f"Found {total_tickets} total tickets across all brands")
        
        for brand, tickets in current_tickets.items():
            logger.info(f"- {brand}: {len(tickets)} tickets")
        
        # Step 2: Detect status changes requiring notifications
        logger.info("Step 2: Detecting status changes requiring notifications...")
        status_changes = status_tracker.detect_status_changes(current_tickets)
        
        logger.info(f"Found {len(status_changes)} status changes requiring notification")
        
        if not status_changes:
            logger.info("No status changes detected. Updating history and exiting.")
            status_tracker.update_status_history(current_tickets)
            return True
        
        # Log detected changes
        for change in status_changes:
            ticket_id = change['ticket_data'].get('Ticket ID', 'N/A')
            logger.info(f"- {ticket_id}: {change['previous_status']} -> {change['current_status']}")
        
        # Step 3: Send notification emails
        logger.info("Step 3: Sending status update emails...")
        email_results = email_sender.send_batch_status_updates(status_changes)
        
        logger.info(f"Email sending results:")
        logger.info(f"- Total: {email_results['total_emails']}")
        logger.info(f"- Sent successfully: {email_results['sent_successfully']}")
        logger.info(f"- Failed: {email_results['failed']}")
        
        # Step 4: Update status history
        logger.info("Step 4: Updating status history...")
        status_tracker.update_status_history(current_tickets)
        
        # Step 5: Send admin summary email
        logger.info("Step 5: Sending admin summary email...")
        admin_email_sent = email_sender.send_summary_email_to_admin(email_results)
        
        if admin_email_sent:
            logger.info("✅ Admin summary email sent successfully")
        else:
            logger.warning("⚠️ Admin summary email failed or not configured")
        
        # Step 6: Cleanup old entries (optional)
        logger.info("Step 6: Cleaning up old status history entries...")
        status_tracker.cleanup_old_entries(days_old=30)
        
        # Final summary
        logger.info("=" * 60)
        logger.info("STATUS UPDATE NOTIFICATION AUTOMATION COMPLETED")
        logger.info(f"- Processed {total_tickets} total tickets")
        logger.info(f"- Detected {len(status_changes)} status changes")
        logger.info(f"- Sent {email_results['sent_successfully']} notifications successfully")
        logger.info(f"- Failed {email_results['failed']} notifications")
        logger.info(f"Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # Return success if all notifications sent or only minor failures
        success_rate = email_results['sent_successfully'] / max(email_results['total_emails'], 1)
        return success_rate >= 0.8  # 80% success rate threshold
        
    except Exception as e:
        logger.error(f"Fatal error in status update automation: {str(e)}")
        logger.error("=" * 60)
        logger.error("STATUS UPDATE NOTIFICATION AUTOMATION FAILED")
        logger.error("=" * 60)
        return False

def get_status_summary():
    """Get current status tracking summary for monitoring"""
    try:
        status_tracker = StatusTracker()
        summary = status_tracker.get_status_summary()
        
        print("Current Status Tracking Summary:")
        print("=" * 40)
        print(f"Total tracked tickets: {summary.get('total_tracked_tickets', 0)}")
        print(f"Last updated: {summary.get('last_updated', 'Never')}")
        print(f"Notification statuses: {', '.join(get_supported_statuses())}")
        
        if summary.get('status_breakdown'):
            print("\nStatus breakdown:")
            for status, count in summary['status_breakdown'].items():
                print(f"  {status}: {count}")
        
        if summary.get('brand_breakdown'):
            print("\nBrand breakdown:")
            for brand, count in summary['brand_breakdown'].items():
                print(f"  {brand}: {count}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting status summary: {str(e)}")
        return None

def test_components():
    """Test all components individually"""
    print("Testing Status Update Notification Components...")
    print("=" * 60)
    
    success = True
    
    # Test Excel Reader
    try:
        print("Testing Excel Reader...")
        excel_reader = ExcelReader()
        tickets = excel_reader.get_all_tickets_status()
        total = sum(len(t) for t in tickets.values())
        print(f"✅ Excel Reader: Found {total} tickets")
    except Exception as e:
        print(f"❌ Excel Reader failed: {str(e)}")
        success = False
    
    # Test Status Tracker
    try:
        print("Testing Status Tracker...")
        status_tracker = StatusTracker()
        summary = status_tracker.get_status_summary()
        print(f"✅ Status Tracker: Tracking {summary.get('total_tracked_tickets', 0)} tickets")
    except Exception as e:
        print(f"❌ Status Tracker failed: {str(e)}")
        success = False
    
    # Test Email Sender
    try:
        print("Testing Email Sender...")
        email_sender = EmailSender()
        if email_sender.test_smtp_connection():
            print("✅ Email Sender: SMTP connection successful")
        else:
            print("❌ Email Sender: SMTP connection failed")
            success = False
    except Exception as e:
        print(f"❌ Email Sender failed: {str(e)}")
        success = False
    
    print("=" * 60)
    if success:
        print("✅ All components tested successfully")
    else:
        print("❌ Some components failed testing")
    
    return success

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "summary":
            get_status_summary()
        elif sys.argv[1] == "test":
            test_components()
        else:
            print("Usage: python main.py [summary|test]")
            print("  summary: Show current status tracking summary")
            print("  test: Test all components")
            print("  (no args): Run full automation")
    else:
        # Run main automation
        success = main()
        exit(0 if success else 1)