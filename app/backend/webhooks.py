"""Webhook system for outbound notifications."""

import os
import json
import logging
import httpx
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON
from models import Base

logger = logging.getLogger(__name__)


class WebhookDB(Base):
    """Webhook configuration in database."""
    __tablename__ = "webhooks"
    
    id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    events = Column(JSON)  # List of event types: decision_created, decision_blocked, high_risk, etc.
    secret = Column(String)  # Optional webhook secret for verification
    enabled = Column(Boolean, default=True)
    headers = Column(JSON)  # Custom headers to include
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_triggered = Column(DateTime)
    failure_count = Column(String, default="0")  # Store as string to avoid type issues


async def trigger_webhook(webhook: WebhookDB, event_type: str, payload: Dict) -> bool:
    """Trigger a webhook with the given payload."""
    if not webhook.enabled:
        return False
    
    if webhook.events and event_type not in webhook.events:
        return False
    
    try:
        headers = {
            "Content-Type": "application/json",
            "X-PatchPulse-Event": event_type,
            "X-PatchPulse-Timestamp": datetime.utcnow().isoformat()
        }
        
        # Add custom headers
        if webhook.headers:
            headers.update(webhook.headers)
        
        # Add webhook secret if configured
        if webhook.secret:
            headers["X-PatchPulse-Signature"] = webhook.secret
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            logger.info(f"Webhook triggered successfully: {webhook.url} for event {event_type}")
            return True
            
    except Exception as e:
        logger.error(f"Webhook failed: {webhook.url} - {str(e)}")
        # Update failure count
        try:
            failure_count = int(webhook.failure_count or "0") + 1
            webhook.failure_count = str(failure_count)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to update webhook failure count: {e}")
            pass
        return False


async def trigger_webhooks_for_decision(
    db,
    decision_id: str,
    decision_data: Dict,
    event_type: str = "decision_created"
):
    """Trigger all relevant webhooks for a decision."""
    from models import DecisionDB
    from sqlalchemy.orm import Session
    
    webhooks = db.query(WebhookDB).filter(WebhookDB.enabled == True).all()
    
    if not webhooks:
        return
    
    # Determine event type based on decision
    decision = db.query(DecisionDB).filter(DecisionDB.id == decision_id).first()
    if decision:
        if not decision.allowed:
            event_type = "decision_blocked"
        elif decision.risk_score >= 70:
            event_type = "high_risk"
    
    payload = {
        "event": event_type,
        "decision": decision_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Trigger all matching webhooks
    for webhook in webhooks:
        await trigger_webhook(webhook, event_type, payload)
        
        # Update last_triggered
        webhook.last_triggered = datetime.utcnow()
        db.commit()


