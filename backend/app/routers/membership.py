"""Membership router — tier listing, upgrade, and status queries."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user, require_user
from app.models.user import User
from app.services.membership_service import membership_service, TIERS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/membership", tags=["membership"])


# ── Schemas ──────────────────────────────────────────────────────────


class TierResponse(BaseModel):
    id: str
    label: str
    max_points: int
    daily_free: int
    price_discount: float
    price: float


class TiersListResponse(BaseModel):
    tiers: list[TierResponse]


class UpgradeRequest(BaseModel):
    tier: str  # "pro" or "premium"
    channel: str = "mock"


class UpgradeResponse(BaseModel):
    tier: str
    status: str
    expires_at: str


class MembershipStatusResponse(BaseModel):
    tier: str
    label: str
    expires_at: str | None
    daily_left: int
    points_balance: int
    max_points: int


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/tiers", response_model=TiersListResponse)
async def list_tiers():
    """List all membership tiers with their benefits."""
    return TiersListResponse(
        tiers=[TierResponse(**t) for t in membership_service.get_all_tiers()]
    )


@router.post("/upgrade", response_model=UpgradeResponse)
async def upgrade_membership(
    req: UpgradeRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
):
    """Upgrade user membership (mock payment).

    In production, this would redirect to WeChat/Alipay payment.
    For local dev, the mock channel immediately activates the tier for 30 days.
    """
    if req.tier not in ("pro", "premium"):
        raise HTTPException(status_code=400, detail="无效的会员等级，仅支持 pro / premium")

    if user.membership_tier == "premium":
        raise HTTPException(status_code=400, detail="已经是最高级会员")

    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    user.membership_tier = req.tier
    user.membership_expires_at = expires_at
    # Reset daily counter on upgrade (fresh start)
    user.daily_generations = 0
    from datetime import date
    user.daily_generations_date = date.today().isoformat()
    await session.commit()

    logger.info("User %s upgraded to %s, expires at %s", user.id, req.tier, expires_at)

    return UpgradeResponse(
        tier=req.tier,
        status="active",
        expires_at=expires_at.isoformat(),
    )


@router.get("/my-status", response_model=MembershipStatusResponse)
async def my_membership_status(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
):
    """Return current user's membership status and daily quota info."""
    tier = user.membership_tier
    config = TIERS.get(tier, TIERS["free"])
    daily_left = membership_service.tier_daily_left(user)

    expires = None
    if user.membership_expires_at:
        expires = user.membership_expires_at.isoformat()
        # Auto-downgrade check: expire past → show as free
        # SQLite loses tz info on write, so compare as naive UTC
        expires_naive = user.membership_expires_at.replace(tzinfo=None)
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        if expires_naive < now_naive:
            tier = "free"
            config = TIERS["free"]
            daily_left = config["daily_free"]

    return MembershipStatusResponse(
        tier=tier,
        label=config["label"],
        expires_at=expires,
        daily_left=daily_left,
        points_balance=user.points_balance,
        max_points=config["max_points"],
    )
