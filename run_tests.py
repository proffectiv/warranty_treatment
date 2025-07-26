#!/usr/bin/env python3
"""
Test runner for warranty automation system
This script allows you to test the automation with different brand scenarios
"""

import os
import sys
import json
from datetime import datetime

def display_menu():
    """Display test options menu"""
    print("\n" + "="*60)
    print("🧪 WARRANTY AUTOMATION TEST RUNNER")
    print("="*60)
    print("Select a test scenario:")
    print()
    print("1. 🔧 Cycplus - Mini Compresor AS2 PRO (Complete test data)")
    print("2. 🚴 Conway - Cairon C 2.0 500 (Complete test data)")
    print("3. 🏔️  Dare - GA S8 (Complete test data)")
    print("4. 📄 Custom JSON file")
    print("5. 🔍 Test individual components")
    print("6. ❌ Exit")
    print()

def display_component_menu():
    """Display component test menu"""
    print("\n" + "="*50)
    print("🔧 COMPONENT TESTING")
    print("="*50)
    print("1. 📧 Test confirmation email only")
    print("2. 🔔 Test notification email only")
    print("3. 📊 Test Excel update only")
    print("4. 🔙 Back to main menu")
    print()

def run_component_test(component, test_file):
    """Run individual component test"""
    print(f"\n🚀 Running {component} test with {test_file}...")
    
    if component == "confirmation":
        os.system(f"python send_confirmation_email.py {test_file}")
    elif component == "notification":
        os.system(f"python send_notification_email.py {test_file}")
    elif component == "excel":
        os.system(f"python update_excel_dropbox.py {test_file}")

def run_full_test(test_file):
    """Run full automation test"""
    print(f"\n🚀 Running full warranty automation test with {test_file}...")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if test file exists
    if not os.path.exists(test_file):
        print(f"❌ Error: Test file '{test_file}' not found!")
        return False
    
    # Display test data summary
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📋 Test Data Summary:")
        print(f"   Event ID: {data.get('eventId', 'N/A')}")
        print(f"   Response ID: {data.get('data', {}).get('responseId', 'N/A')}")
        
        # Extract brand info
        fields = data.get('data', {}).get('fields', [])
        brand = "Unknown"
        empresa = "Unknown"
        
        for field in fields:
            if field['key'] == 'question_YG10j0' and field.get('value'):
                for option in field.get('options', []):
                    if option['id'] in field['value']:
                        brand = option['text']
                        break
            elif field['key'] == 'question_59JjXb':
                empresa = field.get('value', 'Unknown')
        
        print(f"   Company: {empresa}")
        print(f"   Brand: {brand}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not parse test data: {str(e)}")
    
    # Run the main script
    result = os.system(f"python main.py {test_file}")
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if result == 0:
        print("✅ Test completed successfully!")
        return True
    else:
        print("❌ Test completed with errors!")
        return False

def main():
    """Main test runner"""
    
    # Check if required files exist
    required_files = [
        'main.py',
        'send_confirmation_email.py',
        'send_notification_email.py',
        'update_excel_dropbox.py'
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"❌ Error: Missing required files: {', '.join(missing_files)}")
        return
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  Warning: .env file not found. Make sure to configure your environment variables.")
        print("   You can copy .env.example to .env and fill in your credentials.")
    
    while True:
        display_menu()
        
        try:
            choice = input("👉 Enter your choice (1-6): ").strip()
            
            if choice == '1':
                run_full_test('test_webhook_data.json')
            elif choice == '2':
                run_full_test('test_conway_data.json')
            elif choice == '3':
                run_full_test('test_dare_data.json')
            elif choice == '4':
                custom_file = input("📁 Enter path to custom JSON file: ").strip()
                if custom_file:
                    run_full_test(custom_file)
                else:
                    print("❌ No file specified!")
            elif choice == '5':
                while True:
                    display_component_menu()
                    comp_choice = input("👉 Enter your choice (1-4): ").strip()
                    
                    if comp_choice == '1':
                        test_file = input("📁 Enter test file (or press Enter for Cycplus): ").strip()
                        if not test_file:
                            test_file = 'test_webhook_data.json'
                        run_component_test('confirmation', test_file)
                    elif comp_choice == '2':
                        test_file = input("📁 Enter test file (or press Enter for Cycplus): ").strip()
                        if not test_file:
                            test_file = 'test_webhook_data.json'
                        run_component_test('notification', test_file)
                    elif comp_choice == '3':
                        test_file = input("📁 Enter test file (or press Enter for Cycplus): ").strip()
                        if not test_file:
                            test_file = 'test_webhook_data.json'
                        run_component_test('excel', test_file)
                    elif comp_choice == '4':
                        break
                    else:
                        print("❌ Invalid choice! Please select 1-4.")
            elif choice == '6':
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice! Please select 1-6.")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()