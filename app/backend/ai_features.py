"""Advanced AI-powered features for PatchPulse."""

import os
import json
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Get client and API function from ai_analyzer (reuse existing secure client)
try:
    from ai_analyzer import client, _call_ai_api, client_type
    ai_client = client
    AI_AVAILABLE = ai_client is not None
except (ImportError, AttributeError):
    AI_AVAILABLE = False
    ai_client = None
    _call_ai_api = None
    client_type = None
    logger.warning("AI client not available for advanced features")


def get_security_vulnerabilities(
    diff_hunks: List[Dict],
    files: List[str],
    cluster_signals: List[Dict]
) -> Dict:
    """
    AI-powered security vulnerability scanning.
    
    Returns:
        {
            "vulnerabilities": List[Dict],
            "severity": str,
            "recommendations": List[str]
        }
    """
    if not AI_AVAILABLE:
        return {"vulnerabilities": [], "severity": "none", "recommendations": []}
    
    try:
        diff_text = "\n\n".join([
            f"File: {hunk.get('file', 'unknown')}\n{hunk.get('hunk', '')}"
            for hunk in diff_hunks
        ])
        
        prompt = f"""Analyze this Kubernetes configuration for security vulnerabilities.

DIFF:
{diff_text}

Look for:
- Privilege escalation risks
- Network exposure issues
- Secret management problems
- RBAC misconfigurations
- Container security issues
- Image vulnerabilities
- Resource exhaustion risks

Respond in JSON:
{{
    "vulnerabilities": [
        {{
            "type": "<vulnerability type>",
            "severity": "<critical|high|medium|low>",
            "description": "<description>",
            "location": "<file:line>",
            "cve": "<CVE if applicable>"
        }}
    ],
    "severity": "<overall severity>",
    "recommendations": ["<rec1>", "<rec2>"]
}}"""

        content = _call_ai_api(
            messages=[
                {
                    "role": "system",
                    "content": "You are a Kubernetes security expert. Analyze configurations for vulnerabilities."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        
        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        return result
        
    except Exception as e:
        logger.error(f"Security scan failed: {str(e)}")
        return {"vulnerabilities": [], "severity": "unknown", "recommendations": []}


def get_change_recommendations(
    diff_hunks: List[Dict],
    files: List[str],
    risk_score: int,
    guardrails_triggered: List[Dict]
) -> Dict:
    """
    AI-powered recommendations to improve the change.
    
    Returns:
        {
            "recommendations": List[Dict],
            "priority": List[str]
        }
    """
    if not AI_AVAILABLE:
        return {"recommendations": [], "priority": []}
    
    try:
        diff_text = "\n\n".join([
            f"File: {hunk.get('file', 'unknown')}\n{hunk.get('hunk', '')}"
            for hunk in diff_hunks[:5]  # Limit to 5 files
        ])
        
        guardrail_summary = ", ".join([gr.get("id", "unknown") for gr in guardrails_triggered[:5]])
        
        prompt = f"""Analyze this Kubernetes change and provide specific, actionable recommendations to improve it.

Current Risk Score: {risk_score}/100
Triggered Guardrails: {guardrail_summary}

DIFF:
{diff_text}

Provide concrete recommendations to:
- Reduce risk score
- Fix guardrail violations
- Improve security
- Enhance reliability
- Follow best practices

Respond in JSON:
{{
    "recommendations": [
        {{
            "priority": "<high|medium|low>",
            "category": "<security|reliability|performance|best-practice>",
            "title": "<short title>",
            "description": "<detailed description>",
            "code_example": "<optional code snippet>"
        }}
    ],
    "priority": ["<top 3 priority actions>"]
}}"""

        content = _call_ai_api(
            messages=[
                {
                    "role": "system",
                    "content": "You are a Kubernetes SRE expert. Provide actionable recommendations."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        return result
        
    except Exception as e:
        logger.error(f"Recommendations failed: {str(e)}")
        return {"recommendations": [], "priority": []}


def predict_incident_risk(
    change_event: Dict,
    cluster_signals: List[Dict],
    historical_decisions: List[Dict]
) -> Dict:
    """
    AI-powered incident prediction based on patterns.
    
    Returns:
        {
            "incident_probability": float (0-1),
            "predicted_issues": List[str],
            "confidence": float (0-1),
            "time_to_incident": str
        }
    """
    if not AI_AVAILABLE:
        return {
            "incident_probability": 0.0,
            "predicted_issues": [],
            "confidence": 0.0,
            "time_to_incident": "unknown"
        }
    
    try:
        # Build context
        recent_high_risk = [d for d in historical_decisions if d.get("risk_score", 0) >= 70][:5]
        cluster_issues = [s for s in cluster_signals if s.get("value", 0) > 80][:5]
        
        prompt = f"""Predict the likelihood of a production incident based on this change and cluster state.

CHANGE:
- Files: {', '.join(change_event.get('files', []))}
- Risk Score: {change_event.get('risk_score', 0)}/100

CLUSTER STATE:
{json.dumps(cluster_issues, indent=2) if cluster_issues else "No critical signals"}

RECENT HIGH-RISK DECISIONS:
{len(recent_high_risk)} high-risk changes in recent history

Analyze patterns and predict:
1. Probability of incident (0-1)
2. What type of issues might occur
3. When they might occur
4. Confidence in prediction

Respond in JSON:
{{
    "incident_probability": <0.0-1.0>,
    "predicted_issues": ["<issue1>", "<issue2>"],
    "confidence": <0.0-1.0>,
    "time_to_incident": "<immediate|hours|days|weeks>",
    "reasoning": "<brief explanation>"
}}"""

        content = _call_ai_api(
            messages=[
                {
                    "role": "system",
                    "content": "You are an incident prediction expert. Analyze patterns to predict incidents."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1500
        )
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        return result
        
    except Exception as e:
        logger.error(f"Incident prediction failed: {str(e)}")
        return {
            "incident_probability": 0.0,
            "predicted_issues": [],
            "confidence": 0.0,
            "time_to_incident": "unknown"
        }


def get_cost_optimization_suggestions(
    diff_hunks: List[Dict],
    cluster_signals: List[Dict]
) -> Dict:
    """
    AI-powered cost optimization suggestions.
    
    Returns:
        {
            "suggestions": List[Dict],
            "estimated_savings": str,
            "priority": List[str]
        }
    """
    if not AI_AVAILABLE:
        return {"suggestions": [], "estimated_savings": "$0", "priority": []}
    
    try:
        diff_text = "\n\n".join([
            f"File: {hunk.get('file', 'unknown')}\n{hunk.get('hunk', '')}"
            for hunk in diff_hunks
        ])
        
        resource_usage = [s for s in cluster_signals if s.get("metric") in ["cpu_usage", "memory_usage"]]
        
        prompt = f"""Analyze this Kubernetes change for cost optimization opportunities.

DIFF:
{diff_text}

CURRENT RESOURCE USAGE:
{json.dumps(resource_usage, indent=2) if resource_usage else "No usage data"}

Look for:
- Over-provisioned resources
- Missing resource limits
- Inefficient resource requests
- Unused replicas
- Expensive image pulls
- Storage optimization

Respond in JSON:
{{
    "suggestions": [
        {{
            "type": "<resource_limits|replicas|storage|images>",
            "description": "<what to change>",
            "current": "<current state>",
            "recommended": "<recommended state>",
            "savings_estimate": "<$X/month or %>"
        }}
    ],
    "estimated_savings": "<total estimate>",
    "priority": ["<top 3>"]
}}"""

        content = _call_ai_api(
            messages=[
                {
                    "role": "system",
                    "content": "You are a cloud cost optimization expert. Find savings in Kubernetes configs."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        return result
        
    except Exception as e:
        logger.error(f"Cost optimization failed: {str(e)}")
        return {"suggestions": [], "estimated_savings": "$0", "priority": []}

