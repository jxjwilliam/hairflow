"""Auth service — SMS verification code management, JWT token generation."""

import logging
import random
import string
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory SMS code store (local dev only).
# For production, replace with Redis or DB-backed storage.
# Key: phone, Value: {"code": str, "expires_at": datetime}
_sms_store: dict[str, dict] = {}


def _generate_code(length: int = 6) -> str:
    """Generate a random numeric code."""
    return "".join(random.choices(string.digits, k=length))


def _create_jwt(user_id: int) -> str:
    """Create a JWT access token for the given user."""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def send_sms_code(phone: str) -> str:
    """Send (or simulate) an SMS verification code.

    In local dev mode, prints the code to logs and stores it in memory.
    The magic code '888888' always works regardless of what was sent.
    Returns the code for convenience (in production, never return it).
    """
    if settings.dev_magic_code:
        # Magic code mode — always use the dev code
        code = settings.dev_magic_code
        logger.info(
            "[DEV] SMS code for %s: %s (or use magic code: %s)",
            phone, code, settings.dev_magic_code,
        )
    else:
        code = _generate_code()
        logger.info("[SMS] Verification code for %s: %s", phone, code)

    _sms_store[phone] = {
        "code": code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    return code


async def verify_sms_code(phone: str, code: str) -> bool:
    """Verify an SMS code. Returns True if valid and not expired."""
    # Magic code always works in dev
    if settings.dev_magic_code and code == settings.dev_magic_code:
        return True

    record = _sms_store.get(phone)
    if record is None:
        logger.warning("No code sent for %s", phone)
        return False

    if datetime.now(timezone.utc) > record["expires_at"]:
        logger.warning("SMS code expired for %s", phone)
        _sms_store.pop(phone, None)
        return False

    if code != record["code"]:
        logger.warning("Invalid SMS code for %s", phone)
        return False

    # Consume the code
    _sms_store.pop(phone, None)
    return True


async def login_or_register(
    session: AsyncSession, phone: str
) -> tuple[object, str]:
    """Find or create user by phone, return (user, jwt_token)."""
    from app.models.user import User

    result = await session.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user is None:
        # New user — register + grant bonus points (single transaction)
        user = User(
            phone=phone,
            phone_verified=True,
            nickname=f"用户{phone[-4:]}",
            points_balance=3,  # 新用户赠送 3 点
        )
        session.add(user)
        await session.flush()  # get user.id without committing

        from app.models.points_ledger import PointsLedger
        ledger = PointsLedger(
            user_id=user.id,
            amount=3,
            type="bonus",
            balance_after=user.points_balance,
            description="新用户注册赠送",
        )
        session.add(ledger)
        await session.commit()  # single commit for user + ledger
        await session.refresh(user)
        logger.info("New user registered: phone=%s id=%d", phone, user.id)
    else:
        logger.info("Existing user login: phone=%s id=%d", phone, user.id)

    token = _create_jwt(user.id)
    return user, token
