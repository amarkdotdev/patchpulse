"""Slack integration for risk notifications."""

import os
from typing import List, Dict, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackNotifier:
    """Send risk notifications to Slack."""
    
    def __init__(self, token: Optional[str] = None, channel: Optional[str] = None):
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.channel = channel or os.getenv("SLACK_CHANNEL", "#patchpulse")
        self.client = WebClient(token=self.token) if self.token else None
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
        """Format decision as Slack message."""
        risk_score = decision.get("risk_score", 0)
        reasons = decision.get("reasons", [])[:5]  # Top 5
        guardrails = decision.get("guardrails_triggered", [])
        mode = decision.get("mode", "advisory")
        allowed = decision.get("allowed", True)
        change_event_id = decision.get("change_event_id")
        decision_id = decision.get("decision_id")
        
        # Determine status
        if not allowed:
            status = "❌ BLOCKED"
            color = "danger"
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
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"PatchPulse Risk Analysis: {status}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Risk Score:*\n{self.format_risk_score(risk_score)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Mode:*\n{mode.upper()}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top Issues:*\n{reasons_text}"
                }
            }
        ]
        
        if guardrails_text:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Guardrails Triggered:*\n{guardrails_text}"
                }
            })
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommended Action:*\n{action}"
            }
        })
        
        # Add interactive buttons
        if decision_id:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Details"
                        },
                        "url": f"{self.backend_url}/ui/#/decisions/{decision_id}",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve" if allowed else "Override"
                        },
                        "value": f"approve_{decision_id}",
                        "action_id": "approve_decision"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Deny"
                        },
                        "value": f"deny_{decision_id}",
                        "action_id": "deny_decision",
                        "style": "danger"
                    }
                ]
            })
        
        return {
            "blocks": blocks,
            "color": color
        }
    
    def send_decision_notification(self, decision: Dict) -> bool:
        """Send decision notification to Slack."""
        if not self.client:
            print("Slack client not configured, skipping notification")
            return False
        
        try:
            message = self.format_decision_message(decision)
            
            response = self.client.chat_postMessage(
                channel=self.channel,
                blocks=message["blocks"],
                text=f"PatchPulse Risk Analysis: {decision.get('risk_score', 0)}/100"
            )
            
            print(f"Sent Slack notification: {response['ts']}")
            return True
        except SlackApiError as e:
            print(f"Error sending Slack message: {e.response['error']}")
            return False
    
    def handle_button_callback(self, payload: Dict) -> Dict:
        """Handle Slack button callback."""
        action = payload.get("actions", [{}])[0]
        action_id = action.get("action_id")
        value = action.get("value", "")
        
        if action_id == "approve_decision":
            decision_id = value.replace("approve_", "")
            # In a real implementation, this would update the decision in the backend
            return {"text": f"Decision {decision_id} approved"}
        elif action_id == "deny_decision":
            decision_id = value.replace("deny_", "")
            return {"text": f"Decision {decision_id} denied"}
        
        return {"text": "Unknown action"}


def notify_on_decision(decision: Dict):
    """Convenience function to notify on decision."""
    notifier = SlackNotifier()
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
    
    notifier = SlackNotifier()
    notifier.send_decision_notification(test_decision)

