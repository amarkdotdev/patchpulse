"""FastAPI main application."""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
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
from ai_features import (
    get_security_vulnerabilities,
    get_change_recommendations,
    predict_incident_risk,
    get_cost_optimization_suggestions
)

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

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []

async def broadcast_decision(decision_data: dict):
    """Broadcast new decision to all connected WebSocket clients."""
    if active_connections:
        message = json.dumps(decision_data)
        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        # Remove disconnected clients
        for conn in disconnected:
            if conn in active_connections:
                active_connections.remove(conn)


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

# Mount UI static files as dashboard
try:
    app.mount("/dashboard", StaticFiles(directory="/app/ui", html=True), name="dashboard")
    logger.info("Dashboard mounted at /dashboard")
except Exception:
    logger.warning("UI directory not found, skipping static file mount")


@app.get("/")
async def root():
    """Serve marketing index page at root."""
    from fastapi.responses import FileResponse
    import os
    index_path = os.path.join("/app/website", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"name": "PatchPulse API", "version": "1.0.0"}


@app.get("/{path:path}")
async def serve_marketing(path: str):
    """Serve marketing static files."""
    from fastapi.responses import FileResponse
    import os
    
    # Don't serve API routes, dashboard, docs, or health
    if path.startswith("api/") or path.startswith("dashboard") or path.startswith("docs") or path == "health" or path == "metrics":
        raise HTTPException(status_code=404)
    
    # Try marketing directory first
    file_path = os.path.join("marketing", path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Try as HTML file
    if not path.endswith((".html", ".css", ".js", ".png", ".jpg", ".svg", ".ico", ".json")):
        html_path = os.path.join("marketing", f"{path}.html")
        if os.path.exists(html_path):
            return FileResponse(html_path)
    
    # Default to index.html for directories
    index_path = os.path.join("marketing", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "PatchPulse API",
        "version": "1.0.0",
        "endpoints": {
            "dashboard": "/dashboard",
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


@app.post("/api/v1/auth/login")
async def login(request: Request):
    """Login endpoint - authenticates users and returns JWT token."""
    from backend.auth import create_access_token
    try:
        body = await request.json()
        email = body.get("email", "")
        password = body.get("password", "")
        
        # For demo/production: validate credentials
        # In production, verify against your auth provider (Auth0, Okta, etc.)
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password required")
        
        # Demo mode: accept any credentials
        # Production: verify against database/auth provider
        user_id = email.split("@")[0] if "@" in email else email
        
        access_token = create_access_token(
            data={"sub": user_id, "email": email, "role": "user"}
        )
        
        logger.info(f"User logged in: {email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user_id,
                "email": email,
                "role": "user"
            }
        }
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


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
        
        # Get AI-powered features
        ai_features = {}
        try:
            # Security vulnerability scanning
            security_scan = get_security_vulnerabilities(
                diff_hunks=change_event.diff_hunks,
                files=change_event.files,
                cluster_signals=[s.model_dump() for s in cluster_signals]
            )
            ai_features["security_scan"] = security_scan
            
            # Change recommendations
            recommendations = get_change_recommendations(
                diff_hunks=change_event.diff_hunks,
                files=change_event.files,
                risk_score=policy_result["risk_score"],
                guardrails_triggered=[gr.model_dump() if hasattr(gr, 'model_dump') else gr for gr in policy_result["guardrails_triggered"]]
            )
            ai_features["recommendations"] = recommendations
            
            # Cost optimization
            cost_optimization = get_cost_optimization_suggestions(
                diff_hunks=change_event.diff_hunks,
                cluster_signals=[s.model_dump() for s in cluster_signals]
            )
            ai_features["cost_optimization"] = cost_optimization
            
            # Incident prediction (get recent decisions for context)
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=7)
            recent_decisions = db.query(DecisionDB).filter(
                DecisionDB.created_at >= cutoff
            ).order_by(DecisionDB.created_at.desc()).limit(10).all()
            
            historical_decisions = [
                {
                    "risk_score": d.risk_score,
                    "allowed": d.allowed,
                    "created_at": d.created_at.isoformat()
                }
                for d in recent_decisions
            ]
            
            incident_prediction = predict_incident_risk(
                change_event=change_event.model_dump(),
                cluster_signals=[s.model_dump() for s in cluster_signals],
                historical_decisions=historical_decisions
            )
            ai_features["incident_prediction"] = incident_prediction
            
        except Exception as e:
            logger.error(f"AI features failed: {str(e)}", exc_info=True)
            # Continue without AI features if they fail
        
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
        
        # Serialize outputs with datetime handling and AI features
        outputs_serialized = json.loads(json.dumps(policy_result, default=str))
        if ai_features:
            outputs_serialized["ai_features"] = ai_features
        
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
        
        # Broadcast to WebSocket clients
        decision_data = {
            "type": "new_decision",
            "decision_id": decision.id,
            "change_event_id": db_event.id,
            "risk_score": policy_result["risk_score"],
            "allowed": policy_result["allowed"],
            "timestamp": decision.created_at.isoformat()
        }
        await broadcast_decision(decision_data)
        
        from security import validate_no_key_leakage, sanitize_for_logging
        
        response = {
            "change_event_id": db_event.id,
            "decision_id": decision.id,
            **policy_result
        }
        
        # Add AI features to response (but NEVER expose API key)
        if ai_features:
            response["ai_features"] = ai_features
        
        # SECURITY: Validate no API key leakage before returning
        response = validate_no_key_leakage(response)
        
        return response


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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep connection alive and handle ping/pong
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)


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


@app.get("/api/v1/analytics/summary")
async def get_analytics_summary(db: Session = Depends(get_db)):
    """Get analytics summary."""
    from datetime import timedelta
    from sqlalchemy import func
    
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    total_decisions = db.query(func.count(DecisionDB.id)).scalar() or 0
    decisions_24h = db.query(func.count(DecisionDB.id)).filter(DecisionDB.created_at >= last_24h).scalar() or 0
    decisions_7d = db.query(func.count(DecisionDB.id)).filter(DecisionDB.created_at >= last_7d).scalar() or 0
    
    blocked_count = db.query(func.count(DecisionDB.id)).filter(DecisionDB.allowed == False).scalar() or 0
    high_risk_count = db.query(func.count(DecisionDB.id)).filter(DecisionDB.risk_score >= 60).scalar() or 0
    
    avg_risk = db.query(func.avg(DecisionDB.risk_score)).scalar()
    avg_risk = round(avg_risk, 1) if avg_risk else 0
    
    # Top guardrails triggered
    from sqlalchemy import text
    guardrail_counts = {}
    decisions = db.query(DecisionDB).all()
    for d in decisions:
        if d.guardrails_triggered:
            for gr in d.guardrails_triggered:
                gr_id = gr.get('id', 'unknown')
                guardrail_counts[gr_id] = guardrail_counts.get(gr_id, 0) + 1
    
    top_guardrails = sorted(guardrail_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_decisions": total_decisions,
        "decisions_24h": decisions_24h,
        "decisions_7d": decisions_7d,
        "blocked_count": blocked_count,
        "high_risk_count": high_risk_count,
        "avg_risk_score": avg_risk,
        "top_guardrails": [{"id": g[0], "count": g[1]} for g in top_guardrails]
    }


@app.get("/api/v1/analytics/risk-trend")
async def get_risk_trend(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get risk score trend over time."""
    from datetime import timedelta
    from sqlalchemy import func, cast, Date
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Group by date and calculate average risk
    results = db.query(
        cast(DecisionDB.created_at, Date).label('date'),
        func.avg(DecisionDB.risk_score).label('avg_risk'),
        func.count(DecisionDB.id).label('count')
    ).filter(
        DecisionDB.created_at >= cutoff
    ).group_by(
        cast(DecisionDB.created_at, Date)
    ).order_by('date').all()
    
    return [
        {
            "date": r.date.isoformat(),
            "avg_risk": round(float(r.avg_risk), 1),
            "count": r.count
        }
        for r in results
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

