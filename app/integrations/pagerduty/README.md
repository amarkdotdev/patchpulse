# PagerDuty Integration

Send PatchPulse risk notifications to PagerDuty for incident management.

## Setup

1. **Create a PagerDuty Integration:**
   - Log in to PagerDuty
   - Go to Services → Your Service → Integrations
   - Add "Events API v2" integration
   - Copy the Integration Key

2. **Configure Environment Variable:**
   ```bash
   export PAGERDUTY_INTEGRATION_KEY="your-integration-key"
   ```

## Usage

```python
from integrations.pagerduty.notifier import PagerDutyNotifier

notifier = PagerDutyNotifier()
notifier.send_decision_notification(decision_data)

# Resolve an incident
notifier.resolve_incident(decision_id, "Issue resolved")
```

## Features

- Automatic incident creation for high-risk decisions
- Severity mapping based on risk score
- Custom details with full decision context
- Deduplication using decision IDs
- Incident resolution support

## Severity Mapping

- **Critical**: Risk score ≥ 80 or blocked decisions
- **Error**: Risk score 60-79
- **Warning**: Risk score 40-59
- **Info**: Risk score < 40

## Event Actions

- **Trigger**: Creates new incident (for blocked or high-risk decisions)
- **Acknowledge**: Acknowledges without creating incident (for low-risk)

## Custom Details

PagerDuty incidents include:
- Risk score
- Repository and PR/MR information
- Top issues detected
- Guardrails triggered count
- Link to dashboard

## Incident Management

Incidents are automatically deduplicated using decision IDs. You can resolve incidents programmatically:

```python
notifier.resolve_incident(decision_id, "Change approved after review")
```



