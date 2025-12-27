"""FastAPI main application."""

import os
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from models import (
    ChangeEvent, ClusterSignal, Decision, DecisionResponse, GuardrailResult,
    ChangeEventDB, ClusterSignalDB, DecisionDB
)
from database import init_db, get_db
from policy_engine import evaluate_policy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(name)s"}'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
decision_counter = Counter('patchpulse_decisions_total', 'Total decisions made', ['mode', 'allowed'])
decision_risk_score = Histogram('patchpulse_risk_score', 'Risk score distribution', buckets=[0, 20, 40, 60, 80, 100])
request_duration = Histogram('patchpulse_request_duration_seconds', 'Request duration', ['endpoint'])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup."""
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="PatchPulse API",
    description="Pre-flight risk analysis and guardrail enforcement",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount UI static files
try:
    app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")
except Exception:
    logger.warning("UI directory not found, skipping static file mount")

# Mount marketing site
try:
    app.mount("/marketing", StaticFiles(directory="marketing", html=True), name="marketing")
except Exception:
    logger.warning("Marketing directory not found, skipping static file mount")


@app.get("/")
async def root():
    """Root endpoint - redirects to marketing site."""
    from fastapi.responses import RedirectResponse
    try:
        # Try to serve marketing index
        return RedirectResponse(url="/marketing/")
    except:
        return {
            "name": "PatchPulse API",
            "version": "1.0.0",
            "endpoints": {
                "marketing": "/marketing/",
                "dashboard": "/ui",
                "api": "/api/v1",
                "docs": "/docs"
            }
        }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/change-events", response_model=Dict)
async def create_change_event(
    change_event: ChangeEvent,
    db: Session = Depends(get_db)
):
    """Create a change event and evaluate policy."""
    with request_duration.labels(endpoint="create_change_event").time():
        # Store change event
        db_event = ChangeEventDB(**change_event.model_dump())
        db.add(db_event)
        db.flush()
        
        # Get recent cluster signals (last hour)
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=1)
        signals = db.query(ClusterSignalDB).filter(
            ClusterSignalDB.timestamp >= cutoff
        ).all()
        
        cluster_signals = [
            ClusterSignal(
                kind=s.kind,
                namespace=s.namespace,
                name=s.name,
                metric=s.metric,
                value=s.value,
                metadata=s.signal_metadata,
                timestamp=s.timestamp
            )
            for s in signals
        ]
        
        # Evaluate policy
        mode = os.getenv("POLICY_MODE", "advisory")
        policy_result = evaluate_policy(change_event, cluster_signals, mode)
        
        # Create decision - serialize guardrails properly
        guardrails_serialized = []
        for gr in policy_result["guardrails_triggered"]:
            if hasattr(gr, 'model_dump'):
                guardrails_serialized.append(gr.model_dump())
            elif isinstance(gr, dict):
                guardrails_serialized.append(gr)
            else:
                guardrails_serialized.append({
                    "id": getattr(gr, 'id', 'unknown'),
                    "severity": getattr(gr, 'severity', 0),
                    "message": getattr(gr, 'message', ''),
                    "evidence": getattr(gr, 'evidence', [])
                })
        
        # Serialize outputs with datetime handling
        outputs_serialized = json.loads(json.dumps(policy_result, default=str))
        
        decision = DecisionDB(
            change_event_id=db_event.id,
            risk_score=policy_result["risk_score"],
            reasons=policy_result["reasons"],
            guardrails_triggered=guardrails_serialized,
            mode=mode,
            allowed=policy_result["allowed"],
            evidence_refs=policy_result["evidence_refs"],
            policy_version="1.0.0",
            triggered_by="system",
            inputs=json.loads(json.dumps({"change_event": change_event.model_dump()}, default=str)),
            outputs=outputs_serialized
        )
        db.add(decision)
        db.commit()
        
        # Update metrics
        decision_counter.labels(mode=mode, allowed=policy_result["allowed"]).inc()
        decision_risk_score.observe(policy_result["risk_score"])
        
        logger.info(
            f"Decision created: change_event_id={db_event.id}, "
            f"risk_score={policy_result['risk_score']}, allowed={policy_result['allowed']}"
        )
        
        return {
            "change_event_id": db_event.id,
            "decision_id": decision.id,
            **policy_result
        }


@app.post("/api/v1/cluster-signals", response_model=Dict)
async def create_cluster_signal(
    signals: List[ClusterSignal],
    db: Session = Depends(get_db)
):
    """Create cluster signals from agent."""
    with request_duration.labels(endpoint="create_cluster_signal").time():
        db_signals = []
        for signal in signals:
            db_signal = ClusterSignalDB(**signal.model_dump())
            db.add(db_signal)
            db_signals.append(db_signal)
        
        db.commit()
        
        logger.info(f"Created {len(db_signals)} cluster signals")
        
        return {"created": len(db_signals)}


@app.get("/api/v1/decisions", response_model=List[DecisionResponse])
async def list_decisions(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List recent decisions."""
    decisions = db.query(DecisionDB).order_by(DecisionDB.created_at.desc()).limit(limit).all()
    
    results = []
    for d in decisions:
        results.append(DecisionResponse(
            id=d.id,
            change_event_id=d.change_event_id,
            risk_score=d.risk_score,
            reasons=d.reasons or [],
            guardrails_triggered=[GuardrailResult(**g) for g in (d.guardrails_triggered or [])],
            mode=d.mode,
            allowed=d.allowed,
            evidence_refs=d.evidence_refs or [],
            policy_version=d.policy_version,
            created_at=d.created_at
        ))
    
    return results


@app.get("/api/v1/decisions/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific decision with full details."""
    decision = db.query(DecisionDB).filter(DecisionDB.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    return DecisionResponse(
        id=decision.id,
        change_event_id=decision.change_event_id,
        risk_score=decision.risk_score,
        reasons=decision.reasons or [],
        guardrails_triggered=[GuardrailResult(**g) for g in (decision.guardrails_triggered or [])],
        mode=decision.mode,
        allowed=decision.allowed,
        evidence_refs=decision.evidence_refs or [],
        policy_version=decision.policy_version,
        created_at=decision.created_at
    )


@app.get("/api/v1/change-events/{change_event_id}")
async def get_change_event(
    change_event_id: str,
    db: Session = Depends(get_db)
):
    """Get a change event with its decisions."""
    event = db.query(ChangeEventDB).filter(ChangeEventDB.id == change_event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Change event not found")
    
    decisions = db.query(DecisionDB).filter(DecisionDB.change_event_id == change_event_id).all()
    
    return {
        "id": event.id,
        "source": event.source,
        "repo": event.repo,
        "sha": event.sha,
        "pr_number": event.pr_number,
        "files": event.files,
        "diff_hunks": event.diff_hunks,
        "timestamp": event.timestamp.isoformat(),
        "decisions": [
            {
                "id": d.id,
                "risk_score": d.risk_score,
                "allowed": d.allowed,
                "created_at": d.created_at.isoformat()
            }
            for d in decisions
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

