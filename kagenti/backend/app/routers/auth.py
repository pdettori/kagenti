# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""
Authentication API endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user, get_required_user, TokenData
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class UserInfoResponse(BaseModel):
    """User information response."""

    username: str
    email: Optional[str] = None
    roles: List[str] = []
    authenticated: bool = True


class AuthStatusResponse(BaseModel):
    """Authentication status response."""

    enabled: bool
    authenticated: bool
    keycloak_url: Optional[str] = None
    realm: Optional[str] = None
    client_id: Optional[str] = None


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    user: Optional[TokenData] = Depends(get_current_user),
) -> AuthStatusResponse:
    """
    Get authentication status and configuration.

    Returns whether auth is enabled and current authentication state.
    """
    keycloak_url = settings.keycloak_url or f"http://keycloak.{settings.domain_name}:8080"

    return AuthStatusResponse(
        enabled=settings.enable_auth,
        authenticated=user is not None,
        keycloak_url=keycloak_url if settings.enable_auth else None,
        realm=settings.keycloak_realm if settings.enable_auth else None,
        client_id=settings.keycloak_client_id if settings.enable_auth else None,
    )


@router.get("/userinfo", response_model=UserInfoResponse)
async def get_user_info(
    user: TokenData = Depends(get_required_user),
) -> UserInfoResponse:
    """
    Get current user information.

    Requires authentication.
    """
    return UserInfoResponse(
        username=user.username,
        email=user.email,
        roles=user.roles,
        authenticated=True,
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    user: Optional[TokenData] = Depends(get_current_user),
) -> UserInfoResponse:
    """
    Get current user information (optional auth).

    Returns guest user info if not authenticated.
    """
    if user is None:
        return UserInfoResponse(
            username="guest",
            email=None,
            roles=[],
            authenticated=False,
        )

    return UserInfoResponse(
        username=user.username,
        email=user.email,
        roles=user.roles,
        authenticated=True,
    )
