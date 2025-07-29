# Status Update Notification Automation

Daily automation system that monitors warranty ticket status changes in Dropbox Excel files and sends Spanish email notifications to clients when status changes to "Tramitada", "Aceptada", or "Denegada".

## 🎯 Overview

This automation integrates seamlessly with your existing warranty management system, providing automatic client notifications when warranty statuses are updated. The system runs daily via GitHub Actions and tracks status changes to prevent duplicate notifications.

## 🏗️ Architecture

### Core Components

- **`main.py`** - Main orchestrator script that coordinates the entire process
- **`excel_reader.py`** - Reads Excel file from Dropbox and extracts current status data
- **`status_tracker.py`** - Manages status tracking using JSON file to store previous states  
- **`email_sender.py`** - Sends status update emails using existing SMTP configuration
- **`email_templates.py`** - Spanish email templates for each status type

### Status Tracking System

- **JSON-based history** (`status_history.json`) tracks previous status states
- **Smart duplicate prevention** by comparing current vs previous status
- **Automatic cleanup** of tickets that reach final states ("Aceptada"/"Denegada")
- **Multi-brand support** for Conway, Cycplus, Dare, and Kogel

## 📧 Email Templates

### Supported Status Types

1. **"Tramitada"** - Warranty is being processed
   - Subject: "📋 Actualización de Garantía - En Tramitación"
   - Informs client their warranty is under review

2. **"Aceptada"** - Warranty approved  
   - Subject: "✅ Garantía Aceptada - Siguiente Paso"
   - Notifies client of approval and next steps

3. **"Denegada"** - Warranty rejected
   - Subject: "❌ Resolución de Garantía - Información Importante"
   - Explains rejection and provides options

### Template Features

- **Spanish language** emails with professional formatting
- **Ticket ID prominence** for easy reference
- **Brand-specific information** included
- **HTML formatting** with color-coded status indicators
- **Company branding** consistent with existing emails

## ⏰ Automation Schedule

### GitHub Actions Workflow

The system runs automatically via GitHub Actions:

- **Daily execution** at 9:00 AM UTC (10:00 AM CET / 11:00 AM CEST)
- **Manual triggering** available for testing via `workflow_dispatch`
- **Repository dispatch** support for external triggers

### Workflow Features

- **Environment variable setup** using GitHub Secrets
- **Fault tolerance** with `continue-on-error: true`
- **Comprehensive logging** of execution details
- **Admin summary emails** with results

## 🔧 Configuration

### Required Environment Variables

```bash
# Email Configuration (reuses existing SMTP settings)
SMTP_HOST=smtp.strato.com
SMTP_PORT=465
SMTP_USERNAME=miguel@proffectiv.com
SMTP_PASSWORD=your-password
NOTIFICATION_EMAIL=admin@domain.com

# Dropbox Configuration (reuses existing credentials)
DROPBOX_APP_KEY=your-app-key
DROPBOX_APP_SECRET=your-app-secret
DROPBOX_REFRESH_TOKEN=your-refresh-token
DROPBOX_FOLDER_PATH=/GARANTIAS
```

### Excel File Requirements

- **File location**: `/GARANTIAS/GARANTIAS_PROFFECTIV.xlsx` in Dropbox
- **Required sheets**: Conway, Cycplus, Dare, Kogel
- **Required columns**: "Ticket ID", "Estado", "Email", "Empresa"
- **Status values**: Must match exactly ("Recibida", "Tramitada", "Aceptada", "Denegada")
- **Initial status**: New warranty entries start with "Recibida" status

## 🚀 Usage

### Automatic Execution

The system runs automatically every day at 9:00 AM UTC via GitHub Actions. No manual intervention required.

### Manual Execution

```bash
# Run full automation
cd status_update_notification/src
python main.py

# Get status summary
python main.py summary

# Test components
python main.py test
```

### Triggering via GitHub Actions

```bash
# Manual trigger
gh workflow run "Status Update Notification"

# Repository dispatch trigger
gh api repos/owner/repo/dispatches \
  --field event_type=status-update-notification
```

## 🧪 Testing

### Test Suite

Comprehensive testing is available in the `tests/` directory:

```bash
# Run all tests
cd status_update_notification/tests
python run_tests.py all

# Interactive test menu
python run_tests.py interactive

# Test specific components
python run_tests.py templates  # Email templates only
python run_tests.py tracker    # Status tracker only
```

### Test Coverage

- **Email template generation** and content validation
- **Status change detection** and duplicate prevention
- **History management** and cleanup
- **Component integration** testing
- **Environment validation**
- **SMTP connectivity** testing

## 📊 Monitoring

### Admin Notifications

The system sends daily summary emails to the admin with:

- **Total notifications processed**
- **Success/failure counts**
- **Failed ticket details** (if any)
- **Execution timestamp**

### Logging

- **Secure logging** with sensitive data filtering
- **Comprehensive execution logs** in GitHub Actions
- **Component-level logging** for debugging
- **Error tracking** and reporting

## 🔄 Workflow Integration

### Execution Flow

1. **Download Excel file** from Dropbox
2. **Extract current status** for all tickets across all brand sheets
3. **Compare with stored history** to identify changes
4. **Send appropriate emails** for status changes requiring notification
5. **Update status history** with new states
6. **Clean up resolved tickets** from tracking
7. **Send admin summary** with results

### Error Handling

- **Graceful failure handling** with detailed error logging
- **Retry logic** for transient network issues
- **Validation checks** for data integrity
- **Rollback protection** for status history

## 🛡️ Security

- **Environment variable protection** via GitHub Secrets
- **Secure logging** with credential filtering
- **No plaintext secrets** in code or logs
- **Access token refresh** for Dropbox authentication

## 📈 Performance

- **Efficient Excel reading** with pandas
- **Batch email processing** for multiple notifications
- **Smart status tracking** to minimize processing
- **Cleanup routines** to prevent data growth

## 🔧 Maintenance

### Regular Tasks

- **Monitor admin summary emails** for failures
- **Review GitHub Actions logs** for errors
- **Update email templates** as needed
- **Verify Excel file structure** consistency

### Troubleshooting

- **Check environment variables** if components fail to initialize
- **Verify Dropbox credentials** if Excel reading fails
- **Test SMTP connection** if emails aren't sending
- **Review status history** for tracking issues

## 📝 Development

### Adding New Status Types

1. Add status to `email_templates.py` `get_supported_statuses()`
2. Create email template in `create_status_update_email()`
3. Update tests in `tests/test_email_templates.py`
4. Test with `python run_tests.py templates`

### Modifying Email Templates

1. Edit templates in `email_templates.py`
2. Test changes with `python run_tests.py templates`
3. Generate samples with option 7 in interactive menu
4. Review HTML output in browser

## 🚨 Important Notes

- **Status values must match exactly** - case sensitive
- **Tickets with final statuses** (Aceptada/Denegada) are automatically cleaned up
- **Only tickets with Ticket ID and Email** are processed
- **Duplicate notifications are prevented** via status history tracking
- **System integrates seamlessly** with existing warranty workflow

## 🆘 Support

For issues or questions:

1. **Check GitHub Actions logs** for execution details
2. **Run test suite** to identify component issues
3. **Review admin summary emails** for failure patterns
4. **Examine status history file** for tracking issues
5. **Verify environment variables** and credentials