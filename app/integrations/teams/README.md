# Microsoft Teams Integration

Send PatchPulse risk notifications to Microsoft Teams channels using Adaptive Cards.

## Setup

1. **Create a Teams Webhook:**
   - Go to your Teams channel
   - Click the three dots (...) next to the channel name
   - Select "Connectors"
   - Search for "Incoming Webhook"
   - Click "Configure" and create a webhook
   - Copy the webhook URL

2. **Configure Environment Variable:**
   ```bash
   export TEAMS_WEBHOOK_URL="https://outlook.office.com/webhook/..."
   ```

## Usage

```python
from integrations.teams.notifier import TeamsNotifier

notifier = TeamsNotifier()
notifier.send_decision_notification(decision_data)
```

## Features

- Rich Adaptive Cards with formatted risk information
- Color-coded risk scores
- Interactive buttons to view details
- Guardrails and recommendations display
- Automatic formatting based on risk level

## Message Format

Teams notifications include:
- Risk score with color coding
- Top issues detected
- Guardrails triggered
- Recommended actions
- Link to dashboard for details

