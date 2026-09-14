"""Authentication and identity resolution dependencies."""

from datetime import datetime, timedelta, timezone
import os
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, status
import jwt
from pydantic import BaseModel

from core.settings import settings

# Default deterministic owner ID for local development and single-user mode
DEFAULT_OWNER_ID = "owner_local_default"


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
    secret: str | None = None,
    algorithm: str | None = None,
) -> str:
    """Generate a signed JWT token with sub and expiration."""
    now = datetime.now(timezone.utc)
    delta = expires_delta if expires_delta is not None else timedelta(hours=1)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + delta).timestamp()),
    }
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience
    if settings.jwt_issuer:
        payload["iss"] = settings.jwt_issuer
    if extra_claims:
        payload.update(extra_claims)

    key = secret or settings.jwt_secret
    alg = algorithm or settings.jwt_algorithm
    return jwt.encode(payload, key=key, algorithm=alg)


def get_current_owner_id(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_owner_id: Annotated[str | None, Header(alias="X-Owner-Id")] = None,
) -> str:
    """Resolve the current active owner identifier.

    - If Authorization: Bearer <token> is provided, validates the JWT and extracts sub.
    - If no Authorization header is provided:
        - In AUTH_MODE="jwt", raises 401 Unauthorized.
        - In AUTH_MODE="local", allows overriding via X-Owner-Id (for isolation tests)
          or defaults to DEFAULT_OWNER_ID.
    """
    if authorization and authorization.strip():
        parts = authorization.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1]
        try:
            decode_options = {
                "verify_aud": bool(settings.jwt_audience),
                "verify_iss": bool(settings.jwt_issuer),
            }
            payload = jwt.decode(
                token,
                key=settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
                options=decode_options,  # pyright: ignore[reportArgumentType]
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {err}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        sub = payload.get("sub")
        if not sub or not str(sub).strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token missing required 'sub' claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return str(sub).strip()

    # No Authorization header provided
    if settings.auth_mode == "jwt":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required Authorization bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if x_owner_id and x_owner_id.strip():
        return x_owner_id.strip()
    return os.getenv("DEFAULT_OWNER_ID", DEFAULT_OWNER_ID)


class UserProfile(BaseModel):
    owner_id: str
    auth_mode: str
    authenticated: bool


def get_current_user_profile(
    owner_id: Annotated[str, Depends(get_current_owner_id)],
) -> UserProfile:
    """Return identity and authentication state of the current caller."""
    is_authenticated = settings.auth_mode == "jwt" or owner_id != DEFAULT_OWNER_ID
    return UserProfile(
        owner_id=owner_id,
        auth_mode=settings.auth_mode,
        authenticated=is_authenticated,
    )

