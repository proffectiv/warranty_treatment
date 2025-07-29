#!/usr/bin/env python3
"""
Email Sender for Status Update Notifications
Sends status update emails to clients using existing SMTP configuration
"""

import os
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from dotenv import load_dotenv

# Import logging filter from root directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging
from email_templates import create_status_update_email

load_dotenv()

# Set up secure logging
logger = setup_secure_logging('email_sender')

class EmailSender:
    """Handles sending status update emails to clients"""
    
    def __init__(self):
        """Initialize email sender with SMTP configuration"""
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        
        # Validate configuration
        if not all([self.smtp_host, self.smtp_port, self.smtp_username, self.smtp_password]):
            raise Exception("Missing SMTP configuration in environment variables")
        
        logger.info("Email sender initialized with SMTP configuration")
    
    def send_status_update_email(self, ticket_data: Dict[str, Any], new_status: str) -> bool:
        """
        Send status update email to client
        
        Args:
            ticket_data: Dictionary containing ticket information
            new_status: New status value (Tramitada, Aceptada, Denegada)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create email content using template
            html_content, subject, client_email = create_status_update_email(ticket_data, new_status)
            
            if not html_content or not client_email:
                logger.error("Failed to create email template or missing client email")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_username
            msg['To'] = client_email
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            ticket_id = ticket_data.get('Ticket ID', 'N/A')
            logger.info(f"Status update email sent successfully for ticket {ticket_id} to {client_email}")
            return True
            
        except Exception as e:
            ticket_id = ticket_data.get('Ticket ID', 'N/A')
            logger.error(f"Error sending status update email for ticket {ticket_id}: {str(e)}")
            return False
    
    def send_batch_status_updates(self, status_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send multiple status update emails
        
        Args:
            status_changes: List of status change dictionaries
            
        Returns:
            Dictionary with results summary
        """
        results = {
            'total_emails': len(status_changes),
            'sent_successfully': 0,
            'failed': 0,
            'failed_tickets': []
        }
        
        logger.info(f"Starting batch email sending for {len(status_changes)} status changes")
        
        for change in status_changes:
            ticket_data = change['ticket_data']
            new_status = change['current_status']
            ticket_id = ticket_data.get('Ticket ID', 'N/A')
            
            try:
                success = self.send_status_update_email(ticket_data, new_status)
                
                if success:
                    results['sent_successfully'] += 1
                    logger.info(f"✅ Email sent for ticket {ticket_id} - Status: {new_status}")
                else:
                    results['failed'] += 1
                    results['failed_tickets'].append({
                        'ticket_id': ticket_id,
                        'status': new_status,
                        'error': 'Email sending failed'
                    })
                    logger.error(f"❌ Email failed for ticket {ticket_id}")
                
            except Exception as e:
                results['failed'] += 1
                results['failed_tickets'].append({
                    'ticket_id': ticket_id,
                    'status': new_status,
                    'error': str(e)
                })
                logger.error(f"❌ Error processing ticket {ticket_id}: {str(e)}")
        
        logger.info(f"Batch email sending completed: {results['sent_successfully']} sent, {results['failed']} failed")
        return results
    
    def send_summary_email_to_admin(self, results: Dict[str, Any]) -> bool:
        """
        Send summary email to admin about status update notifications
        
        Args:
            results: Results from batch email sending
            
        Returns:
            True if admin email sent successfully
        """
        try:
            admin_email = os.getenv('NOTIFICATION_EMAIL')
            if not admin_email:
                logger.warning("No admin email configured for summary notifications")
                return False
            
            # Create summary email content
            subject = f"📊 Status Update Notifications - Daily Summary"
            
            html_content = f"""
            <html>
            <body>
                <h2>Status Update Notifications - Daily Summary</h2>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3>Email Sending Results</h3>
                    <ul>
                        <li><strong>Total notifications processed:</strong> {results['total_emails']}</li>
                        <li><strong>Successfully sent:</strong> {results['sent_successfully']}</li>
                        <li><strong>Failed:</strong> {results['failed']}</li>
                    </ul>
                </div>
                
                {self._create_failed_tickets_section(results.get('failed_tickets', []))}
                
                <p>This is an automated summary from the warranty status update notification system.</p>
                
                <br>
                <p>Automation System - PROFFECTIV</p>
            </body>
            </html>
            """
            
            # Create and send message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_username
            msg['To'] = admin_email
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Admin summary email sent successfully to {admin_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending admin summary email: {str(e)}")
            return False
    
    def _create_failed_tickets_section(self, failed_tickets: List[Dict[str, Any]]) -> str:
        """Create HTML section for failed tickets"""
        if not failed_tickets:
            return """
            <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
                <h3>✅ All Notifications Sent Successfully</h3>
                <p>No failed notifications to report.</p>
            </div>
            """
        
        failed_list = ""
        for ticket in failed_tickets:
            failed_list += f"""
            <li>
                <strong>Ticket:</strong> {ticket.get('ticket_id', 'N/A')} - 
                <strong>Status:</strong> {ticket.get('status', 'N/A')} - 
                <strong>Error:</strong> {ticket.get('error', 'Unknown error')}
            </li>
            """
        
        return f"""
        <div style="background-color: #f8d7da; padding: 15px; border-left: 4px solid #dc3545; margin: 20px 0;">
            <h3>❌ Failed Notifications</h3>
            <p>The following notifications failed to send:</p>
            <ul>
                {failed_list}
            </ul>
        </div>
        """
    
    def test_smtp_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
            logger.info("SMTP connection test successful")
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {str(e)}")
            return False

if __name__ == "__main__":
    # Test the email sender
    try:
        sender = EmailSender()
        
        print("Testing Email Sender...")
        print("=" * 50)
        
        # Test SMTP connection
        if sender.test_smtp_connection():
            print("✅ SMTP connection successful")
        else:
            print("❌ SMTP connection failed")
            exit(1)
        
        # Test email template creation and sending (uncomment to actually send test email)
        """
        test_ticket_data = {
            'Ticket ID': 'TEST-12345',
            'Brand': 'Conway',
            'Email': 'test@example.com',  # Replace with your test email
            'Empresa': 'Test Company S.L.',
            'Modelo': 'Cairon C 2.0 500'
        }
        
        # Test sending status update email
        success = sender.send_status_update_email(test_ticket_data, 'Tramitada')
        if success:
            print("✅ Test status update email sent successfully")
        else:
            print("❌ Test status update email failed")
        """
        
        print("Email sender test completed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")