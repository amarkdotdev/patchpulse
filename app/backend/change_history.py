"""Change history tracking and analysis."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import ChangeEventDB, DecisionDB


def get_change_history(
    repo: Optional[str] = None,
    days: int = 30,
    db: Session = None
) -> List[Dict]:
    """Get change history for a repository."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(ChangeEventDB).filter(ChangeEventDB.timestamp >= cutoff)
    
    if repo:
        query = query.filter(ChangeEventDB.repo == repo)
    
    events = query.order_by(ChangeEventDB.timestamp.desc()).all()
    
    history = []
    for event in events:
        # Get decisions for this event
        decisions = db.query(DecisionDB).filter(DecisionDB.change_event_id == event.id).all()
        
        history.append({
            "change_event_id": event.id,
            "repo": event.repo,
            "sha": event.sha,
            "pr_number": event.pr_number,
            "branch": event.branch,
            "timestamp": event.timestamp.isoformat(),
            "files_changed": len(event.files) if event.files else 0,
            "decisions_count": len(decisions),
            "latest_decision": {
                "risk_score": decisions[0].risk_score,
                "allowed": decisions[0].allowed,
                "created_at": decisions[0].created_at.isoformat()
            } if decisions else None
        })
    
    return history


def get_repository_stats(repo: str, days: int = 30, db: Session = None) -> Dict:
    """Get statistics for a repository."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    events = db.query(ChangeEventDB).filter(
        ChangeEventDB.repo == repo,
        ChangeEventDB.timestamp >= cutoff
    ).all()
    
    if not events:
        return {
            "repo": repo,
            "total_changes": 0,
            "period_days": days
        }
    
    # Get all decisions for these events
    event_ids = [e.id for e in events]
    decisions = db.query(DecisionDB).filter(DecisionDB.change_event_id.in_(event_ids)).all()
    
    return {
        "repo": repo,
        "total_changes": len(events),
        "total_decisions": len(decisions),
        "high_risk_changes": len([d for d in decisions if d.risk_score >= 70]),
        "blocked_changes": len([d for d in decisions if not d.allowed]),
        "avg_risk_score": sum(d.risk_score for d in decisions) / len(decisions) if decisions else 0,
        "period_days": days,
        "last_change": events[0].timestamp.isoformat() if events else None
    }

