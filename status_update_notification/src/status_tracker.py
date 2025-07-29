#!/usr/bin/env python3
"""
Status Tracker for Warranty Notifications
Manages status history and detects changes that require notifications
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Import logging filter from root directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

# Set up secure logging
logger = setup_secure_logging('status_tracker')

class StatusTracker:
    """Manages warranty ticket status tracking and change detection"""
    
    def __init__(self, history_file_path: str = None):
        """
        Initialize status tracker
        
        Args:
            history_file_path: Path to status history JSON file
        """
        if history_file_path is None:
            # Default to status_update_notification directory
            base_dir = os.path.dirname(os.path.dirname(__file__))
            history_file_path = os.path.join(base_dir, 'status_history.json')
        
        self.history_file_path = history_file_path
        self.status_history = self._load_status_history()
        self.notification_statuses = ['Tramitada', 'Aceptada', 'Denegada']
        self.final_statuses = ['Aceptada', 'Denegada']
        logger.info(f"Status tracker initialized with history file: {history_file_path}")
    
    def _load_status_history(self) -> Dict[str, Any]:
        """Load status history from JSON file"""
        try:
            if os.path.exists(self.history_file_path):
                with open(self.history_file_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                logger.info(f"Loaded status history with {len(history.get('tickets', {}))} tickets")
                return history
            else:
                logger.info("No existing status history found, creating new one")
                return {
                    'last_updated': None,
                    'tickets': {}
                }
        except Exception as e:
            logger.error(f"Error loading status history: {str(e)}")
            return {
                'last_updated': None,
                'tickets': {}
            }
    
    def _save_status_history(self):
        """Save status history to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.history_file_path), exist_ok=True)
            
            # Update last_updated timestamp
            self.status_history['last_updated'] = datetime.now().isoformat()
            
            with open(self.history_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.status_history, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Status history saved with {len(self.status_history['tickets'])} tickets")
            
        except Exception as e:
            logger.error(f"Error saving status history: {str(e)}")
    
    def _get_ticket_key(self, ticket_data: Dict[str, Any]) -> str:
        """Generate unique key for ticket"""
        ticket_id = ticket_data.get('Ticket ID', '')
        brand = ticket_data.get('Brand', '')
        return f"{brand}_{ticket_id}"
    
    def detect_status_changes(self, current_tickets: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Detect status changes that require notifications
        
        Args:
            current_tickets: Current ticket data from Excel (brand -> list of tickets)
            
        Returns:
            List of tickets with status changes requiring notification
        """
        changes_to_notify = []
        
        try:
            # Process all current tickets
            for brand, tickets in current_tickets.items():
                for ticket in tickets:
                    ticket_key = self._get_ticket_key(ticket)
                    current_status = ticket.get('Estado', '').strip()
                    
                    # Skip if no ticket ID or email
                    if not ticket.get('Ticket ID') or not ticket.get('Email'):
                        continue
                    
                    # Get previous status
                    previous_data = self.status_history['tickets'].get(ticket_key, {})
                    previous_status = previous_data.get('status', '')
                    
                    # Check if status changed and requires notification
                    if self._should_notify(previous_status, current_status):
                        change_info = {
                            'ticket_data': ticket,
                            'previous_status': previous_status,
                            'current_status': current_status,
                            'change_timestamp': datetime.now().isoformat(),
                            'ticket_key': ticket_key
                        }
                        changes_to_notify.append(change_info)
                        logger.info(f"Status change detected for {ticket_key}: {previous_status} -> {current_status}")
            
            logger.info(f"Detected {len(changes_to_notify)} status changes requiring notification")
            return changes_to_notify
            
        except Exception as e:
            logger.error(f"Error detecting status changes: {str(e)}")
            return []
    
    def _should_notify(self, previous_status: str, current_status: str) -> bool:
        """
        Determine if a status change requires notification
        
        Args:
            previous_status: Previous status value
            current_status: Current status value
            
        Returns:
            True if notification should be sent
        """
        # No notification needed if status hasn't changed
        if previous_status == current_status:
            return False
        
        # No notification if current status is not a notification status
        if current_status not in self.notification_statuses:
            return False
        
        # For new tickets (no previous status), notify if in notification status
        if not previous_status:
            return True
        
        # For existing tickets, notify only if status actually changed to notification status
        return previous_status != current_status
    
    def update_status_history(self, current_tickets: Dict[str, List[Dict[str, Any]]]):
        """
        Update status history with current ticket states
        
        Args:
            current_tickets: Current ticket data from Excel
        """
        try:
            updated_count = 0
            cleaned_count = 0
            
            # Update with current tickets
            for brand, tickets in current_tickets.items():
                for ticket in tickets:
                    ticket_key = self._get_ticket_key(ticket)
                    current_status = ticket.get('Estado', '').strip()
                    
                    # Skip if no ticket ID
                    if not ticket.get('Ticket ID'):
                        continue
                    
                    # Update ticket info
                    self.status_history['tickets'][ticket_key] = {
                        'status': current_status,
                        'last_updated': datetime.now().isoformat(),
                        'ticket_id': ticket.get('Ticket ID'),
                        'brand': ticket.get('Brand'),
                        'email': ticket.get('Email'),
                        'empresa': ticket.get('Empresa', '')
                    }
                    updated_count += 1
            
            # Clean up tickets in final states (no longer need tracking)
            tickets_to_remove = []
            for ticket_key, ticket_info in self.status_history['tickets'].items():
                if ticket_info.get('status') in self.final_statuses:
                    tickets_to_remove.append(ticket_key)
            
            for ticket_key in tickets_to_remove:
                del self.status_history['tickets'][ticket_key]
                cleaned_count += 1
            
            # Save updated history
            self._save_status_history()
            
            logger.info(f"Updated status history: {updated_count} tickets updated, {cleaned_count} final tickets cleaned")
            
        except Exception as e:
            logger.error(f"Error updating status history: {str(e)}")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of current status tracking
        
        Returns:
            Dictionary with status summary information
        """
        try:
            tickets = self.status_history['tickets']
            
            # Count by status
            status_counts = {}
            for ticket_info in tickets.values():
                status = ticket_info.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by brand
            brand_counts = {}
            for ticket_info in tickets.values():
                brand = ticket_info.get('brand', 'Unknown')
                brand_counts[brand] = brand_counts.get(brand, 0) + 1
            
            summary = {
                'total_tracked_tickets': len(tickets),
                'last_updated': self.status_history.get('last_updated'),
                'status_breakdown': status_counts,
                'brand_breakdown': brand_counts,
                'notification_statuses': self.notification_statuses,
                'final_statuses': self.final_statuses
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting status summary: {str(e)}")
            return {}
    
    def cleanup_old_entries(self, days_old: int = 30):
        """
        Clean up old entries from status history
        
        Args:
            days_old: Remove entries older than this many days
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            tickets_to_remove = []
            
            for ticket_key, ticket_info in self.status_history['tickets'].items():
                last_updated_str = ticket_info.get('last_updated')
                if last_updated_str:
                    try:
                        last_updated = datetime.fromisoformat(last_updated_str)
                        if last_updated < cutoff_date:
                            tickets_to_remove.append(ticket_key)
                    except ValueError:
                        # Invalid date format, remove entry
                        tickets_to_remove.append(ticket_key)
            
            # Remove old entries
            for ticket_key in tickets_to_remove:
                del self.status_history['tickets'][ticket_key]
            
            if tickets_to_remove:
                self._save_status_history()
                logger.info(f"Cleaned up {len(tickets_to_remove)} old entries from status history")
            
        except Exception as e:
            logger.error(f"Error cleaning up old entries: {str(e)}")

if __name__ == "__main__":
    # Test the status tracker
    try:
        tracker = StatusTracker()
        
        print("Testing Status Tracker...")
        print("=" * 50)
        
        # Test status summary
        summary = tracker.get_status_summary()
        print(f"Current status summary:")
        print(f"- Total tracked tickets: {summary.get('total_tracked_tickets', 0)}")
        print(f"- Last updated: {summary.get('last_updated', 'Never')}")
        print(f"- Status breakdown: {summary.get('status_breakdown', {})}")
        print(f"- Brand breakdown: {summary.get('brand_breakdown', {})}")
        
        print("\n" + "=" * 50)
        
        # Test mock status change detection
        mock_current_tickets = {
            'Conway': [
                {
                    'Ticket ID': 'TEST-001',
                    'Brand': 'Conway',
                    'Email': 'test@example.com',
                    'Estado': 'Tramitada',
                    'Empresa': 'Test Company'
                }
            ]
        }
        
        changes = tracker.detect_status_changes(mock_current_tickets)
        print(f"Mock status changes detected: {len(changes)}")
        
        for change in changes:
            print(f"- {change['ticket_key']}: {change['previous_status']} -> {change['current_status']}")
        
        # Update history with mock data
        tracker.update_status_history(mock_current_tickets)
        print("✅ Status history updated with mock data")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")