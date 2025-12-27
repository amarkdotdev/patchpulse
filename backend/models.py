"""Data models for PatchPulse backend."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

Base = declarative_base()


# SQLAlchemy Models
class ChangeEventDB(Base):
    """Change event from Git integration."""
    __tablename__ = "change_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    source = Column(String, nullable=False)  # github, gitlab
    repo = Column(String, nullable=False)
    sha = Column(String, nullable=False)
    pr_number = Column(Integer)
    branch = Column(String)
    files = Column(JSON)  # List of file paths
    diff_hunks = Column(JSON)  # List of {file, hunk} objects
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    decisions = relationship("DecisionDB", back_populates="change_event")


class ClusterSignalDB(Base):
    """Cluster signal from agent."""
    __tablename__ = "cluster_signals"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    kind = Column(String, nullable=False)  # deployment, pod, node, event
    namespace = Column(String)
    name = Column(String)
    metric = Column(String, nullable=False)  # cpu_usage, memory_usage, restart_count, etc.
    value = Column(Float)
    signal_metadata = Column("metadata", JSON)  # Additional context (renamed to avoid SQLAlchemy conflict)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DecisionDB(Base):
    """Risk decision for a change event."""
    __tablename__ = "decisions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    change_event_id = Column(String, ForeignKey("change_events.id"), nullable=False)
    risk_score = Column(Integer, nullable=False)  # 0-100
    reasons = Column(JSON)  # List of reason strings
    guardrails_triggered = Column(JSON)  # List of {id, severity, message, evidence}
    mode = Column(String, nullable=False)  # advisory, enforce
    allowed = Column(Boolean, nullable=False)
    evidence_refs = Column(JSON)  # List of evidence references
    policy_version = Column(String, default="1.0.0")
    triggered_by = Column(String)  # user, system, integration
    inputs = Column(JSON)  # Snapshot of inputs for audit
    outputs = Column(JSON)  # Snapshot of outputs for audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    change_event = relationship("ChangeEventDB", back_populates="decisions")


# Pydantic Models for API
class ChangeEvent(BaseModel):
    source: str
    repo: str
    sha: str
    pr_number: Optional[int] = None
    branch: Optional[str] = None
    files: List[str]
    diff_hunks: List[Dict[str, str]]
    timestamp: datetime

    class Config:
        from_attributes = True


class ClusterSignal(BaseModel):
    kind: str
    namespace: Optional[str] = None
    name: Optional[str] = None
    metric: str
    value: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class GuardrailResult(BaseModel):
    id: str
    severity: int  # 0-100
    message: str
    evidence: List[str] = []


class Decision(BaseModel):
    change_event_id: str
    risk_score: int  # 0-100
    reasons: List[str]
    guardrails_triggered: List[GuardrailResult]
    mode: str  # advisory, enforce
    allowed: bool
    evidence_refs: List[str]
    policy_version: str = "1.0.0"

    class Config:
        from_attributes = True


class DecisionResponse(BaseModel):
    id: str
    change_event_id: str
    risk_score: int
    reasons: List[str]
    guardrails_triggered: List[GuardrailResult]
    mode: str
    allowed: bool
    evidence_refs: List[str]
    policy_version: str
    created_at: datetime

