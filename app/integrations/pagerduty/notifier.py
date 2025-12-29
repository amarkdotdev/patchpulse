"""PagerDuty integration for risk notifications."""

import os
import json
import httpx
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PagerDutyNotifier:
    """Send risk notifications to PagerDuty."""
    
    def __init__(self, integration_key: Optional[str] = None):
        self.integration_key = integration_key or os.getenv("PAGERDUTY_INTEGRATION_KEY")
        self.events_api_url = "https://events.pagerduty.com/v2/enqueue"
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    def determine_severity(self, risk_score: int, allowed: bool) -> str:
        """Determine PagerDuty severity based on risk score."""
        if not allowed:
            return "critical"  # Blocked changes are critical
        elif risk_score >= 80:
            return "critical"
        elif risk_score >= 60:
            return "error"
        elif risk_score >= 40:
            return "warning"
        else:
            return "info"
    
    def format_decision_event(self, decision: Dict) -> Dict:
        """Format decision as PagerDuty event."""
        risk_score = decision.get("risk_score", 0)
        allowed = decision.get("allowed", True)
        reasons = decision.get("reasons", [])[:5]
        guardrails = decision.get("guardrails_triggered", [])
        mode = decision.get("mode", "advisory")
        change_event_id = decision.get("change_event_id")
        decision_id = decision.get("decision_id")
        repo = decision.get("repo", "Unknown")
        pr_number = decision.get("pr_number")
        
        severity = self.determine_severity(risk_score, allowed)
        
        # Build summary
        status = "BLOCKED" if not allowed else "HIGH RISK" if risk_score >= 70 else "ALLOWED"
        summary = f"PatchPulse: {status} - Risk Score {risk_score}/100 - {repo}"
        
        # Build details
        details = {
            "risk_score": risk_score,
            "status": "blocked" if not allowed else "allowed",
            "mode": mode,
            "repository": repo,
            "pr_number": pr_number,
            "decision_id": decision_id,
            "change_event_id": change_event_id,
            "top_issues": reasons,
            "guardrails_triggered": len(guardrails),
            "guardrail_details": [
                {
                    "id": gr.get("id"),
                    "message": gr.get("message"),
                    "severity": gr.get("severity", 0)
                }
                for gr in guardrails[:5]
            ],
            "dashboard_url": f"{self.backend_url}/dashboard#/decisions/{decision_id}" if decision_id else None
        }
        
        # Build custom details for PagerDuty
        custom_details = {
            "Risk Score": f"{risk_score}/100",
            "Status": status,
            "Repository": repo,
            "PR/MR Number": str(pr_number) if pr_number else "N/A",
            "Mode": mode.upper(),
            "Top Issues": "; ".join(reasons[:3]) if reasons else "None",
            "Guardrails Triggered": len(guardrails)
        }
        
        # Determine event action
        if not allowed or risk_score >= 80:
            event_action = "trigger"  # Create incident
        elif risk_score >= 60:
            event_action = "trigger"  # Create incident for high risk
        else:
            event_action = "acknowledge"  # Just acknowledge, don't create incident
        
        event = {
            "routing_key": self.integration_key,
            "event_action": event_action,
            "payload": {
                "summary": summary,
                "severity": severity,
                "source": "PatchPulse",
                "custom_details": custom_details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Add dedup_key for resolving/acknowledging
        if decision_id:
            event["dedup_key"] = f"patchpulse-{decision_id}"
        
        return event
    
    def send_decision_notification(self, decision: Dict) -> bool:
        """Send decision notification to PagerDuty."""
        if not self.integration_key:
            logger.warning("PagerDuty integration key not configured, skipping notification")
            return False
        
        try:
            event = self.format_decision_event(decision)
            
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self.events_api_url,
                    json=event,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get("status") == "success":
                    logger.info(f"Sent PagerDuty notification for decision {decision.get('decision_id')}")
                    return True
                else:
                    logger.error(f"PagerDuty API returned error: {result}")
                    return False
        except Exception as e:
            logger.error(f"Error sending PagerDuty event: {str(e)}")
            return False
    
    def resolve_incident(self, decision_id: str, note: Optional[str] = None) -> bool:
        """Resolve a PagerDuty incident."""
        if not self.integration_key:
            return False
        
        try:
            event = {
                "routing_key": self.integration_key,
                "event_action": "resolve",
                "dedup_key": f"patchpulse-{decision_id}",
                "payload": {
                    "summary": f"PatchPulse decision {decision_id} resolved",
                    "source": "PatchPulse"
                }
            }
            
            if note:
                event["payload"]["custom_details"] = {"resolution_note": note}
            
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self.events_api_url,
                    json=event,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Error resolving PagerDuty incident: {str(e)}")
            return False


def notify_on_decision(decision: Dict):
    """Convenience function to notify on decision."""
    notifier = PagerDutyNotifier()
    notifier.send_decision_notification(decision)


if __name__ == "__main__":
    # Example usage
    test_decision = {
        "change_event_id": "test-123",
        "decision_id": "dec-456",
        "risk_score": 85,
        "repo": "my-org/production-configs",
        "pr_number": 123,
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
        "allowed": False
    }
    
    notifier = PagerDutyNotifier()
    notifier.send_decision_notification(test_decision)

