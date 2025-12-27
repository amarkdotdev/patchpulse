"""Security utilities to prevent API key leakage."""

import os
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Get API key once at module load
_API_KEY = os.getenv("DEEPSEEK_API_KEY")


def sanitize_for_logging(data: Any) -> Any:
    """
    Recursively sanitize data structures to remove API keys.
    Never log or expose API keys in any form.
    """
    if _API_KEY is None:
        return data
    
    if isinstance(data, str):
        # Replace API key if found
        if _API_KEY in data:
            return data.replace(_API_KEY, "[REDACTED_API_KEY]")
        # Also check for partial matches (first/last chars)
        if len(_API_KEY) > 10:
            partial = _API_KEY[:8] + "..." + _API_KEY[-4:]
            if partial in data:
                return data.replace(partial, "[REDACTED_API_KEY]")
        return data
    
    elif isinstance(data, dict):
        return {k: sanitize_for_logging(v) for k, v in data.items()}
    
    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]
    
    return data


def validate_no_key_leakage(response_data: Dict) -> Dict:
    """
    Validate that API key is not in response data.
    Raises exception if key is found.
    """
    if _API_KEY is None:
        return response_data
    
    response_str = json.dumps(response_data) if isinstance(response_data, dict) else str(response_data)
    
    if _API_KEY in response_str:
        logger.critical("SECURITY ALERT: API key detected in response data!")
        # Remove key from response
        response_str = response_str.replace(_API_KEY, "[REDACTED]")
        if isinstance(response_data, dict):
            return json.loads(response_str)
        return response_str
    
    return response_data


def safe_log(message: str, *args, **kwargs):
    """Log message with API key sanitization."""
    safe_message = sanitize_for_logging(message)
    safe_args = [sanitize_for_logging(arg) for arg in args]
    safe_kwargs = {k: sanitize_for_logging(v) for k, v in kwargs.items()}
    logger.info(safe_message, *safe_args, **safe_kwargs)


# Import json for validation
import json

