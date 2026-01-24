"""
Authentication endpoints for orchestrator UI.

Validates users against Habit Platform API and manages access tokens.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from orchestrator.database import get_db
from orchestrator.database.models import UserSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# Pydantic schemas
class LoginRequest(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with user info and token."""
    success: bool
    message: str
    user: dict
    access_token: str


class LogoutResponse(BaseModel):
    """Logout confirmation."""
    success: bool
    message: str


class UserInfoResponse(BaseModel):
    """Current user information."""
    email: str
    name: str
    roles: list
    last_login: Optional[datetime]


# Helper functions
def get_habit_auth_url() -> str:
    """Get Habit Platform authentication URL from environment."""
    base_url = os.getenv(
        "HABIT_AUTH_URL",
        "https://api.platform.integrations.habit.io"
    )
    app_id = os.getenv(
        "HABIT_APPLICATION_ID",
        "af620e5c-dc3a-47e8-9976-7e673e0fb5f0"
    )
    return f"{base_url}/v3/applications/{app_id}/login"


def get_habit_user_me_url() -> str:
    """Get Habit Platform user info URL from environment."""
    base_url = os.getenv(
        "HABIT_AUTH_URL",
        "https://api.platform.integrations.habit.io"
    )
    return f"{base_url}/v3/users/me"


async def validate_token_with_habit(access_token: str) -> Optional[dict]:
    """
    Validate access token with Habit Platform.
    
    Returns user info if valid, None otherwise.
    """
    url = get_habit_user_me_url()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Token validation failed: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"Error validating token with Habit: {e}")
        return None


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> UserSession:
    """
    Dependency to get current authenticated user.
    
    Validates the Bearer token from Authorization header.
    Required for all UI endpoints.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = parts[1]
    
    # Check if token exists in database
    session = db.query(UserSession).filter(
        UserSession.access_token == token
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last_activity
    session.last_activity = datetime.utcnow()
    db.commit()
    
    return session


def get_current_user_from_query(
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> UserSession:
    """
    Dependency to get current authenticated user from query parameter.
    
    Used for endpoints that cannot use Authorization headers (e.g., SSE streams).
    Validates the token from ?token=<token> query parameter.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token query parameter",
        )
    
    # Check if token exists in database
    session = db.query(UserSession).filter(
        UserSession.access_token == token
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    # Update last_activity
    session.last_activity = datetime.utcnow()
    db.commit()
    
    return session


# API endpoints
@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user with Habit Platform.
    
    Validates credentials against Habit Platform API and returns access token.
    Only users with ADMIN role are allowed.
    """
    url = get_habit_auth_url()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "email": credentials.email,
                    "password": credentials.password,
                },
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            
            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            if response.status_code != 200:
                logger.error(f"Habit auth failed: {response.status_code} {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Authentication service unavailable"
                )
            
            data = response.json()
            
            if not data.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )
            
            user_data = data.get("user", {})
            roles = user_data.get("roles", [])
            
            # Check if user has ADMIN role
            if "ADMIN" not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Only Habit administrators are allowed."
                )
            
            access_token = user_data.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No access token received from authentication service"
                )
            
            # Store or update session in database
            existing_session = db.query(UserSession).filter(
                UserSession.email == credentials.email
            ).first()
            
            if existing_session:
                # Update existing session
                existing_session.access_token = access_token
                existing_session.refresh_token = user_data.get("refresh_token")
                existing_session.user_data = user_data
                existing_session.last_login = datetime.utcnow()
                existing_session.last_activity = datetime.utcnow()
                session = existing_session
            else:
                # Create new session
                session = UserSession(
                    email=credentials.email,
                    access_token=access_token,
                    refresh_token=user_data.get("refresh_token"),
                    user_data=user_data,
                    last_login=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                )
                db.add(session)
            
            db.commit()
            db.refresh(session)
            
            logger.info(f"User {credentials.email} logged in successfully")
            
            return LoginResponse(
                success=True,
                message="Login successful",
                user=user_data,
                access_token=access_token
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user.
    
    Removes the user session from database.
    """
    email = current_user.email
    
    db.delete(current_user)
    db.commit()
    
    logger.info(f"User {email} logged out")
    
    return LogoutResponse(
        success=True,
        message="Logged out successfully"
    )


@router.get("/me", response_model=UserInfoResponse)
def get_current_user_info(current_user: UserSession = Depends(get_current_user)):
    """
    Get current user information.
    
    Returns user details from the active session.
    """
    user_data = current_user.user_data or {}
    
    return UserInfoResponse(
        email=current_user.email,
        name=user_data.get("name", ""),
        roles=user_data.get("roles", []),
        last_login=current_user.last_login
    )


@router.post("/validate")
async def validate_token(
    current_user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate current token with Habit Platform.
    
    Checks if the token is still valid on Habit's side.
    """
    user_info = await validate_token_with_habit(current_user.access_token)
    
    if not user_info:
        # Token is invalid, remove session
        db.delete(current_user)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is no longer valid"
        )
    
    return {
        "valid": True,
        "user": user_info
    }
