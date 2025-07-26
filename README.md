# Warranty Treatment Automations

This repository contains various automations for warranty management and treatment processes. Each automation is organized in its own folder with source code, tests, and documentation.

## 📁 Repository Structure

```
warranty_treatment/
├── .env.example                      # Environment variables template
├── .env                             # Environment variables (not in git)
├── .gitignore                       # Git ignore rules
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── .github/
│   └── workflows/                   # GitHub Actions workflows
│       └── form-submission-automation.yml
└── form_submission/                 # Form submission automation
    ├── src/                         # Source code
    │   ├── main.py                  # Main orchestrator
    │   ├── send_confirmation_email.py
    │   ├── send_notification_email.py
    │   └── update_excel_dropbox.py
    └── tests/                       # Tests and test data
        ├── run_tests.py             # Test runner
        ├── test_duplicate_detection.py
        ├── TESTING_README.md        # Testing documentation
        └── test_*.json              # Test data files
```

## 🚀 Available Automations

### 1. Form Submission Automation (`form_submission/`)

Automates warranty form processing from Tally forms:
- **Duplicate detection** with 75% similarity threshold
- **Email confirmations** to clients in Spanish
- **Notification emails** to administrators
- **Excel file updates** in Dropbox with ticket tracking
- **Unique ticket ID generation** for each warranty case

**Key Features:**
- ✅ UUID-based ticket tracking
- ✅ Status management (Abierto, En trámite, Cliente notificado, Completado)
- ✅ Multi-brand support (Conway, Cycplus, Dare, Kogel)
- ✅ Smart duplicate detection algorithm
- ✅ Comprehensive test suite

## 🛠️ Setup

### 1. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd warranty_treatment

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials
```

### 2. Environment Variables
Configure the following in your `.env` file:

```bash
# Tally API
TALLY_API_KEY=your_tally_api_key

# Email Configuration (SMTP)
SMTP_HOST=smtp.strato.com
SMTP_PORT=465
SMTP_USERNAME=your_smtp_email
SMTP_PASSWORD=your_smtp_password

# Dropbox Configuration
DROPBOX_APP_KEY=your_dropbox_app_key
DROPBOX_APP_SECRET=your_dropbox_app_secret
DROPBOX_REFRESH_TOKEN=your_dropbox_refresh_token
DROPBOX_FOLDER_PATH=/path/to/your/dropbox/folder
DROPBOX_EMAIL_FOR_AUTOMATIONS=your_email@domain.com

# Holded API (if used)
HOLDED_API_KEY=your_holded_api_key
HOLDED_BASE_URL=https://api.holded.com/api/invoicing/v1
```

## 🧪 Testing

### Quick Testing
```bash
# Run all automation tests
cd form_submission/tests
python run_tests.py

# Run duplicate detection tests specifically
python test_duplicate_detection.py

# Test individual components
cd ../src
python main.py ../tests/test_webhook_data.json
```

### Test Options
1. **Full automation tests** with different brands
2. **Component testing** (emails, Excel updates)
3. **Duplicate detection algorithm** validation
4. **Interactive testing** mode

See `form_submission/tests/TESTING_README.md` for detailed testing instructions.

## 🔄 GitHub Actions

Each automation includes a GitHub workflow that triggers on repository dispatch events:

- **Form Submission**: `.github/workflows/form-submission-automation.yml`
  - Trigger: `FORM_RESPONSE` event type
  - Processes Tally webhook data automatically

### Setting up Webhooks
1. Configure Tally form webhook to point to GitHub repository dispatch
2. Set up repository secrets for all environment variables
3. Test with sample webhook data

## 📋 Adding New Automations

To add a new automation:

1. **Create folder structure**:
   ```
   new_automation/
   ├── src/
   │   └── main.py
   └── tests/
       ├── test_*.py
       └── test_*.json
   ```

2. **Create GitHub workflow**:
   ```yaml
   # .github/workflows/new-automation.yml
   name: New Automation
   on:
     repository_dispatch:
       types: [NEW_EVENT_TYPE]
   ```

3. **Update main README** with automation details

## 🔧 Dependencies

- **Python 3.9+**
- **pandas** - Excel file manipulation
- **requests** - HTTP requests and Dropbox API
- **python-dotenv** - Environment variable management
- **xlsxwriter** - Excel file writing
- **openpyxl** - Excel file reading

## 📚 Documentation

- **General Setup**: This README
- **Form Submission**: `form_submission/tests/TESTING_README.md`
- **Environment Variables**: `.env.example`

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running scripts from the correct directory
2. **Environment Variables**: Check `.env` file configuration
3. **Dropbox Access**: Verify API credentials and file paths
4. **Email Sending**: Confirm SMTP settings and credentials

### Debug Mode
Add debug prints to troubleshoot:
```python
print(f"Debug: Current working directory: {os.getcwd()}")
print(f"Debug: Environment loaded: {os.getenv('SMTP_HOST')}")
```

## 🤝 Contributing

1. Create a new branch for your automation
2. Follow the existing folder structure
3. Include comprehensive tests
4. Update documentation
5. Create pull request

## 📄 License

[Add your license information here]