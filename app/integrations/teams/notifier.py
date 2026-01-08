"""Microsoft Teams integration for risk notifications."""

import os
import json
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class TeamsNotifier:
    """Send risk notifications to Microsoft Teams."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("TEAMS_WEBHOOK_URL")
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    def format_risk_score(self, score: int) -> str:
        """Format risk score with emoji."""
        if score >= 80:
            return f"🔴 {score}/100 (Critical)"
        elif score >= 60:
            return f"🟠 {score}/100 (High)"
        elif score >= 30:
            return f"🟡 {score}/100 (Medium)"
        else:
            return f"🟢 {score}/100 (Low)"
    
    def format_decision_message(self, decision: Dict) -> Dict:
        """Format decision as Teams Adaptive Card."""
        risk_score = decision.get("risk_score", 0)
        reasons = decision.get("reasons", [])[:5]  # Top 5
        guardrails = decision.get("guardrails_triggered", [])
        mode = decision.get("mode", "advisory")
        allowed = decision.get("allowed", True)
        change_event_id = decision.get("change_event_id")
        decision_id = decision.get("decision_id")
        
        # Determine status and color
        if not allowed:
            status = "❌ BLOCKED"
            color = "attention"
        elif risk_score >= 70:
            status = "⚠️ HIGH RISK"
            color = "warning"
        else:
            status = "✅ ALLOWED"
            color = "good"
        
        # Build reasons text
        reasons_text = "\n".join([f"• {r}" for r in reasons]) if reasons else "No specific issues detected"
        
        # Build guardrails text
        guardrails_text = ""
        if guardrails:
            guardrails_list = []
            for gr in guardrails[:5]:
                severity_emoji = "🔴" if gr.get("severity", 0) >= 50 else "🟠" if gr.get("severity", 0) >= 30 else "🟡"
                guardrails_list.append(f"{severity_emoji} {gr.get('message', 'Unknown')}")
            guardrails_text = "\n".join(guardrails_list)
        
        # Recommended action
        if not allowed:
            action = "🚫 Change should not be merged. Review guardrails and fix issues."
        elif risk_score >= 70:
            action = "⚠️ Consider canary deployment or rollback plan before merging."
        elif risk_score >= 40:
            action = "💡 Review changes carefully. Consider adding resource limits or monitoring."
        else:
            action = "✅ Change looks safe. Proceed with normal deployment."
        
        # Build Adaptive Card
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"PatchPulse Risk Analysis: {status}",
                                "size": "large",
                                "weight": "bolder",
                                "wrap": True
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {
                                        "title": "Risk Score:",
                                        "value": self.format_risk_score(risk_score)
                                    },
                                    {
                                        "title": "Mode:",
                                        "value": mode.upper()
                                    },
                                    {
                                        "title": "Status:",
                                        "value": "Allowed" if allowed else "Blocked"
                                    }
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": "**Top Issues:**",
                                "weight": "bolder",
                                "spacing": "medium"
                            },
                            {
                                "type": "TextBlock",
                                "text": reasons_text,
                                "wrap": True,
                                "spacing": "small"
                            }
                        ]
                    }
                }
            ]
        }
        
        # Add guardrails section if present
        if guardrails_text:
            card["attachments"][0]["content"]["body"].extend([
                {
                    "type": "TextBlock",
                    "text": "**Guardrails Triggered:**",
                    "weight": "bolder",
                    "spacing": "medium"
                },
                {
                    "type": "TextBlock",
                    "text": guardrails_text,
                    "wrap": True,
                    "spacing": "small"
                }
            ])
        
        # Add recommended action
        card["attachments"][0]["content"]["body"].append({
            "type": "TextBlock",
            "text": f"**Recommended Action:**\n{action}",
            "wrap": True,
            "spacing": "medium"
        })
        
        # Add action buttons
        actions = []
        if decision_id:
            actions.append({
                "type": "Action.OpenUrl",
                "title": "View Details",
                "url": f"{self.backend_url}/dashboard#/decisions/{decision_id}"
            })
        
        if actions:
            card["attachments"][0]["content"]["actions"] = actions
        
        return card
    
    def send_decision_notification(self, decision: Dict) -> bool:
        """Send decision notification to Teams."""
        if not self.webhook_url:
            logger.warning("Teams webhook URL not configured, skipping notification")
            return False
        
        try:
            message = self.format_decision_message(decision)
            
            async def send():
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        self.webhook_url,
                        json=message,
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    return True
            
            # For sync usage, we'll use httpx in sync mode
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self.webhook_url,
                    json=message,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
            
            logger.info(f"Sent Teams notification for decision {decision.get('decision_id')}")
            return True
        except Exception as e:
            logger.error(f"Error sending Teams message: {str(e)}")
            return False


def notify_on_decision(decision: Dict):
    """Convenience function to notify on decision."""
    notifier = TeamsNotifier()
    notifier.send_decision_notification(decision)


if __name__ == "__main__":
    # Example usage
    test_decision = {
        "change_event_id": "test-123",
        "decision_id": "dec-456",
        "risk_score": 75,
        "reasons": [
            "Resource limits removed",
            "High CPU usage detected",
            "HPA disabled"
        ],
        "guardrails_triggered": [
            {"id": "no_limits", "severity": 50, "message": "Resource limits removed"},
            {"id": "high_cpu", "severity": 30, "message": "High CPU usage detected"}
        ],
        "mode": "advisory",
        "allowed": True
    }
    
    notifier = TeamsNotifier()
    notifier.send_decision_notification(test_decision)



