#!/usr/bin/env python3
"""
Excel Reader for Status Update Notifications
Reads warranty tickets from Dropbox Excel file and extracts status information
"""

import os
import json
import requests
import pandas as pd
import sys
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Any
from dotenv import load_dotenv

# Import logging filter from root directory
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from log_filter import setup_secure_logging

load_dotenv()

# Set up secure logging
logger = setup_secure_logging('excel_reader')

class ExcelReader:
    """Handles reading warranty data from Dropbox Excel file"""
    
    def __init__(self):
        self.access_token = None
        self.file_path = None
        self._initialize_dropbox()
    
    def _initialize_dropbox(self):
        """Initialize Dropbox credentials and file path"""
        try:
            self.access_token = self._get_dropbox_access_token()
            folder_path = os.getenv('DROPBOX_FOLDER_PATH')
            self.file_path = f"{folder_path}/GARANTIAS_PROFFECTIV.xlsx"
            logger.info("Dropbox credentials initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Dropbox credentials: {str(e)}")
            raise
    
    def _get_dropbox_access_token(self):
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
    
    def _download_excel_from_dropbox(self):
        """Download Excel file from Dropbox"""
        url = 'https://content.dropboxapi.com/2/files/download'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Dropbox-API-Arg': json.dumps({'path': self.file_path})
        }
        
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            raise Exception(f"Failed to download file: {response.text}")
    
    def get_all_tickets_status(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Read all warranty tickets from Excel file and return current status
        
        Returns:
            Dictionary with brand names as keys and list of ticket data as values
        """
        try:
            logger.info("Starting to read Excel file from Dropbox")
            
            # Download Excel file
            excel_file = self._download_excel_from_dropbox()
            
            # Read all sheets
            excel_data = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
            
            all_tickets = {}
            brands = ['Conway', 'Cycplus', 'Dare', 'Kogel']
            
            for brand in brands:
                if brand not in excel_data:
                    logger.warning(f"Sheet '{brand}' not found in Excel file")
                    continue
                
                df = excel_data[brand]
                tickets = []
                
                # Process each row (skip header)
                for index, row in df.iterrows():
                    if index == 0:  # Skip header row
                        continue
                    
                    # Extract ticket data
                    ticket_data = {}
                    for col in df.columns:
                        ticket_data[col] = row[col] if pd.notna(row[col]) else ''
                    
                    # Add brand information
                    ticket_data['Brand'] = brand
                    
                    # Only include tickets with Ticket ID and Email
                    if ticket_data.get('Ticket ID') and ticket_data.get('Email'):
                        tickets.append(ticket_data)
                
                all_tickets[brand] = tickets
                logger.info(f"Read {len(tickets)} tickets from {brand} sheet")
            
            total_tickets = sum(len(tickets) for tickets in all_tickets.values())
            logger.info(f"Successfully read {total_tickets} total tickets from all sheets")
            
            return all_tickets
            
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
            return {}
    
    def get_tickets_by_status(self, target_statuses: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get tickets filtered by specific status values
        
        Args:
            target_statuses: List of status values to filter by (default: all notification statuses)
            
        Returns:
            Dictionary with brand names as keys and filtered ticket lists as values
        """
        if target_statuses is None:
            target_statuses = ['Tramitada', 'Aceptada', 'Denegada']
        
        all_tickets = self.get_all_tickets_status()
        filtered_tickets = {}
        
        for brand, tickets in all_tickets.items():
            filtered = []
            for ticket in tickets:
                status = ticket.get('Estado', '').strip()
                if status in target_statuses:
                    filtered.append(ticket)
            
            if filtered:
                filtered_tickets[brand] = filtered
        
        total_filtered = sum(len(tickets) for tickets in filtered_tickets.values())
        logger.info(f"Found {total_filtered} tickets with target statuses: {target_statuses}")
        
        return filtered_tickets
    
    def get_active_tickets(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get tickets that are not in final states (not 'Aceptada' or 'Denegada')
        These are the tickets we need to track for status changes
        
        Returns:
            Dictionary with brand names as keys and active ticket lists as values
        """
        all_tickets = self.get_all_tickets_status()
        active_tickets = {}
        
        final_statuses = ['Aceptada', 'Denegada']
        
        for brand, tickets in all_tickets.items():
            active = []
            for ticket in tickets:
                status = ticket.get('Estado', '').strip()
                if status not in final_statuses:
                    active.append(ticket)
            
            if active:
                active_tickets[brand] = active
        
        total_active = sum(len(tickets) for tickets in active_tickets.values())
        logger.info(f"Found {total_active} active tickets (not in final states)")
        
        return active_tickets

if __name__ == "__main__":
    # Test the Excel reader
    try:
        reader = ExcelReader()
        
        print("Testing Excel Reader...")
        print("=" * 50)
        
        # Test reading all tickets
        all_tickets = reader.get_all_tickets_status()
        total = sum(len(tickets) for tickets in all_tickets.values())
        print(f"Total tickets found: {total}")
        
        for brand, tickets in all_tickets.items():
            print(f"{brand}: {len(tickets)} tickets")
        
        print("\n" + "=" * 50)
        
        # Test reading tickets by status
        status_tickets = reader.get_tickets_by_status(['Tramitada', 'Aceptada', 'Denegada'])
        total_status = sum(len(tickets) for tickets in status_tickets.values())
        print(f"Tickets with notification statuses: {total_status}")
        
        for brand, tickets in status_tickets.items():
            print(f"{brand}: {len(tickets)} tickets with notification statuses")
        
        print("\n" + "=" * 50)
        
        # Test reading active tickets
        active_tickets = reader.get_active_tickets()
        total_active = sum(len(tickets) for tickets in active_tickets.values())
        print(f"Active tickets (not in final state): {total_active}")
        
        for brand, tickets in active_tickets.items():
            print(f"{brand}: {len(tickets)} active tickets")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")