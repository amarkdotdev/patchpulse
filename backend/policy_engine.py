"""Policy engine with guardrail registry."""

import re
from typing import List, Dict, Any, Optional
from models import ChangeEvent, ClusterSignal, GuardrailResult

# Critical namespaces that get risk modifiers
CRITICAL_NAMESPACES = ["kube-system", "production", "prod"]


class GuardrailRegistry:
    """Registry for guardrail functions."""
    
    def __init__(self):
        self.guardrails: List[callable] = []
    
    def register(self, func: callable):
        """Register a guardrail function."""
        self.guardrails.append(func)
        return func
    
    def evaluate_all(self, change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> List[GuardrailResult]:
        """Evaluate all registered guardrails."""
        results = []
        for guardrail in self.guardrails:
            try:
                result = guardrail(change_event, cluster_signals)
                if result:
                    results.append(result)
            except Exception as e:
                # Log error but don't fail entire evaluation
                print(f"Error in guardrail {guardrail.__name__}: {e}")
        return results


# Global registry
registry = GuardrailRegistry()


def calculate_risk_score(guardrail_results: List[GuardrailResult], change_event: ChangeEvent) -> int:
    """Calculate risk score from guardrail results."""
    base_score = sum(gr.severity for gr in guardrail_results)
    
    # Apply modifiers for critical namespaces
    modifier = 0
    for file in change_event.files:
        # Check if file mentions critical namespace
        for ns in CRITICAL_NAMESPACES:
            if ns in file.lower():
                modifier += 20
                break
    
    # Check diff hunks for critical keywords
    for hunk in change_event.diff_hunks:
        hunk_text = hunk.get("hunk", "").lower()
        if "kube-system" in hunk_text or "production" in hunk_text:
            modifier += 15
    
    final_score = min(100, base_score + modifier)
    return final_score


# Guardrail implementations

@registry.register
def check_no_resource_limits(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check if resource limits are removed."""
    for hunk in change_event.diff_hunks:
        hunk_text = hunk.get("hunk", "")
        file_path = hunk.get("file", "")
        
        # Check for removal of limits
        if "limits:" in hunk_text and "- limits:" in hunk_text:
            return GuardrailResult(
                id="no_resource_limits",
                severity=50,
                message="Resource limits removed or missing",
                evidence=[f"File: {file_path}"]
            )
        
        # Check for empty limits block
        if re.search(r'-\s*limits:\s*\n\s*$', hunk_text):
            return GuardrailResult(
                id="no_resource_limits",
                severity=50,
                message="Resource limits block is empty",
                evidence=[f"File: {file_path}"]
            )
    
    return None


@registry.register
def check_hpa_disabled(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check if HPA is disabled or removed."""
    for hunk in change_event.diff_hunks:
        hunk_text = hunk.get("hunk", "")
        file_path = hunk.get("file", "")
        
        # Check for HPA removal
        if "kind: HorizontalPodAutoscaler" in hunk_text and "- kind: HorizontalPodAutoscaler" in hunk_text:
            return GuardrailResult(
                id="hpa_disabled",
                severity=40,
                message="HorizontalPodAutoscaler removed",
                evidence=[f"File: {file_path}"]
            )
        
        # Check for HPA minReplicas set to 0 or removed
        if "minReplicas:" in hunk_text:
            if re.search(r'-\s*minReplicas:\s*0', hunk_text):
                return GuardrailResult(
                    id="hpa_disabled",
                    severity=40,
                    message="HPA minReplicas set to 0",
                    evidence=[f"File: {file_path}"]
                )
    
    return None


@registry.register
def check_high_cpu_usage(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check for high CPU usage in cluster signals."""
    for signal in cluster_signals:
        if signal.metric == "cpu_usage" and signal.value and signal.value > 80:
            return GuardrailResult(
                id="high_cpu_usage",
                severity=30,
                message=f"High CPU usage detected: {signal.value:.1f}%",
                evidence=[f"Namespace: {signal.namespace}, Service: {signal.name}"]
            )
    return None


@registry.register
def check_pod_restarts(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check for excessive pod restarts."""
    for signal in cluster_signals:
        if signal.metric == "restart_count" and signal.value and signal.value > 5:
            return GuardrailResult(
                id="excessive_restarts",
                severity=35,
                message=f"Excessive pod restarts: {signal.value}",
                evidence=[f"Namespace: {signal.namespace}, Pod: {signal.name}"]
            )
    return None


@registry.register
def check_critical_service_modification(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check if critical services are being modified."""
    critical_services = ["api-server", "etcd", "scheduler", "controller-manager"]
    
    for hunk in change_event.diff_hunks:
        hunk_text = hunk.get("hunk", "").lower()
        file_path = hunk.get("file", "")
        
        for service in critical_services:
            if service in hunk_text:
                return GuardrailResult(
                    id="critical_service_modification",
                    severity=60,
                    message=f"Modification to critical service: {service}",
                    evidence=[f"File: {file_path}"]
                )
    
    return None


@registry.register
def check_image_tag_latest(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check if image tag is 'latest'."""
    for hunk in change_event.diff_hunks:
        hunk_text = hunk.get("hunk", "")
        file_path = hunk.get("file", "")
        
        if re.search(r'image:\s*.*:latest', hunk_text):
            return GuardrailResult(
                id="image_tag_latest",
                severity=25,
                message="Image tag is 'latest' (not recommended for production)",
                evidence=[f"File: {file_path}"]
            )
    
    return None


def evaluate_policy(change_event: ChangeEvent, cluster_signals: List[ClusterSignal], mode: str = "advisory") -> Dict[str, Any]:
    """Evaluate policy and return decision."""
    guardrail_results = registry.evaluate_all(change_event, cluster_signals)
    risk_score = calculate_risk_score(guardrail_results, change_event)
    
    # Determine if change should be allowed
    # In advisory mode, always allow but log
    # In enforce mode, block if risk > 70
    allowed = True
    if mode == "enforce" and risk_score > 70:
        allowed = False
    
    reasons = [gr.message for gr in guardrail_results[:5]]  # Top 5 reasons
    
    evidence_refs = []
    for gr in guardrail_results:
        evidence_refs.extend(gr.evidence)
    
    return {
        "risk_score": risk_score,
        "reasons": reasons,
        "guardrails_triggered": guardrail_results,
        "mode": mode,
        "allowed": allowed,
        "evidence_refs": list(set(evidence_refs))  # Deduplicate
    }

