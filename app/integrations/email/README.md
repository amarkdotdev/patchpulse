# Email Integration

Send PatchPulse risk notifications via email (SMTP).

## Setup

### Gmail Example

```bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"  # Use App Password, not regular password
export EMAIL_FROM="patchpulse@yourdomain.com"
export EMAIL_TO="team@yourdomain.com,admin@yourdomain.com"
```

### Other SMTP Providers

```bash
# SendGrid
export SMTP_HOST="smtp.sendgrid.net"
export SMTP_PORT="587"
export SMTP_USER="apikey"
export SMTP_PASSWORD="your-sendgrid-api-key"

# AWS SES
export SMTP_HOST="email-smtp.us-east-1.amazonaws.com"
export SMTP_PORT="587"
export SMTP_USER="your-access-key"
export SMTP_PASSWORD="your-secret-key"

# Custom SMTP
export SMTP_HOST="smtp.yourdomain.com"
export SMTP_PORT="587"
export SMTP_USER="your-username"
export SMTP_PASSWORD="your-password"
export EMAIL_FROM="patchpulse@yourdomain.com"
export EMAIL_TO="team@yourdomain.com"
```

## Usage

```python
from integrations.email.notifier import EmailNotifier

notifier = EmailNotifier()
notifier.send_decision_notification(decision_data)
```

## Features

- HTML and plain text email formats
- Rich HTML formatting with styling
- Multiple recipients support
- Automatic risk score formatting
- Links to dashboard for details

## Email Content

Emails include:
- Risk score with visual indicators
- Repository and PR/MR information
- Top issues detected
- Guardrails triggered
- Recommended actions
- Direct link to decision details

## Security Notes

- Use App Passwords for Gmail (not regular passwords)
- Consider using OAuth2 for production
- Store credentials securely (environment variables, secrets manager)
- Use TLS/SSL for SMTP connections



