# 🎉 New Integrations Added: Teams, Email, and PagerDuty

## Overview

Added **3 major integrations** to PatchPulse for comprehensive notification and incident management:

1. **Microsoft Teams** - Rich webhook notifications
2. **Email Alerts** - SMTP-based email notifications
3. **PagerDuty** - Incident management integration

---

## 📋 Microsoft Teams Integration

### Features
- ✅ Adaptive Cards with rich formatting
- ✅ Color-coded risk scores
- ✅ Interactive buttons to view details
- ✅ Guardrails and recommendations display
- ✅ Automatic formatting based on risk level

### Setup
```bash
# Create Teams webhook and set environment variable
export TEAMS_WEBHOOK_URL="https://outlook.office.com/webhook/..."
```

### Usage
Notifications are automatically sent when decisions are made. The integration uses Teams Adaptive Cards for rich formatting.

---

## 📧 Email Integration

### Features
- ✅ HTML and plain text email formats
- ✅ Rich HTML styling with color-coded risk indicators
- ✅ Multiple recipients support
- ✅ Automatic risk score formatting
- ✅ Links to dashboard for details

### Setup
```bash
# Gmail example
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export EMAIL_FROM="patchpulse@yourdomain.com"
export EMAIL_TO="team@yourdomain.com,admin@yourdomain.com"
```

### Supported Providers
- Gmail
- SendGrid
- AWS SES
- Any SMTP server

### Email Content
- Risk score with visual indicators
- Repository and PR/MR information
- Top issues detected
- Guardrails triggered
- Recommended actions
- Direct link to decision details

---

## 🚨 PagerDuty Integration

### Features
- ✅ Automatic incident creation for high-risk decisions
- ✅ Severity mapping based on risk score
- ✅ Custom details with full decision context
- ✅ Deduplication using decision IDs
- ✅ Incident resolution support

### Setup
```bash
# Create PagerDuty Events API v2 integration and set key
export PAGERDUTY_INTEGRATION_KEY="your-integration-key"
```

### Severity Mapping
- **Critical**: Risk score ≥ 80 or blocked decisions
- **Error**: Risk score 60-79
- **Warning**: Risk score 40-59
- **Info**: Risk score < 40

### Event Actions
- **Trigger**: Creates new incident (for blocked or high-risk decisions)
- **Acknowledge**: Acknowledges without creating incident (for low-risk)

### Incident Management
Incidents are automatically deduplicated using decision IDs. You can resolve incidents programmatically.

---

## 🔧 Integration Management

### API Endpoints

#### List Integrations
```bash
GET /api/v1/integrations
```

Returns status of all integrations:
```json
{
  "teams": {
    "enabled": true,
    "configured": true
  },
  "email": {
    "enabled": true,
    "configured": true
  },
  "pagerduty": {
    "enabled": true,
    "configured": true
  }
}
```

#### Test Integration
```bash
POST /api/v1/integrations/{integration_type}/test
```

Test a specific integration:
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/teams/test"
curl -X POST "http://localhost:8000/api/v1/integrations/email/test"
curl -X POST "http://localhost:8000/api/v1/integrations/pagerduty/test"
```

---

## 🚀 Automatic Integration

All integrations are **automatically triggered** when decisions are made:

1. Decision is created
2. Webhooks are triggered
3. **Teams notification sent** (if configured)
4. **Email alert sent** (if configured)
5. **PagerDuty incident created** (if configured and high-risk)

No additional configuration needed - just set the environment variables!

---

## 📁 Files Created

### Integration Modules
- `app/integrations/teams/notifier.py` - Teams webhook integration
- `app/integrations/email/notifier.py` - SMTP email integration
- `app/integrations/pagerduty/notifier.py` - PagerDuty Events API integration

### Documentation
- `app/integrations/teams/README.md` - Teams setup guide
- `app/integrations/email/README.md` - Email setup guide
- `app/integrations/pagerduty/README.md` - PagerDuty setup guide

### Management
- `app/backend/integration_manager.py` - Integration configuration management

---

## ✅ Integration Status

All integrations are:
- ✅ **Implemented** and tested
- ✅ **Production-ready**
- ✅ **Documented** with setup guides
- ✅ **Automatically integrated** with decision system
- ✅ **Committed** to repository

---

## 🎯 Usage Examples

### Teams Notification
When a decision is made, Teams receives a rich Adaptive Card with:
- Risk score visualization
- Top issues
- Guardrails triggered
- Action buttons

### Email Alert
When a decision is made, configured email addresses receive:
- HTML formatted email
- Plain text fallback
- Risk score with color coding
- Full decision details
- Link to dashboard

### PagerDuty Incident
When a high-risk decision is made:
- Incident automatically created in PagerDuty
- Severity set based on risk score
- Custom details include full context
- Can be resolved programmatically

---

## 🔒 Security Notes

- **Teams**: Webhook URLs should be kept secret
- **Email**: Use App Passwords for Gmail, not regular passwords
- **PagerDuty**: Integration keys should be stored securely
- All credentials should be in environment variables or secrets manager

---

*Integrations added on December 28, 2025*

