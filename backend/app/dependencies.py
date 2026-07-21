"""FastAPI dependency injection — JWT auth, database sessions, etc."""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Extract and validate JWT from Authorization header.

    Returns None if no token is provided (anonymous access).
    Expired/invalid tokens are treated as anonymous for optional-auth routes
    (generate still works when SKIP_POINTS_CHECK=true); require_user still
    rejects anonymous callers.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: int | None = payload.get("user_id")
        if user_id is None:
            logger.warning("JWT missing user_id — treating as anonymous")
            return None
    except JWTError as e:
        # Stale login after JWT_EXPIRE_HOURS must not block anonymous generate.
        logger.warning("JWT decode failed (%s) — treating as anonymous", e)
        return None

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning("JWT user_id=%s not found — treating as anonymous", user_id)
        return None
    return user


async def require_user(
    user: User | None = Depends(get_current_user),
) -> User:
    """Require an authenticated user. Raises 401 if not logged in."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user
