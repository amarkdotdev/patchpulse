"""AI-powered analysis using DeepSeek API."""

import os
import json
import logging
from typing import Dict, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize DeepSeek client - SECURE: Never log or expose API key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# Security: Validate API key format without exposing it
def _validate_api_key(key: Optional[str]) -> bool:
    """Validate API key format without exposing the key."""
    if not key:
        return False
    # Check it starts with 'sk-' and has reasonable length
    return key.startswith("sk-") and len(key) > 20

client = None
if DEEPSEEK_API_KEY and _validate_api_key(DEEPSEEK_API_KEY):
    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        # Test connection without exposing key
        logger.info("DeepSeek AI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DeepSeek client: {str(e)}")
        client = None
else:
    logger.warning("DEEPSEEK_API_KEY not found or invalid, AI analysis will be disabled")

# Security: Sanitize any strings that might contain API key
def _sanitize_log_message(msg: str) -> str:
    """Remove any potential API key from log messages."""
    if DEEPSEEK_API_KEY:
        return msg.replace(DEEPSEEK_API_KEY, "[REDACTED]")
    return msg


def analyze_change_with_ai(
    diff_hunks: List[Dict],
    files: List[str],
    cluster_signals: List[Dict],
    repo: str,
    branch: str
) -> Dict:
    """
    Use AI to analyze Kubernetes changes and provide risk assessment.
    
    Returns:
        {
            "risk_score": int (0-100),
            "ai_analysis": str,
            "recommendations": List[str],
            "potential_issues": List[str],
            "confidence": float (0-1)
        }
    """
    if not client:
        logger.warning("AI client not available, skipping AI analysis")
        return {
            "risk_score": 0,
            "ai_analysis": "AI analysis unavailable",
            "recommendations": [],
            "potential_issues": [],
            "confidence": 0.0
        }
    
    try:
        # Build context for AI
        diff_text = "\n\n".join([
            f"File: {hunk.get('file', 'unknown')}\n{hunk.get('hunk', '')}"
            for hunk in diff_hunks
        ])
        
        cluster_context = ""
        if cluster_signals:
            cluster_context = "\n".join([
                f"- {s.get('kind', 'unknown')} {s.get('name', 'unknown')}: "
                f"{s.get('metric', 'unknown')} = {s.get('value', 0)}"
                for s in cluster_signals[:10]  # Limit to 10 signals
            ])
        
        # Create AI prompt
        prompt = f"""You are an expert Kubernetes SRE analyzing a deployment change for potential risks.

Repository: {repo}
Branch: {branch}
Files Changed: {', '.join(files)}

DIFF:
{diff_text}

CURRENT CLUSTER STATE:
{cluster_context if cluster_context else "No recent cluster signals"}

Analyze this change and provide:
1. Risk score (0-100) - How risky is this change?
2. Detailed analysis - What are the potential issues?
3. Specific recommendations - What should be changed?
4. Potential issues - List specific problems you see

Focus on:
- Resource limits and requests
- Security contexts
- Network policies
- Health checks
- Replica counts
- Image tags
- Configuration changes
- Compatibility with current cluster state

Respond in JSON format:
{{
    "risk_score": <0-100>,
    "ai_analysis": "<detailed explanation>",
    "recommendations": ["<rec1>", "<rec2>", ...],
    "potential_issues": ["<issue1>", "<issue2>", ...],
    "confidence": <0.0-1.0>
}}"""

        # Call DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Kubernetes SRE. Analyze changes and provide risk assessments in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=2000
        )
        
        # Parse response
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            ai_result = json.loads(content)
            
            # Validate and normalize
            risk_score = max(0, min(100, int(ai_result.get("risk_score", 0))))
            ai_analysis = ai_result.get("ai_analysis", "No analysis provided")
            recommendations = ai_result.get("recommendations", [])
            potential_issues = ai_result.get("potential_issues", [])
            confidence = max(0.0, min(1.0, float(ai_result.get("confidence", 0.5))))
            
            logger.info(f"AI analysis completed: risk_score={risk_score}, confidence={confidence}")
            
            return {
                "risk_score": risk_score,
                "ai_analysis": ai_analysis,
                "recommendations": recommendations[:5],  # Limit to 5
                "potential_issues": potential_issues[:5],  # Limit to 5
                "confidence": confidence
            }
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response as JSON: {content[:200]}")
            # Fallback: try to extract risk score from text
            risk_score = 50  # Default
            if "risk" in content.lower():
                # Try to find a number between 0-100
                import re
                scores = re.findall(r'\b(\d{1,2}|100)\b', content)
                if scores:
                    risk_score = min(100, max(0, int(scores[0])))
            
            return {
                "risk_score": risk_score,
                "ai_analysis": content[:500],  # Truncate if too long
                "recommendations": [],
                "potential_issues": [],
                "confidence": 0.5
            }
            
    except Exception as e:
        logger.error(f"AI analysis failed: {str(e)}", exc_info=True)
        return {
            "risk_score": 0,
            "ai_analysis": f"AI analysis error: {str(e)}",
            "recommendations": [],
            "potential_issues": [],
            "confidence": 0.0
        }


def explain_guardrail_with_ai(
    guardrail_id: str,
    guardrail_message: str,
    evidence: List[str],
    diff_context: str
) -> str:
    """
    Use AI to provide a detailed explanation of why a guardrail was triggered.
    
    Returns a human-readable explanation.
    """
    if not client:
        return guardrail_message
    
    try:
        prompt = f"""Explain why this Kubernetes guardrail was triggered in simple, actionable terms.

Guardrail: {guardrail_id}
Message: {guardrail_message}
Evidence: {', '.join(evidence)}

Change Context:
{diff_context[:500]}

Provide a clear, concise explanation (2-3 sentences) that helps a developer understand:
1. What the problem is
2. Why it's risky
3. What they should do about it"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful SRE explaining Kubernetes best practices."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_tokens=300
        )
        
        explanation = response.choices[0].message.content.strip()
        return explanation
        
    except Exception as e:
        logger.error(f"AI explanation failed: {str(e)}")
        return guardrail_message

