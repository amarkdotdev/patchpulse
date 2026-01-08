"""Email integration for risk notifications."""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send risk notifications via email."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        to_emails: Optional[List[str]] = None,
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("EMAIL_FROM", "patchpulse@example.com")
        self.to_emails = to_emails or os.getenv("EMAIL_TO", "").split(",")
        self.use_tls = use_tls
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
    
    def format_decision_email(self, decision: Dict) -> tuple:
        """Format decision as HTML and plain text email."""
        risk_score = decision.get("risk_score", 0)
        reasons = decision.get("reasons", [])[:10]  # Top 10
        guardrails = decision.get("guardrails_triggered", [])
        mode = decision.get("mode", "advisory")
        allowed = decision.get("allowed", True)
        change_event_id = decision.get("change_event_id")
        decision_id = decision.get("decision_id")
        repo = decision.get("repo", "Unknown")
        pr_number = decision.get("pr_number")
        
        # Determine status
        if not allowed:
            status = "❌ BLOCKED"
            status_color = "#dc3545"
        elif risk_score >= 70:
            status = "⚠️ HIGH RISK"
            status_color = "#ff9800"
        else:
            status = "✅ ALLOWED"
            status_color = "#4caf50"
        
        # Build reasons HTML
        reasons_html = "<ul>"
        for r in reasons:
            reasons_html += f"<li>{r}</li>"
        reasons_html += "</ul>" if reasons else "<p>No specific issues detected</p>"
        
        # Build guardrails HTML
        guardrails_html = ""
        if guardrails:
            guardrails_html = "<ul>"
            for gr in guardrails[:10]:
                severity_emoji = "🔴" if gr.get("severity", 0) >= 50 else "🟠" if gr.get("severity", 0) >= 30 else "🟡"
                guardrails_html += f"<li>{severity_emoji} {gr.get('message', 'Unknown')}</li>"
            guardrails_html += "</ul>"
        
        # Recommended action
        if not allowed:
            action = "🚫 Change should not be merged. Review guardrails and fix issues."
        elif risk_score >= 70:
            action = "⚠️ Consider canary deployment or rollback plan before merging."
        elif risk_score >= 40:
            action = "💡 Review changes carefully. Consider adding resource limits or monitoring."
        else:
            action = "✅ Change looks safe. Proceed with normal deployment."
        
        # HTML email
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {status_color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .footer {{ background-color: #f0f0f0; padding: 10px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
                .risk-score {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
                .section {{ margin: 20px 0; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
                .button-danger {{ background-color: #dc3545; }}
                ul {{ margin: 10px 0; padding-left: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PatchPulse Risk Analysis</h1>
                    <div class="risk-score">{status}</div>
                </div>
                <div class="content">
                    <div class="section">
                        <h2>Decision Summary</h2>
                        <p><strong>Repository:</strong> {repo}</p>
                        <p><strong>PR/MR Number:</strong> {pr_number or 'N/A'}</p>
                        <p><strong>Risk Score:</strong> {self.format_risk_score(risk_score)}</p>
                        <p><strong>Mode:</strong> {mode.upper()}</p>
                        <p><strong>Status:</strong> {"Allowed" if allowed else "Blocked"}</p>
                    </div>
                    
                    <div class="section">
                        <h3>Top Issues</h3>
                        {reasons_html}
                    </div>
                    
                    {f'<div class="section"><h3>Guardrails Triggered</h3>{guardrails_html}</div>' if guardrails_html else ''}
                    
                    <div class="section">
                        <h3>Recommended Action</h3>
                        <p>{action}</p>
                    </div>
                    
                    {f'<div class="section"><a href="{self.backend_url}/dashboard#/decisions/{decision_id}" class="button">View Details</a></div>' if decision_id else ''}
                </div>
                <div class="footer">
                    <p>This is an automated notification from PatchPulse</p>
                    <p>Generated at {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text email
        text_body = f"""
PatchPulse Risk Analysis: {status}

Repository: {repo}
PR/MR Number: {pr_number or 'N/A'}
Risk Score: {self.format_risk_score(risk_score)}
Mode: {mode.upper()}
Status: {"Allowed" if allowed else "Blocked"}

Top Issues:
{chr(10).join([f"• {r}" for r in reasons]) if reasons else "No specific issues detected"}

{f'Guardrails Triggered:{chr(10)}{chr(10).join([f"• {gr.get(\"message\", \"Unknown\")}" for gr in guardrails[:10]])}' if guardrails else ''}

Recommended Action:
{action}

{f'View Details: {self.backend_url}/dashboard#/decisions/{decision_id}' if decision_id else ''}

---
This is an automated notification from PatchPulse
Generated at {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
        """
        
        return html_body, text_body
    
    def send_decision_notification(self, decision: Dict, subject: Optional[str] = None) -> bool:
        """Send decision notification via email."""
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email notification")
            return False
        
        if not self.to_emails or not any(self.to_emails):
            logger.warning("No recipient emails configured, skipping email notification")
            return False
        
        try:
            risk_score = decision.get("risk_score", 0)
            allowed = decision.get("allowed", True)
            repo = decision.get("repo", "Unknown")
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = ", ".join([email.strip() for email in self.to_emails if email.strip()])
            msg["Subject"] = subject or f"PatchPulse Alert: {risk_score}/100 Risk - {repo} ({'Blocked' if not allowed else 'Allowed'})"
            
            # Get email content
            html_body, text_body = self.format_decision_email(decision)
            
            # Add parts
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Sent email notification for decision {decision.get('decision_id')}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False


def notify_on_decision(decision: Dict):
    """Convenience function to notify on decision."""
    notifier = EmailNotifier()
    notifier.send_decision_notification(decision)


if __name__ == "__main__":
    # Example usage
    test_decision = {
        "change_event_id": "test-123",
        "decision_id": "dec-456",
        "risk_score": 75,
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
        "allowed": True
    }
    
    notifier = EmailNotifier()
    notifier.send_decision_notification(test_decision)



