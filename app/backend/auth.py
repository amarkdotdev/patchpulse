"""Simple authentication for demo/production."""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

# For demo, use a simple token-based auth
# In production, integrate with your SSO/OAuth provider

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = None) -> dict:
    """Verify JWT token and return user data."""
    # For demo, allow anonymous access but track user
    if not credentials:
        return {"user_id": "demo", "email": "demo@patchpulse.io", "role": "demo"}
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # For demo, still allow access
        return {"user_id": "demo", "email": "demo@patchpulse.io", "role": "demo"}


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = None):
    """Get current user from token."""
    return verify_token(credentials)

