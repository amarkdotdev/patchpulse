# Slack Integration

Slack notifications and interactive approvals for PatchPulse decisions.

## Setup

1. Create a Slack app at https://api.slack.com/apps
2. Add bot token scopes: `chat:write`, `channels:read`
3. Install app to workspace
4. Add bot to your channel
5. Set up interactive components (buttons) and webhook URL

## How to Run

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_CHANNEL="#patchpulse"
export BACKEND_URL="http://localhost:8000"

# For webhook server
python webhook.py
```

## Environment Variables

- `SLACK_BOT_TOKEN`: Slack bot token (required)
- `SLACK_CHANNEL`: Channel to post notifications (default: `#patchpulse`)
- `BACKEND_URL`: Backend API URL for detail links

## Usage

```python
from notifier import notify_on_decision

decision = {
    "change_event_id": "...",
    "decision_id": "...",
    "risk_score": 75,
    "reasons": [...],
    "mode": "advisory",
    "allowed": True
}

notify_on_decision(decision)
```

## Message Format

Slack messages include:
- Risk score with color coding
- Top 5 issues
- Guardrails triggered
- Recommended action
- Interactive buttons (View Details, Approve, Deny)

