"""Kubernetes Admission Webhook for PatchPulse."""

import os
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import yaml

logger = logging.getLogger(__name__)

# Admission webhook server
webhook_app = FastAPI(title="PatchPulse Admission Webhook")


def analyze_resource(resource: Dict, mode: str = "advisory") -> Dict:
    """Analyze a Kubernetes resource and return admission decision."""
    from policy_engine import evaluate_policy
    from models import ChangeEvent
    
    # Extract resource metadata
    kind = resource.get("kind", "")
    metadata = resource.get("metadata", {})
    name = metadata.get("name", "unknown")
    namespace = metadata.get("namespace", "default")
    
    # Convert resource to change event format
    resource_yaml = yaml.dump(resource)
    
    # Create diff hunk (simulating a new resource)
    diff_hunk = f"+ {resource_yaml}"
    
    change_event = ChangeEvent(
        source="admission_webhook",
        repo=f"{namespace}/{kind}",
        sha=hashlib.sha256(resource_yaml.encode()).hexdigest()[:8],
        branch=namespace,
        pr_number=None,
        files=[f"{kind.lower()}-{name}.yaml"],
        diff_hunks=[{"file": f"{kind.lower()}-{name}.yaml", "hunk": diff_hunk}],
        timestamp=datetime.utcnow()
    )
    
    # Evaluate policy
    policy_result = evaluate_policy(change_event, [], mode)
    
    return {
        "allowed": policy_result["allowed"],
        "risk_score": policy_result["risk_score"],
        "reasons": policy_result["reasons"],
        "guardrails_triggered": [
            {
                "id": gr.get("id", "unknown"),
                "severity": gr.get("severity", 0),
                "message": gr.get("message", "")
            }
            for gr in policy_result.get("guardrails_triggered", [])
        ]
    }


@webhook_app.post("/validate")
async def validate_admission(request: Request):
    """Validating admission webhook endpoint."""
    try:
        body = await request.json()
        admission_review = body
        
        # Extract the resource
        request_obj = admission_review.get("request", {})
        resource = request_obj.get("object", {})
        
        # Get mode from environment or annotation
        mode = os.getenv("ADMISSION_MODE", "advisory")
        annotations = resource.get("metadata", {}).get("annotations", {})
        if "patchpulse.io/mode" in annotations:
            mode = annotations["patchpulse.io/mode"]
        
        # Analyze resource
        analysis = analyze_resource(resource, mode)
        
        # Create response
        uid = request_obj.get("uid", "")
        
        if mode == "enforce" and not analysis["allowed"]:
            # Reject in enforce mode
            message = f"PatchPulse blocked this resource. Risk score: {analysis['risk_score']}/100. Reasons: {', '.join(analysis['reasons'][:3])}"
            
            return {
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "response": {
                    "uid": uid,
                    "allowed": False,
                    "status": {
                        "code": 403,
                        "message": message,
                        "reason": "PatchPulseRiskAnalysis"
                    }
                }
            }
        else:
            # Allow but annotate in advisory mode
            patches = []
            if "metadata" in resource and "annotations" in resource.get("metadata", {}):
                patches.append({
                    "op": "add",
                    "path": "/metadata/annotations/patchpulse.io~1risk-score",
                    "value": str(analysis["risk_score"])
                })
                patches.append({
                    "op": "add",
                    "path": "/metadata/annotations/patchpulse.io~1decision-id",
                    "value": hashlib.sha256(json.dumps(resource).encode()).hexdigest()[:16]
                })
            
            return {
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "response": {
                    "uid": uid,
                    "allowed": True,
                    "patchType": "JSONPatch",
                    "patch": json.dumps(patches).encode().decode("unicode_escape")
                }
            }
            
    except Exception as e:
        logger.error(f"Admission webhook error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@webhook_app.post("/mutate")
async def mutate_admission(request: Request):
    """Mutating admission webhook endpoint."""
    try:
        body = await request.json()
        admission_review = body
        
        request_obj = admission_review.get("request", {})
        resource = request_obj.get("object", {})
        
        # Analyze resource
        analysis = analyze_resource(resource, "advisory")
        
        # Add annotations
        uid = request_obj.get("uid", "")
        patches = []
        
        if "metadata" not in resource:
            patches.append({"op": "add", "path": "/metadata", "value": {}})
        
        if "annotations" not in resource.get("metadata", {}):
            patches.append({"op": "add", "path": "/metadata/annotations", "value": {}})
        
        patches.append({
            "op": "add",
            "path": "/metadata/annotations/patchpulse.io~1risk-score",
            "value": str(analysis["risk_score"])
        })
        patches.append({
            "op": "add",
            "path": "/metadata/annotations/patchpulse.io~1analyzed-at",
            "value": datetime.utcnow().isoformat()
        })
        
        return {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": uid,
                "allowed": True,
                "patchType": "JSONPatch",
                "patch": json.dumps(patches).encode().decode("unicode_escape")
            }
        }
        
    except Exception as e:
        logger.error(f"Mutation webhook error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



