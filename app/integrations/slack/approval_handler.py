"""Slack/Teams Approval Handler with Context."""

import os
import hmac
import hashlib
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

approval_app = FastAPI(title="PatchPulse Approval Handler")

# Store nonces to prevent replay attacks
used_nonces = set()
NONCE_EXPIRY = 300  # 5 minutes


def verify_slack_signature(
    timestamp: str,
    signature: str,
    body: str,
    signing_secret: str
) -> bool:
    """Verify Slack request signature."""
    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False  # Request too old
    
    sig_basestring = f"v0:{timestamp}:{body}"
    computed_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)


def format_approval_message(decision: Dict, context: Dict) -> Dict:
    """Format approval message with full context."""
    risk_score = decision.get("risk_score", 0)
    reasons = decision.get("reasons", [])[:5]
    guardrails = decision.get("guardrails_triggered", [])[:5]
    
    # Build diff snippet
    diff_snippet = context.get("diff_snippet", "No diff available")
    if len(diff_snippet) > 500:
        diff_snippet = diff_snippet[:500] + "..."
    
    # Build impacted resources
    impacted = context.get("impacted_resources", [])
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔒 Approval Required: Risk Score {risk_score}/100"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Repository:*\n{decision.get('repo', 'Unknown')}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*PR/MR:*\n#{decision.get('pr_number', 'N/A')}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Top Issues:*\n" + "\n".join([f"• {r}" for r in reasons])
            }
        }
    ]
    
    if diff_snippet:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Change Summary:*\n```\n{diff_snippet}\n```"
            }
        })
    
    if impacted:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Impacted Resources:*\n" + "\n".join([f"• {r}" for r in impacted[:5]])
            }
        })
    
    # Add approval buttons with context
    decision_id = decision.get("decision_id", "")
    nonce = hashlib.sha256(f"{decision_id}{time.time()}".encode()).hexdigest()[:16]
    
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Approve"},
                "style": "primary",
                "value": f"approve_{decision_id}",
                "action_id": "approve_decision"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Approve (24h Exception)"},
                "value": f"approve_24h_{decision_id}",
                "action_id": "approve_24h"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Approve (Repo Exception)"},
                "value": f"approve_repo_{decision_id}",
                "action_id": "approve_repo"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Reject"},
                "style": "danger",
                "value": f"reject_{decision_id}",
                "action_id": "reject_decision"
            }
        ]
    })
    
    return {
        "blocks": blocks,
        "metadata": {
            "decision_id": decision_id,
            "nonce": nonce,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


@approval_app.post("/slack/approval")
async def handle_slack_approval(
    request: Request,
    x_slack_signature: Optional[str] = Header(None),
    x_slack_request_timestamp: Optional[str] = Header(None)
):
    """Handle Slack approval button click."""
    try:
        body = await request.body()
        body_text = body.decode()
        payload = json.loads(request.form.get("payload", "{}"))
        
        # Verify signature
        signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        if signing_secret and x_slack_signature:
            if not verify_slack_signature(
                x_slack_request_timestamp or "",
                x_slack_signature,
                body_text,
                signing_secret
            ):
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Extract action
        action = payload.get("actions", [{}])[0]
        action_id = action.get("action_id")
        value = action.get("value", "")
        user = payload.get("user", {})
        
        # Check nonce (prevent replay)
        nonce = payload.get("metadata", {}).get("nonce")
        if nonce and nonce in used_nonces:
            raise HTTPException(status_code=400, detail="Replay attack detected")
        if nonce:
            used_nonces.add(nonce)
        
        # Parse decision ID
        decision_id = value.split("_")[-1] if "_" in value else ""
        
        # Handle different approval types
        if action_id == "approve_decision":
            # Standard approval
            return {
                "response_type": "ephemeral",
                "text": f"✅ Decision {decision_id} approved by {user.get('name', 'user')}"
            }
        elif action_id == "approve_24h":
            # Time-bound exception
            expiry = datetime.utcnow() + timedelta(hours=24)
            return {
                "response_type": "ephemeral",
                "text": f"✅ Decision {decision_id} approved with 24h exception (expires {expiry.isoformat()})"
            }
        elif action_id == "approve_repo":
            # Repo-scoped exception
            return {
                "response_type": "ephemeral",
                "text": f"✅ Decision {decision_id} approved for repository scope"
            }
        elif action_id == "reject_decision":
            return {
                "response_type": "ephemeral",
                "text": f"❌ Decision {decision_id} rejected by {user.get('name', 'user')}"
            }
        
        return {"response_type": "ephemeral", "text": "Action processed"}
        
    except Exception as e:
        logger.error(f"Approval handler error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

