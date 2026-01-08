"""AI-powered analysis supporting multiple providers (OpenAI, DeepSeek, Claude, Gemini)."""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Supported AI providers
AI_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "base_url": None,  # Uses default OpenAI endpoint
        "default_model": "gpt-4o-mini"
    },
    "deepseek": {
        "name": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat"
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": None,
        "default_model": "claude-3-5-sonnet-20241022"
    },
    "gemini": {
        "name": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "base_url": None,
        "default_model": "gemini-1.5-pro"
    }
}

# Get configured provider from env (defaults to first available)
AI_PROVIDER = os.getenv("AI_PROVIDER", "").lower()
if AI_PROVIDER not in AI_PROVIDERS:
    AI_PROVIDER = None

# Initialize client based on available API keys
client = None
client_type = None
_api_keys = {}  # Store all API keys for sanitization

# Try to initialize client for each provider in priority order
for provider_id, provider_config in AI_PROVIDERS.items():
    api_key = os.getenv(provider_config["env_key"])
    if api_key:
        _api_keys[provider_id] = api_key
        
        # If specific provider requested, only try that one
        if AI_PROVIDER and provider_id != AI_PROVIDER:
            continue
            
        try:
            if provider_id in ["openai", "deepseek"]:
                # OpenAI-compatible API
                # Support custom base URL for OpenAI (e.g., Ollama, LocalAI, etc.)
                base_url = provider_config["base_url"]
                if provider_id == "openai":
                    # Allow override via OPENAI_BASE_URL env var for custom endpoints
                    custom_base_url = os.getenv("OPENAI_BASE_URL")
                    if custom_base_url:
                        base_url = custom_base_url
                        logger.info(f"Using custom OpenAI-compatible endpoint: {base_url}")
                
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url if base_url else None
                )
                client_type = provider_id
                logger.info(f"{provider_config['name']} AI client initialized successfully")
                break
            elif provider_id == "claude":
                # Anthropic Claude - use OpenAI client with Anthropic endpoint
                try:
                    from anthropic import Anthropic
                    client = Anthropic(api_key=api_key)
                    client_type = "claude"
                    logger.info(f"{provider_config['name']} AI client initialized successfully")
                    break
                except ImportError:
                    logger.warning("anthropic package not installed. Install with: pip install anthropic")
            elif provider_id == "gemini":
                # Google Gemini
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    client = genai
                    client_type = "gemini"
                    logger.info(f"{provider_config['name']} AI client initialized successfully")
                    break
                except ImportError:
                    logger.warning("google-generativeai package not installed. Install with: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Failed to initialize {provider_config['name']} client: {str(e)}")
            client = None
            client_type = None

if not client:
    available_keys = [k for k, v in _api_keys.items() if v]
    if available_keys:
        logger.warning(f"AI API keys found but client initialization failed. Available: {', '.join(available_keys)}")
    else:
        logger.warning("No AI API keys found. Set one of: OPENAI_API_KEY, DEEPSEEK_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY")

# Security: Sanitize any strings that might contain API key
def _sanitize_log_message(msg: str) -> str:
    """Remove any potential API key from log messages."""
    sanitized = msg
    for key in _api_keys.values():
        if key:
            sanitized = sanitized.replace(key, "[REDACTED]")
    return sanitized


def _call_ai_api(messages: List[Dict], model: Optional[str] = None, max_tokens: int = 2000, temperature: float = 0.3) -> str:
    """Unified interface to call different AI providers."""
    if not client:
        raise ValueError("AI client not available")
    
    if client_type in ["openai", "deepseek"]:
        # OpenAI-compatible API
        provider_config = AI_PROVIDERS[client_type]
        model = model or provider_config["default_model"]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    
    elif client_type == "claude":
        # Anthropic Claude
        provider_config = AI_PROVIDERS["claude"]
        model = model or provider_config["default_model"]
        # Convert messages format for Claude
        system_msg = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_msg if system_msg else "",
            messages=user_messages
        )
        return response.content[0].text.strip()
    
    elif client_type == "gemini":
        # Google Gemini
        provider_config = AI_PROVIDERS["gemini"]
        model_name = model or provider_config["default_model"]
        gemini_model = client.GenerativeModel(model_name)
        
        # Convert messages format for Gemini
        prompt_parts = []
        for msg in messages:
            role_prefix = "System: " if msg["role"] == "system" else ("User: " if msg["role"] == "user" else "Assistant: ")
            prompt_parts.append(f"{role_prefix}{msg['content']}")
        
        response = gemini_model.generate_content(
            "\n".join(prompt_parts),
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
        )
        return response.text.strip()
    
    else:
        raise ValueError(f"Unsupported AI provider: {client_type}")


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

        # Call AI API (unified interface)
        content = _call_ai_api(
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

        explanation = _call_ai_api(
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
        return explanation
        
    except Exception as e:
        logger.error(f"AI explanation failed: {str(e)}")
        return guardrail_message

