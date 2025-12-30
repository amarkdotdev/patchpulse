"""Risk Explanation Evidence Pack generator."""

import json
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from models import ChangeEvent, ClusterSignal


class EvidencePack:
    """Evidence pack for risk decisions."""
    
    def __init__(
        self,
        decision_id: str,
        change_event: ChangeEvent,
        risk_score: int,
        guardrails_triggered: List[Dict],
        cluster_signals: List[ClusterSignal],
        previous_score: Optional[int] = None
    ):
        self.decision_id = decision_id
        self.change_event = change_event
        self.risk_score = risk_score
        self.guardrails_triggered = guardrails_triggered
        self.cluster_signals = cluster_signals
        self.previous_score = previous_score
        self.timestamp = datetime.utcnow()
        self.evidence_hash = None
    
    def generate(self) -> Dict:
        """Generate complete evidence pack."""
        # Map guardrails to diff hunks
        matched_hunks = []
        for gr in self.guardrails_triggered:
            gr_id = gr.get("id", "unknown")
            # Find which diff hunks triggered this guardrail
            for hunk in self.change_event.diff_hunks:
                hunk_content = hunk.get("hunk", "")
                if self._hunk_matches_guardrail(hunk_content, gr_id):
                    matched_hunks.append({
                        "guardrail_id": gr_id,
                        "file": hunk.get("file", "unknown"),
                        "hunk_id": hashlib.sha256(hunk_content.encode()).hexdigest()[:16],
                        "matched_lines": self._extract_matched_lines(hunk_content, gr_id)
                    })
        
        # Calculate score delta
        score_delta = None
        score_explanation = []
        if self.previous_score is not None:
            score_delta = self.risk_score - self.previous_score
            if score_delta > 0:
                score_explanation.append(f"Risk increased by {score_delta} points")
                for gr in self.guardrails_triggered:
                    score_explanation.append(f"{gr.get('message', '')}: +{gr.get('severity', 0)}")
        
        # Signal queries and results
        signal_queries = []
        signal_results = []
        for signal in self.cluster_signals:
            signal_queries.append({
                "kind": signal.kind,
                "namespace": signal.namespace,
                "metric": signal.metric,
                "query_time": signal.timestamp.isoformat()
            })
            signal_results.append({
                "metric": signal.metric,
                "value": signal.value,
                "timestamp": signal.timestamp.isoformat()
            })
        
        evidence_pack = {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp.isoformat(),
            "change_event": {
                "id": self.change_event.id if hasattr(self.change_event, 'id') else None,
                "repo": self.change_event.repo,
                "sha": self.change_event.sha,
                "pr_number": self.change_event.pr_number,
                "files": self.change_event.files
            },
            "risk_analysis": {
                "risk_score": self.risk_score,
                "previous_score": self.previous_score,
                "score_delta": score_delta,
                "score_explanation": score_explanation,
                "allowed": True  # Will be set by decision
            },
            "guardrails": [
                {
                    "rule_id": gr.get("id", "unknown"),
                    "severity": gr.get("severity", 0),
                    "message": gr.get("message", ""),
                    "evidence": gr.get("evidence", []),
                    "matched_hunk_ids": [
                        mh["hunk_id"] for mh in matched_hunks
                        if mh["guardrail_id"] == gr.get("id")
                    ]
                }
                for gr in self.guardrails_triggered
            ],
            "matched_hunks": matched_hunks,
            "signal_queries": signal_queries,
            "signal_results_digest": hashlib.sha256(
                json.dumps(signal_results, sort_keys=True).encode()
            ).hexdigest(),
            "signal_results": signal_results,
            "evidence_hash": None  # Will be calculated
        }
        
        # Calculate evidence hash
        evidence_pack["evidence_hash"] = hashlib.sha256(
            json.dumps(evidence_pack, sort_keys=True).encode()
        ).hexdigest()
        
        return evidence_pack
    
    def _hunk_matches_guardrail(self, hunk_content: str, guardrail_id: str) -> bool:
        """Check if hunk content matches guardrail pattern."""
        # Simple pattern matching (in production, use more sophisticated matching)
        patterns = {
            "image_tag_latest": ["latest", ":latest"],
            "no_resource_limits": ["resources:", "limits:"],
            "privileged_security_context": ["privileged:", "privileged: true"],
            "host_network": ["hostNetwork:", "hostNetwork: true"],
            "run_as_root": ["runAsUser: 0", "runAsUser:0"]
        }
        
        pattern = patterns.get(guardrail_id, [])
        if not pattern:
            return False
        
        hunk_lower = hunk_content.lower()
        return any(p.lower() in hunk_lower for p in pattern)
    
    def _extract_matched_lines(self, hunk_content: str, guardrail_id: str) -> List[str]:
        """Extract lines that matched the guardrail."""
        lines = hunk_content.split("\n")
        matched = []
        
        patterns = {
            "image_tag_latest": ["latest"],
            "no_resource_limits": ["resources", "limits"],
            "privileged_security_context": ["privileged"],
            "host_network": ["hostNetwork"],
            "run_as_root": ["runAsUser"]
        }
        
        search_terms = patterns.get(guardrail_id, [])
        for i, line in enumerate(lines):
            if any(term.lower() in line.lower() for term in search_terms):
                matched.append(f"Line {i+1}: {line.strip()}")
        
        return matched


def generate_evidence_pack(
    decision_id: str,
    change_event: ChangeEvent,
    risk_score: int,
    guardrails_triggered: List[Dict],
    cluster_signals: List[ClusterSignal],
    previous_score: Optional[int] = None
) -> Dict:
    """Generate evidence pack for a decision."""
    pack = EvidencePack(
        decision_id=decision_id,
        change_event=change_event,
        risk_score=risk_score,
        guardrails_triggered=guardrails_triggered,
        cluster_signals=cluster_signals,
        previous_score=previous_score
    )
    return pack.generate()

