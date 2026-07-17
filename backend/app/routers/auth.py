"""Auth router — SMS registration/login, JWT token management."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user, require_user
from app.models.user import User
from app.services.auth_service import (
    login_or_register,
    send_sms_code,
    verify_sms_code,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Request / Response schemas ──────────────────────────────────────


class SmsSendRequest(BaseModel):
    phone: str


class SmsSendResponse(BaseModel):
    message: str


class SmsLoginRequest(BaseModel):
    phone: str
    code: str


class SmsLoginResponse(BaseModel):
    user_id: int
    token: str
    points_balance: int
    nickname: str | None = None


class UserProfileResponse(BaseModel):
    id: int
    phone: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    points_balance: int
    created_at: str | None = None


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/sms/send", response_model=SmsSendResponse)
async def sms_send(req: SmsSendRequest):
    """Send SMS verification code.

    Local dev: code is logged to console + magic code '888888' always works.
    """
    if not req.phone or len(req.phone) < 5:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    await send_sms_code(req.phone)
    return SmsSendResponse(message="验证码已发送")


@router.post("/sms/login", response_model=SmsLoginResponse)
async def sms_login(req: SmsLoginRequest, session: AsyncSession = Depends(get_session)):
    """Login with phone + SMS code. Registers new user if not exists.

    Local dev: use any phone + code '888888'.
    """
    if not await verify_sms_code(req.phone, req.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    user, token = await login_or_register(session, req.phone)
    return SmsLoginResponse(
        user_id=user.id,
        token=token,
        points_balance=user.points_balance,
        nickname=user.nickname,
    )


@router.post("/wechat/login")
async def wechat_login():
    """WeChat OAuth login (stub — not yet implemented).

    Will accept wechat code → exchange for openid → login/register.
    """
    raise HTTPException(status_code=501, detail="微信登录尚未实现")


@router.post("/alipay/login")
async def alipay_login():
    """Alipay OAuth login (stub — not yet implemented)."""
    raise HTTPException(status_code=501, detail="支付宝登录尚未实现")


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(user: User = Depends(require_user)):
    """Get current user profile (requires auth token)."""
    return UserProfileResponse(
        id=user.id,
        phone=user.phone,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        points_balance=user.points_balance,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
