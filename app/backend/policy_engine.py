"""Policy engine with guardrail registry."""

import re
import logging
from typing import List, Dict, Any, Optional
from models import ChangeEvent, ClusterSignal, GuardrailResult

logger = logging.getLogger(__name__)

# Try to import AI analyzer (optional)
try:
    from ai_analyzer import analyze_change_with_ai, explain_guardrail_with_ai
    AI_AVAILABLE = True
except ImportError:
    logger.warning("AI analyzer not available, running in rule-based mode only")
    AI_AVAILABLE = False

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
                logger.error(f"Error in guardrail {guardrail.__name__}: {e}")
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


@registry.register
def check_security_context_privileged(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check for privileged security context."""
    for hunk in change_event.diff_hunks:
        hunk_text = hunk.get("hunk", "")
        file_path = hunk.get("file", "")
        
        if re.search(r'privileged:\s*true', hunk_text, re.IGNORECASE):
            return GuardrailResult(
                id="privileged_security_context",
                severity=70,
                message="Container running with privileged security context",
                evidence=[f"File: {file_path}"]
            )
    
    return None


@registry.register
def check_host_network(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check for hostNetwork usage."""
    for hunk in change_event.diff_hunks:
        hunk_text = hunk.get("hunk", "")
        file_path = hunk.get("file", "")
        
        if re.search(r'hostNetwork:\s*true', hunk_text, re.IGNORECASE):
            return GuardrailResult(
                id="host_network",
                severity=60,
                message="Pod using hostNetwork (security risk)",
                evidence=[f"File: {file_path}"]
            )
    
    return None


@registry.register
def check_missing_readiness_probe(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check for missing readiness probe."""
    for hunk in change_event.diff_hunks:
        hunk_text = hunk.get("hunk", "")
        file_path = hunk.get("file", "")
        
        # Check if readinessProbe is removed
        if re.search(r'-\s*readinessProbe:', hunk_text):
            return GuardrailResult(
                id="missing_readiness_probe",
                severity=30,
                message="Readiness probe removed or missing",
                evidence=[f"File: {file_path}"]
            )
    
    return None


@registry.register
def check_low_replica_count(change_event: ChangeEvent, cluster_signals: List[ClusterSignal]) -> Optional[GuardrailResult]:
    """Check for low replica count in production."""
    for hunk in change_event.diff_hunks:
        hunk_text = hunk.get("hunk", "")
        file_path = hunk.get("file", "")
        
        # Check for replicas: 1 in production namespace
        if "production" in file_path.lower() or "prod" in file_path.lower():
            if re.search(r'replicas:\s*1\b', hunk_text):
                return GuardrailResult(
                    id="low_replica_count",
                    severity=40,
                    message="Single replica in production namespace (no redundancy)",
                    evidence=[f"File: {file_path}"]
                )
    
    return None


def evaluate_policy(change_event: ChangeEvent, cluster_signals: List[ClusterSignal], mode: str = "advisory") -> Dict[str, Any]:
    """Evaluate policy with AI analysis and return decision."""
    guardrail_results = registry.evaluate_all(change_event, cluster_signals)
    rule_based_score = calculate_risk_score(guardrail_results, change_event)
    
    # Get AI analysis if available
    ai_result = None
    if AI_AVAILABLE:
        try:
            cluster_signals_dict = [
                {
                    "kind": s.kind,
                    "name": s.name,
                    "metric": s.metric,
                    "value": s.value,
                    "signal_metadata": getattr(s, 'signal_metadata', getattr(s, 'metadata', {}))
                }
                for s in cluster_signals
            ]
            
            ai_result = analyze_change_with_ai(
                diff_hunks=change_event.diff_hunks,
                files=change_event.files,
                cluster_signals=cluster_signals_dict,
                repo=change_event.repo,
                branch=change_event.branch or "unknown"
            )
            
            # Enhance guardrail messages with AI explanations
            if ai_result and ai_result.get("confidence", 0) > 0.5:
                diff_context = "\n".join([
                    f"File: {h.get('file', '')}\n{h.get('hunk', '')}"
                    for h in change_event.diff_hunks[:3]
                ])
                
                for gr in guardrail_results:
                    if gr.evidence:
                        try:
                            enhanced = explain_guardrail_with_ai(
                                guardrail_id=gr.id,
                                guardrail_message=gr.message,
                                evidence=gr.evidence,
                                diff_context=diff_context
                            )
                            gr.message = enhanced
                        except Exception as e:
                            logger.warning(f"Failed to enhance guardrail {gr.id} with AI: {e}")
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}", exc_info=True)
    
    # Combine rule-based and AI scores
    if ai_result and ai_result.get("confidence", 0) > 0.3:
        ai_score = ai_result.get("risk_score", 0)
        confidence = ai_result.get("confidence", 0)
        # Weighted combination: 60% rule-based, 40% AI (if AI confidence is high)
        risk_score = int(rule_based_score * 0.6 + ai_score * 0.4 * confidence)
        # If AI finds issues not caught by rules, increase score
        if ai_score > rule_based_score + 10:
            risk_score = max(risk_score, ai_score - 5)
    else:
        risk_score = rule_based_score
    
    # Determine if change should be allowed
    # In advisory mode, always allow but log
    # In enforce mode, block if risk > 70
    allowed = True
    if mode == "enforce" and risk_score > 70:
        allowed = False
    
    # Build reasons list (combine guardrails and AI insights)
    reasons = [gr.message for gr in guardrail_results[:3]]  # Top 3 guardrails
    
    if ai_result and ai_result.get("potential_issues"):
        # Add top AI-identified issues
        for issue in ai_result["potential_issues"][:2]:
            if issue not in reasons:
                reasons.append(f"AI: {issue}")
    
    if not reasons:
        reasons = ["No issues detected"]
    
    evidence_refs = []
    for gr in guardrail_results:
        evidence_refs.extend(gr.evidence)
    
    result = {
        "risk_score": risk_score,
        "reasons": reasons,
        "guardrails_triggered": guardrail_results,
        "mode": mode,
        "allowed": allowed,
        "evidence_refs": list(set(evidence_refs))  # Deduplicate
    }
    
    # Add AI analysis if available
    if ai_result:
        result["ai_analysis"] = {
            "risk_score": ai_result.get("risk_score", 0),
            "analysis": ai_result.get("ai_analysis", ""),
            "recommendations": ai_result.get("recommendations", []),
            "potential_issues": ai_result.get("potential_issues", []),
            "confidence": ai_result.get("confidence", 0.0)
        }
    
    return result

