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


# Blog Post Models
class BlogPostDB(Base):
    """Blog post in database."""
    __tablename__ = "blog_posts"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)  # HTML content from rich text editor
    excerpt = Column(Text)  # Short summary
    author = Column(String, default="PatchPulse Team")
    featured_image = Column(String)  # URL to featured image
    status = Column(String, default="published")  # draft, published, archived
    tags = Column(JSON)  # List of tags
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime)  # When it was published


class BlogPost(BaseModel):
    """Pydantic model for blog post."""
    id: Optional[str] = None
    title: str
    slug: Optional[str] = None
    content: str  # HTML content
    excerpt: Optional[str] = None
    author: str = "PatchPulse Team"
    featured_image: Optional[str] = None
    status: str = "published"  # draft, published, archived
    tags: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlogPostCreate(BaseModel):
    """Model for creating a blog post."""
    title: str
    slug: Optional[str] = None
    content: str
    excerpt: Optional[str] = None
    author: str = "PatchPulse Team"
    featured_image: Optional[str] = None
    status: str = "published"
    tags: Optional[List[str]] = None


class BlogPostUpdate(BaseModel):
    """Model for updating a blog post."""
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    author: Optional[str] = None
    featured_image: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


# User Models
class UserDB(Base):
    """User in database."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)  # Hashed password
    full_name = Column(String)
    company = Column(String)
    plan = Column(String, default="free")  # free, professional, enterprise
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)


class User(BaseModel):
    """Pydantic model for user."""
    id: Optional[str] = None
    email: str
    full_name: Optional[str] = None
    company: Optional[str] = None
    plan: str = "free"
    created_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class UserSignup(BaseModel):
    """Model for user signup."""
    email: str
    password: str
    full_name: Optional[str] = None
    company: Optional[str] = None


class UserLogin(BaseModel):
    """Model for user login."""
    email: str
    password: str


# Webhook Models
class WebhookCreate(BaseModel):
    """Model for creating a webhook."""
    url: str
    events: Optional[List[str]] = None  # decision_created, decision_blocked, high_risk, etc.
    secret: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class WebhookUpdate(BaseModel):
    """Model for updating a webhook."""
    url: Optional[str] = None
    events: Optional[List[str]] = None
    secret: Optional[str] = None
    enabled: Optional[bool] = None
    headers: Optional[Dict[str, str]] = None


class Webhook(BaseModel):
    """Pydantic model for webhook."""
    id: str
    url: str
    events: Optional[List[str]] = None
    enabled: bool = True
    created_at: datetime
    last_triggered: Optional[datetime] = None
    failure_count: int = 0

    class Config:
        from_attributes = True


# Approval Models
class ApprovalRequest(BaseModel):
    """Model for approval request."""
    decision_id: str
    approver_email: Optional[str] = None
    comment: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Model for approval response."""
    decision_id: str
    approved: bool
    approver_email: Optional[str] = None
    comment: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# Bulk Operation Models
class BulkOperationRequest(BaseModel):
    """Model for bulk operation."""
    decision_ids: List[str]
    action: str  # approve, reject, or delete
    comment: Optional[str] = None


# Change Comparison Models
class ChangeComparisonRequest(BaseModel):
    """Model for comparing two changes."""
    change_event_id_1: str
    change_event_id_2: str


class ChangeComparison(BaseModel):
    """Model for change comparison result."""
    change_event_1: Dict
    change_event_2: Dict
    differences: List[Dict]
    risk_comparison: Dict
    recommendations: List[str]

    class Config:
        from_attributes = True


# Evidence Pack Models
class EvidencePack(BaseModel):
    """Model for evidence pack."""
    decision_id: str
    timestamp: datetime
    change_event: Dict
    risk_analysis: Dict
    guardrails: List[Dict]
    matched_hunks: List[Dict]
    signal_queries: List[Dict]
    signal_results_digest: str
    evidence_hash: str

    class Config:
        from_attributes = True


# Policy Bundle Models
class PolicyBundleCreate(BaseModel):
    """Model for creating policy bundle."""
    name: str
    version: str
    policies: List[Dict]
    signature: Optional[str] = None
    active: bool = False


class PolicyBundle(BaseModel):
    """Model for policy bundle."""
    id: str
    name: str
    version: str
    bundle_hash: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Tenant Models
class TenantCreate(BaseModel):
    """Model for creating tenant."""
    name: str
    display_name: Optional[str] = None
    data_retention_days: int = 90
    policy_overrides: Optional[Dict] = None


class Tenant(BaseModel):
    """Model for tenant."""
    id: str
    name: str
    display_name: Optional[str] = None
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True

