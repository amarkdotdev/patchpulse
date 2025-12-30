"""Scheduled report generation."""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import DecisionDB, ChangeEventDB
from export import export_analytics_report

logger = logging.getLogger(__name__)


class ScheduledReport:
    """Scheduled report configuration."""
    
    def __init__(
        self,
        id: str,
        name: str,
        schedule: str,  # daily, weekly, monthly
        recipients: List[str],
        format: str = "json",  # json, csv
        filters: Optional[Dict] = None
    ):
        self.id = id
        self.name = name
        self.schedule = schedule
        self.recipients = recipients
        self.format = format
        self.filters = filters or {}
        self.last_run = None
        self.next_run = None


def generate_scheduled_report(report_config: ScheduledReport, db: Session) -> Dict:
    """Generate a scheduled report."""
    try:
        # Calculate date range based on schedule
        now = datetime.utcnow()
        if report_config.schedule == "daily":
            start_date = now - timedelta(days=1)
        elif report_config.schedule == "weekly":
            start_date = now - timedelta(days=7)
        elif report_config.schedule == "monthly":
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=7)
        
        # Query decisions
        query = db.query(DecisionDB).filter(DecisionDB.created_at >= start_date)
        
        # Apply filters
        if report_config.filters.get("min_risk_score"):
            query = query.filter(DecisionDB.risk_score >= report_config.filters["min_risk_score"])
        
        if report_config.filters.get("allowed") is not None:
            query = query.filter(DecisionDB.allowed == report_config.filters["allowed"])
        
        decisions = query.order_by(DecisionDB.created_at.desc()).all()
        
        # Generate report data
        report_data = {
            "report_id": report_config.id,
            "report_name": report_config.name,
            "generated_at": now.isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": now.isoformat(),
                "schedule": report_config.schedule
            },
            "summary": {
                "total_decisions": len(decisions),
                "high_risk": len([d for d in decisions if d.risk_score >= 70]),
                "blocked": len([d for d in decisions if not d.allowed]),
                "avg_risk_score": sum(d.risk_score for d in decisions) / len(decisions) if decisions else 0
            },
            "decisions": [
                {
                    "id": d.id,
                    "risk_score": d.risk_score,
                    "allowed": d.allowed,
                    "created_at": d.created_at.isoformat()
                }
                for d in decisions[:100]  # Limit to 100 most recent
            ]
        }
        
        return report_data
        
    except Exception as e:
        logger.error(f"Error generating scheduled report: {str(e)}")
        raise

