"""Policy templates for common use cases."""

from typing import Dict, List, Optional
from datetime import datetime


class PolicyTemplate:
    """Policy template definition."""
    
    def __init__(self, id: str, name: str, description: str, guardrails: List[str], mode: str = "advisory"):
        self.id = id
        self.name = name
        self.description = description
        self.guardrails = guardrails
        self.mode = mode
        self.created_at = datetime.utcnow()


# Pre-defined policy templates
POLICY_TEMPLATES = {
    "strict": PolicyTemplate(
        id="strict",
        name="Strict Security Policy",
        description="Maximum security with all guardrails enabled in enforce mode",
        guardrails=[
            "no_resource_limits",
            "privileged_security_context",
            "image_tag_latest",
            "missing_readiness_probe",
            "host_network",
            "run_as_root"
        ],
        mode="enforce"
    ),
    "balanced": PolicyTemplate(
        id="balanced",
        name="Balanced Policy",
        description="Recommended policy for most production environments",
        guardrails=[
            "no_resource_limits",
            "image_tag_latest",
            "privileged_security_context"
        ],
        mode="advisory"
    ),
    "permissive": PolicyTemplate(
        id="permissive",
        name="Permissive Policy",
        description="Minimal guardrails for development environments",
        guardrails=[
            "no_resource_limits"
        ],
        mode="advisory"
    ),
    "compliance": PolicyTemplate(
        id="compliance",
        name="Compliance Policy",
        description="Policy focused on compliance requirements",
        guardrails=[
            "no_resource_limits",
            "privileged_security_context",
            "run_as_root",
            "missing_readiness_probe",
            "hpa_disabled"
        ],
        mode="enforce"
    )
}


def get_policy_template(template_id: str) -> Optional[PolicyTemplate]:
    """Get a policy template by ID."""
    return POLICY_TEMPLATES.get(template_id)


def list_policy_templates() -> List[Dict]:
    """List all available policy templates."""
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "guardrails": t.guardrails,
            "mode": t.mode
        }
        for t in POLICY_TEMPLATES.values()
    ]



