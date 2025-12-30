"""Policy-as-Code Engine v2 with versioned bundles."""

import os
import json
import hashlib
import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean
from models import Base

logger = logging.getLogger(__name__)


class PolicyBundleDB(Base):
    """Policy bundle in database."""
    __tablename__ = "policy_bundles"
    
    id = Column(String, primary_key=True)
    version = Column(String, nullable=False)
    name = Column(String, nullable=False)
    bundle_hash = Column(String, nullable=False)  # SHA256 of bundle content
    signature = Column(Text)  # Optional signature
    content = Column(JSON, nullable=False)  # Policy bundle content
    active = Column(Boolean, default=False)
    namespace_override = Column(JSON)  # Per-namespace overrides
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String)


class PolicyBundle:
    """Policy bundle with versioning."""
    
    def __init__(self, name: str, version: str, policies: List[Dict], signature: Optional[str] = None):
        self.name = name
        self.version = version
        self.policies = policies
        self.signature = signature
        self.bundle_hash = self._calculate_hash()
        self.created_at = datetime.utcnow()
    
    def _calculate_hash(self) -> str:
        """Calculate SHA256 hash of bundle content."""
        content = json.dumps({
            "name": self.name,
            "version": self.version,
            "policies": self.policies
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify_signature(self) -> bool:
        """Verify bundle signature (placeholder for actual verification)."""
        if not self.signature:
            return True  # No signature means unsigned (allowed in some modes)
        # In production, verify against public key
        return True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "bundle_hash": self.bundle_hash,
            "signature": self.signature,
            "policies": self.policies,
            "created_at": self.created_at.isoformat()
        }


def create_policy_bundle(name: str, version: str, policies: List[Dict], signature: Optional[str] = None) -> PolicyBundle:
    """Create a new policy bundle."""
    bundle = PolicyBundle(name, version, policies, signature)
    
    if not bundle.verify_signature():
        raise ValueError("Invalid bundle signature")
    
    return bundle


def get_active_bundle(namespace: Optional[str] = None) -> Optional[PolicyBundle]:
    """Get active policy bundle for namespace."""
    # In production, query database
    # For now, return default bundle
    return PolicyBundle(
        name="default",
        version="1.0.0",
        policies=[
            {"id": "no_resource_limits", "enabled": True},
            {"id": "image_tag_latest", "enabled": True},
            {"id": "privileged_security_context", "enabled": True}
        ]
    )

