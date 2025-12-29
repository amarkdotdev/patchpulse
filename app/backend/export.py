"""Export functionality for decisions and analytics."""

import csv
import json
import io
from datetime import datetime
from typing import List, Dict, Any
from fastapi.responses import Response
from sqlalchemy.orm import Session
from models import DecisionDB, ChangeEventDB


def export_decisions_csv(decisions: List[DecisionDB], change_events: Dict[str, ChangeEventDB]) -> Response:
    """Export decisions to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Decision ID",
        "Change Event ID",
        "Repository",
        "PR/MR Number",
        "SHA",
        "Risk Score",
        "Allowed",
        "Mode",
        "Guardrails Triggered",
        "Reasons",
        "Created At"
    ])
    
    # Write data
    for decision in decisions:
        change_event = change_events.get(decision.change_event_id)
        guardrails = ", ".join([gr.get('id', 'unknown') for gr in (decision.guardrails_triggered or [])])
        reasons = "; ".join(decision.reasons or [])
        
        writer.writerow([
            decision.id,
            decision.change_event_id,
            change_event.repo if change_event else "N/A",
            change_event.pr_number if change_event else "N/A",
            change_event.sha if change_event else "N/A",
            decision.risk_score,
            "Yes" if decision.allowed else "No",
            decision.mode,
            guardrails,
            reasons,
            decision.created_at.isoformat()
        ])
    
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=patchpulse_decisions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


def export_decisions_json(decisions: List[DecisionDB], change_events: Dict[str, ChangeEventDB]) -> Response:
    """Export decisions to JSON format."""
    data = []
    for decision in decisions:
        change_event = change_events.get(decision.change_event_id)
        data.append({
            "id": decision.id,
            "change_event_id": decision.change_event_id,
            "change_event": {
                "repo": change_event.repo if change_event else None,
                "pr_number": change_event.pr_number if change_event else None,
                "sha": change_event.sha if change_event else None,
                "branch": change_event.branch if change_event else None,
                "source": change_event.source if change_event else None,
            } if change_event else None,
            "risk_score": decision.risk_score,
            "allowed": decision.allowed,
            "mode": decision.mode,
            "guardrails_triggered": decision.guardrails_triggered or [],
            "reasons": decision.reasons or [],
            "evidence_refs": decision.evidence_refs or [],
            "policy_version": decision.policy_version,
            "created_at": decision.created_at.isoformat()
        })
    
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=patchpulse_decisions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )


def export_analytics_report(db: Session) -> Response:
    """Export comprehensive analytics report."""
    from datetime import timedelta
    from sqlalchemy import func
    
    now = datetime.utcnow()
    last_30d = now - timedelta(days=30)
    
    # Gather analytics data
    total_decisions = db.query(func.count(DecisionDB.id)).scalar() or 0
    high_risk = db.query(func.count(DecisionDB.id)).filter(DecisionDB.risk_score >= 70).scalar() or 0
    blocked = db.query(func.count(DecisionDB.id)).filter(DecisionDB.allowed == False).scalar() or 0
    avg_risk = db.query(func.avg(DecisionDB.risk_score)).scalar() or 0
    
    # Recent decisions
    recent = db.query(DecisionDB).filter(
        DecisionDB.created_at >= last_30d
    ).order_by(DecisionDB.created_at.desc()).limit(100).all()
    
    # Guardrail statistics
    guardrail_counts = {}
    for decision in db.query(DecisionDB).all():
        if decision.guardrails_triggered:
            for gr in decision.guardrails_triggered:
                gr_id = gr.get('id', 'unknown')
                guardrail_counts[gr_id] = guardrail_counts.get(gr_id, 0) + 1
    
    report = {
        "generated_at": now.isoformat(),
        "summary": {
            "total_decisions": total_decisions,
            "high_risk_decisions": high_risk,
            "blocked_decisions": blocked,
            "average_risk_score": round(float(avg_risk), 2),
            "block_rate": round((blocked / total_decisions * 100) if total_decisions > 0 else 0, 2)
        },
        "guardrail_statistics": guardrail_counts,
        "recent_decisions": [
            {
                "id": d.id,
                "risk_score": d.risk_score,
                "allowed": d.allowed,
                "created_at": d.created_at.isoformat()
            }
            for d in recent
        ]
    }
    
    return Response(
        content=json.dumps(report, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=patchpulse_analytics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )

