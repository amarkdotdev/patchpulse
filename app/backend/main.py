"""FastAPI main application."""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request
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
try:
    from models import BlogPost, BlogPostDB, BlogPostCreate, BlogPostUpdate
except ImportError:
    BlogPost = BlogPostDB = BlogPostCreate = BlogPostUpdate = None
try:
    from models import User, UserDB, UserSignup, UserLogin
except ImportError:
    User = UserDB = UserSignup = UserLogin = None
try:
    from models import (
        Webhook, WebhookCreate, WebhookUpdate,
        ApprovalRequest, ApprovalResponse,
        BulkOperationRequest, ChangeComparisonRequest, ChangeComparison
    )
except ImportError:
    Webhook = WebhookCreate = WebhookUpdate = None
    ApprovalRequest = ApprovalResponse = None
    BulkOperationRequest = ChangeComparisonRequest = ChangeComparison = None
from database import init_db, get_db
from policy_engine import evaluate_policy
from ai_features import (
    get_security_vulnerabilities,
    get_change_recommendations,
    predict_incident_risk,
    get_cost_optimization_suggestions
)
try:
    from export import export_decisions_csv, export_decisions_json, export_analytics_report
except ImportError:
    export_decisions_csv = export_decisions_json = export_analytics_report = None
try:
    from webhooks import WebhookDB, trigger_webhooks_for_decision
except ImportError:
    WebhookDB = None
    trigger_webhooks_for_decision = None
from export import export_decisions_csv, export_decisions_json, export_analytics_report
from webhooks import WebhookDB, trigger_webhooks_for_decision

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
    import os
    ui_paths = ["/app/ui", "app/ui", os.path.join(os.getcwd(), "app", "ui")]
    ui_dir = None
    for path in ui_paths:
        if os.path.exists(path):
            ui_dir = path
            break
    if ui_dir:
        app.mount("/dashboard", StaticFiles(directory=ui_dir, html=True), name="dashboard")
        logger.info(f"Dashboard mounted at /dashboard from {ui_dir}")
    else:
        logger.warning("UI directory not found, skipping static file mount")
except Exception as e:
    logger.warning(f"UI directory not found, skipping static file mount: {e}")


@app.get("/dashboard")
async def dashboard_redirect():
    """Redirect /dashboard to /dashboard/ to ensure StaticFiles mount works."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard/")


@app.get("/")
async def root():
    """Serve marketing index page at root."""
    from fastapi.responses import FileResponse
    import os
    website_paths = ["/app/website", "website", os.path.join(os.getcwd(), "website")]
    for base_path in website_paths:
        index_path = os.path.join(base_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return {"name": "PatchPulse API", "version": "1.0.0"}


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


@app.post("/api/v1/auth/signup", response_model=User)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Signup endpoint - creates new user account."""
    from auth import hash_password
    
    # Trim and validate email
    email = user_data.email.strip().lower() if user_data.email else ""
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    
    # Check if user already exists
    existing_user = db.query(UserDB).filter(UserDB.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate password
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Create new user
    password_hash = hash_password(user_data.password)
    new_user = UserDB(
        email=email,
        password_hash=password_hash,
        full_name=user_data.full_name.strip() if user_data.full_name else None,
        company=user_data.company.strip() if user_data.company else None,
        plan="free"
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user signed up: {new_user.email}")
        
        return User.model_validate(new_user)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create account. Please try again.")


@app.post("/api/v1/auth/login")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login endpoint - authenticates users and returns JWT token."""
    from auth import verify_password, create_access_token
    
    # Find user
    user = db.query(UserDB).filter(UserDB.email == credentials.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "plan": user.plan}
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "company": user.company,
            "plan": user.plan
        }
    }


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
        
        # Trigger webhooks
        try:
            await trigger_webhooks_for_decision(
                db,
                decision.id,
                {
                    "id": decision.id,
                    "change_event_id": db_event.id,
                    "risk_score": policy_result["risk_score"],
                    "allowed": policy_result["allowed"],
                    "reasons": policy_result["reasons"]
                }
            )
        except Exception as e:
            logger.error(f"Webhook trigger failed: {str(e)}")
        
        # Trigger integrations (Teams, Email, PagerDuty)
        try:
            decision_data = {
                "decision_id": decision.id,
                "change_event_id": db_event.id,
                "risk_score": policy_result["risk_score"],
                "allowed": policy_result["allowed"],
                "reasons": policy_result["reasons"],
                "guardrails_triggered": guardrails_serialized,
                "mode": mode,
                "repo": db_event.repo,
                "pr_number": db_event.pr_number,
                "sha": db_event.sha
            }
            
            # Teams integration
            try:
                from integrations.teams.notifier import TeamsNotifier
                teams_notifier = TeamsNotifier()
                teams_notifier.send_decision_notification(decision_data)
            except Exception as e:
                logger.debug(f"Teams notification failed: {str(e)}")
            
            # Email integration
            try:
                from integrations.email.notifier import EmailNotifier
                email_notifier = EmailNotifier()
                email_notifier.send_decision_notification(decision_data)
            except Exception as e:
                logger.debug(f"Email notification failed: {str(e)}")
            
            # PagerDuty integration
            try:
                from integrations.pagerduty.notifier import PagerDutyNotifier
                pagerduty_notifier = PagerDutyNotifier()
                pagerduty_notifier.send_decision_notification(decision_data)
            except Exception as e:
                logger.debug(f"PagerDuty notification failed: {str(e)}")
        except Exception as e:
            logger.error(f"Integration notification failed: {str(e)}")
        
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


# Export endpoints
@app.get("/api/v1/export/decisions")
async def export_decisions_endpoint(
    format: str = "json",  # json or csv
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Export decisions in CSV or JSON format."""
    if not export_decisions_csv:
        raise HTTPException(status_code=501, detail="Export functionality not available")
    
    decisions = db.query(DecisionDB).order_by(DecisionDB.created_at.desc()).limit(limit).all()
    
    # Get change events
    change_event_ids = [d.change_event_id for d in decisions]
    change_events = {
        ce.id: ce for ce in db.query(ChangeEventDB).filter(ChangeEventDB.id.in_(change_event_ids)).all()
    }
    
    if format.lower() == "csv":
        return export_decisions_csv(decisions, change_events)
    else:
        return export_decisions_json(decisions, change_events)


@app.get("/api/v1/export/analytics")
async def export_analytics_endpoint(db: Session = Depends(get_db)):
    """Export comprehensive analytics report."""
    if not export_analytics_report:
        raise HTTPException(status_code=501, detail="Export functionality not available")
    return export_analytics_report(db)


# Webhook endpoints
@app.post("/api/v1/webhooks")
async def create_webhook(
    webhook_data: dict,
    db: Session = Depends(get_db)
):
    """Create a new webhook."""
    if not WebhookDB:
        raise HTTPException(status_code=501, detail="Webhooks not available")
    
    from uuid import uuid4
    
    webhook = WebhookDB(
        id=str(uuid4()),
        url=webhook_data.get("url"),
        events=webhook_data.get("events", ["decision_created"]),
        secret=webhook_data.get("secret"),
        headers=webhook_data.get("headers"),
        enabled=True
    )
    
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    
    logger.info(f"Webhook created: {webhook.id} -> {webhook.url}")
    
    return {
        "id": webhook.id,
        "url": webhook.url,
        "events": webhook.events,
        "enabled": webhook.enabled,
        "created_at": webhook.created_at.isoformat()
    }


@app.get("/api/v1/webhooks")
async def list_webhooks(db: Session = Depends(get_db)):
    """List all webhooks."""
    if not WebhookDB:
        raise HTTPException(status_code=501, detail="Webhooks not available")
    
    webhooks = db.query(WebhookDB).all()
    return [
        {
            "id": w.id,
            "url": w.url,
            "events": w.events,
            "enabled": w.enabled,
            "created_at": w.created_at.isoformat(),
            "last_triggered": w.last_triggered.isoformat() if w.last_triggered else None
        }
        for w in webhooks
    ]


# Approval workflow endpoints
@app.post("/api/v1/decisions/{decision_id}/approve")
async def approve_decision(
    decision_id: str,
    approval: dict,
    db: Session = Depends(get_db)
):
    """Approve a high-risk decision (manual override)."""
    decision = db.query(DecisionDB).filter(DecisionDB.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    decision.allowed = True
    decision.triggered_by = f"manual_approval:{approval.get('approver_email', 'unknown')}"
    
    if not decision.outputs:
        decision.outputs = {}
    decision.outputs["manual_approval"] = {
        "approved": True,
        "approver": approval.get("approver_email"),
        "comment": approval.get("comment"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    db.commit()
    
    logger.info(f"Decision {decision_id} manually approved")
    
    return {
        "decision_id": decision_id,
        "approved": True,
        "message": "Decision approved"
    }


@app.post("/api/v1/decisions/{decision_id}/reject")
async def reject_decision(
    decision_id: str,
    approval: dict,
    db: Session = Depends(get_db)
):
    """Reject a decision (manual override)."""
    decision = db.query(DecisionDB).filter(DecisionDB.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    decision.allowed = False
    decision.triggered_by = f"manual_rejection:{approval.get('approver_email', 'unknown')}"
    
    if not decision.outputs:
        decision.outputs = {}
    decision.outputs["manual_rejection"] = {
        "rejected": True,
        "rejector": approval.get("approver_email"),
        "comment": approval.get("comment"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    db.commit()
    
    logger.info(f"Decision {decision_id} manually rejected")
    
    return {
        "decision_id": decision_id,
        "rejected": True,
        "message": "Decision rejected"
    }


# Bulk operations
@app.post("/api/v1/decisions/bulk")
async def bulk_operation(
    operation: dict,
    db: Session = Depends(get_db)
):
    """Perform bulk operation on decisions."""
    decision_ids = operation.get("decision_ids", [])
    action = operation.get("action", "approve")
    comment = operation.get("comment")
    
    decisions = db.query(DecisionDB).filter(DecisionDB.id.in_(decision_ids)).all()
    
    if len(decisions) != len(decision_ids):
        raise HTTPException(status_code=400, detail="Some decision IDs not found")
    
    updated = 0
    for decision in decisions:
        if action == "approve":
            decision.allowed = True
            decision.triggered_by = "bulk_approval"
        elif action == "reject":
            decision.allowed = False
            decision.triggered_by = "bulk_rejection"
        elif action == "delete":
            db.delete(decision)
            continue
        
        if not decision.outputs:
            decision.outputs = {}
        decision.outputs[f"bulk_{action}"] = {
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat()
        }
        updated += 1
    
    db.commit()
    
    return {
        "action": action,
        "processed": len(decisions),
        "updated": updated if action != "delete" else 0,
        "deleted": len(decisions) - updated if action == "delete" else 0
    }


# Change comparison
@app.post("/api/v1/change-events/compare")
async def compare_changes(
    comparison: dict,
    db: Session = Depends(get_db)
):
    """Compare two change events."""
    event1_id = comparison.get("change_event_id_1")
    event2_id = comparison.get("change_event_id_2")
    
    event1 = db.query(ChangeEventDB).filter(ChangeEventDB.id == event1_id).first()
    event2 = db.query(ChangeEventDB).filter(ChangeEventDB.id == event2_id).first()
    
    if not event1 or not event2:
        raise HTTPException(status_code=404, detail="One or both change events not found")
    
    decision1 = db.query(DecisionDB).filter(DecisionDB.change_event_id == event1.id).first()
    decision2 = db.query(DecisionDB).filter(DecisionDB.change_event_id == event2.id).first()
    
    differences = []
    files1 = set([h.get('file', '') for h in (event1.diff_hunks or [])])
    files2 = set([h.get('file', '') for h in (event2.diff_hunks or [])])
    
    only_in_1 = files1 - files2
    only_in_2 = files2 - files1
    
    for file in only_in_1:
        differences.append({
            "type": "only_in_first",
            "file": file,
            "description": f"File {file} only appears in first change"
        })
    
    for file in only_in_2:
        differences.append({
            "type": "only_in_second",
            "file": file,
            "description": f"File {file} only appears in second change"
        })
    
    risk_comparison = {
        "change_1_risk": decision1.risk_score if decision1 else None,
        "change_2_risk": decision2.risk_score if decision2 else None,
        "risk_difference": (decision2.risk_score if decision2 else 0) - (decision1.risk_score if decision1 else 0)
    }
    
    recommendations = []
    if decision1 and decision2:
        if decision1.risk_score > decision2.risk_score:
            recommendations.append("First change has higher risk")
        elif decision2.risk_score > decision1.risk_score:
            recommendations.append("Second change has higher risk")
    
    return {
        "change_event_1": {
            "id": event1.id,
            "repo": event1.repo,
            "sha": event1.sha,
            "pr_number": event1.pr_number,
            "files": event1.files
        },
        "change_event_2": {
            "id": event2.id,
            "repo": event2.repo,
            "sha": event2.sha,
            "pr_number": event2.pr_number,
            "files": event2.files
        },
        "differences": differences,
        "risk_comparison": risk_comparison,
        "recommendations": recommendations
    }


# Integration management endpoints
@app.get("/api/v1/integrations")
async def list_integrations():
    """List all available integrations and their status."""
    from integration_manager import get_integration_config
    
    integrations = {}
    for integration_type in ["teams", "email", "pagerduty"]:
        config = get_integration_config(integration_type)
        integrations[integration_type] = {
            "enabled": config.get("enabled", False) if config else False,
            "configured": bool(config)
        }
    
    return integrations


@app.post("/api/v1/integrations/{integration_type}/test")
async def test_integration(integration_type: str):
    """Test an integration configuration."""
    from integration_manager import test_integration
    
    if integration_type not in ["teams", "email", "pagerduty"]:
        raise HTTPException(status_code=400, detail="Invalid integration type")
    
    result = test_integration(integration_type)
    return result


# Audit log endpoint
@app.get("/api/v1/audit")
async def get_audit_log(
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get comprehensive audit log of all decisions and actions."""
    query = db.query(DecisionDB)
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(DecisionDB.created_at >= start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(DecisionDB.created_at <= end)
        except:
            pass
    
    decisions = query.order_by(DecisionDB.created_at.desc()).limit(limit).all()
    
    audit_entries = []
    for decision in decisions:
        change_event = db.query(ChangeEventDB).filter(ChangeEventDB.id == decision.change_event_id).first()
        
        entry = {
            "timestamp": decision.created_at.isoformat(),
            "type": "decision",
            "decision_id": decision.id,
            "change_event_id": decision.change_event_id,
            "action": "allowed" if decision.allowed else "blocked",
            "risk_score": decision.risk_score,
            "triggered_by": decision.triggered_by,
            "mode": decision.mode,
            "change_event": {
                "repo": change_event.repo if change_event else None,
                "pr_number": change_event.pr_number if change_event else None,
                "sha": change_event.sha if change_event else None
            } if change_event else None
        }
        
        if decision.outputs:
            if "manual_approval" in decision.outputs:
                entry["manual_action"] = "approved"
                entry["approver"] = decision.outputs["manual_approval"].get("approver")
            elif "manual_rejection" in decision.outputs:
                entry["manual_action"] = "rejected"
                entry["rejector"] = decision.outputs["manual_rejection"].get("rejector")
        
        audit_entries.append(entry)
    
    return {
        "total": len(audit_entries),
        "entries": audit_entries
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/{path:path}")
async def serve_marketing(path: str):
    """Serve marketing static files."""
    from fastapi.responses import FileResponse
    import os
    
    # Don't serve API routes or system endpoints
    # Allow "docs/" for website documentation, but block "/docs" (API docs endpoint)
    # Note: dashboard is handled by the mount above, so it won't reach here
    if path.startswith("api/") or path in ["health", "metrics", "docs"]:
        raise HTTPException(status_code=404)
    
    # Try website directory first (in Docker it's /app/website)
    website_paths = ["/app/website", "website"]
    for base_path in website_paths:
        # Direct file path
        file_path = os.path.join(base_path, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Try as HTML file if no extension
        if not path.endswith((".html", ".css", ".js", ".png", ".jpg", ".svg", ".ico", ".json", ".woff", ".woff2", ".gif", ".webp")):
            html_path = os.path.join(base_path, f"{path}.html")
            if os.path.exists(html_path):
                return FileResponse(html_path)
        
        # Handle docs/ subdirectory
        if path.startswith("docs/"):
            docs_file = os.path.join(base_path, path)
            if os.path.exists(docs_file):
                return FileResponse(docs_file)
            # Try with .html extension
            docs_html = os.path.join(base_path, f"{path}.html")
            if os.path.exists(docs_html):
                return FileResponse(docs_html)
    
    # Default to index.html for directories
    for base_path in website_paths:
        index_path = os.path.join(base_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    
