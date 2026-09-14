"""API router for authentication and identity introspection."""

from typing import Annotated

from fastapi import APIRouter, Depends

from core.auth import UserProfile, get_current_user_profile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserProfile)
def get_me(
    profile: Annotated[UserProfile, Depends(get_current_user_profile)],
) -> UserProfile:
    """Return the profile and authentication state of the calling user."""
    return profile
