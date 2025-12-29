"""Integration management for Teams, Email, and PagerDuty."""

import os
import logging
from typing import Dict, Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON
from models import Base
from datetime import datetime

logger = logging.getLogger(__name__)


class IntegrationConfigDB(Base):
    """Integration configuration in database."""
    __tablename__ = "integration_configs"
    
    id = Column(String, primary_key=True)
    integration_type = Column(String, nullable=False)  # teams, email, pagerduty
    enabled = Column(Boolean, default=True)
    config = Column(JSON)  # Integration-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


def get_integration_config(integration_type: str) -> Optional[Dict]:
    """Get integration configuration from environment or database."""
    configs = {
        "teams": {
            "webhook_url": os.getenv("TEAMS_WEBHOOK_URL"),
            "enabled": bool(os.getenv("TEAMS_WEBHOOK_URL"))
        },
        "email": {
            "smtp_host": os.getenv("SMTP_HOST"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "smtp_user": os.getenv("SMTP_USER"),
            "smtp_password": os.getenv("SMTP_PASSWORD"),
            "from_email": os.getenv("EMAIL_FROM"),
            "to_emails": os.getenv("EMAIL_TO", "").split(","),
            "enabled": bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))
        },
        "pagerduty": {
            "integration_key": os.getenv("PAGERDUTY_INTEGRATION_KEY"),
            "enabled": bool(os.getenv("PAGERDUTY_INTEGRATION_KEY"))
        }
    }
    
    return configs.get(integration_type)


def test_integration(integration_type: str) -> Dict:
    """Test an integration configuration."""
    test_decision = {
        "decision_id": "test-123",
        "change_event_id": "test-456",
        "risk_score": 75,
        "allowed": True,
        "reasons": ["Test notification"],
        "guardrails_triggered": [],
        "mode": "advisory",
        "repo": "test/repo",
        "pr_number": 999
    }
    
    try:
        if integration_type == "teams":
            from integrations.teams.notifier import TeamsNotifier
            notifier = TeamsNotifier()
            result = notifier.send_decision_notification(test_decision)
        elif integration_type == "email":
            from integrations.email.notifier import EmailNotifier
            notifier = EmailNotifier()
            result = notifier.send_decision_notification(test_decision)
        elif integration_type == "pagerduty":
            from integrations.pagerduty.notifier import PagerDutyNotifier
            notifier = PagerDutyNotifier()
            result = notifier.send_decision_notification(test_decision)
        else:
            return {"success": False, "error": "Unknown integration type"}
        
        return {"success": result, "message": "Test notification sent successfully" if result else "Test notification failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

