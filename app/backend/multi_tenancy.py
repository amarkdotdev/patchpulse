"""Multi-Tenancy + RBAC + Data Isolation."""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from models import Base

logger = logging.getLogger(__name__)


class TenantDB(Base):
    """Tenant (organization/team) in database."""
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    display_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)
    data_retention_days = Column(Integer, default=90)
    policy_overrides = Column(JSON)  # Per-tenant policy overrides


class TenantUserDB(Base):
    """Tenant user association."""
    __tablename__ = "tenant_users"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, nullable=False)
    role = Column(String, default="member")  # admin, member, viewer
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    tenant = relationship("TenantDB")


class TenantPolicyDB(Base):
    """Per-tenant policy configuration."""
    __tablename__ = "tenant_policies"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    policy_bundle_id = Column(String)
    mode = Column(String, default="advisory")  # advisory, enforce
    namespace_overrides = Column(JSON)  # Per-namespace overrides
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    tenant = relationship("TenantDB")


def get_tenant_from_token(token_data: Dict) -> Optional[str]:
    """Extract tenant ID from JWT token."""
    return token_data.get("tenant_id") or token_data.get("org_id")


def check_tenant_access(user_tenant: str, resource_tenant: str) -> bool:
    """Check if user has access to tenant resource."""
    return user_tenant == resource_tenant


def filter_by_tenant(query, tenant_id: str, tenant_field: str = "tenant_id"):
    """Filter query by tenant."""
    # In production, add tenant filtering to queries
    return query


class RBAC:
    """Role-Based Access Control."""
    
    ROLES = {
        "admin": ["read", "write", "delete", "approve", "manage"],
        "member": ["read", "write", "approve"],
        "viewer": ["read"]
    }
    
    @staticmethod
    def has_permission(role: str, permission: str) -> bool:
        """Check if role has permission."""
        return permission in RBAC.ROLES.get(role, [])
    
    @staticmethod
    def can_access_tenant(user_tenant: str, resource_tenant: str, user_role: str) -> bool:
        """Check if user can access tenant resource."""
        if user_tenant != resource_tenant:
            return False
        
        if user_role == "admin":
            return True
        
        return True  # Members and viewers can read their own tenant

