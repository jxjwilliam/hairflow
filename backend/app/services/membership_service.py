"""Membership tier enforcement and benefits calculation."""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)

TIERS: dict[str, dict] = {
    "free": {
        "label": "免费用户",
        "max_points": 50,
        "daily_free": 2,
        "price_discount": 1.0,
        "price": 0.0,
    },
    "pro": {
        "label": "Pro 会员",
        "max_points": 200,
        "daily_free": 10,
        "price_discount": 0.9,
        "price": 19.90,
    },
    "premium": {
        "label": "Premium 会员",
        "max_points": 1000,
        "daily_free": 999,
        "price_discount": 0.8,
        "price": 49.90,
    },
}


class MembershipService:
    """Manage membership tiers, daily quotas, and pricing benefits."""

    async def check_generation_quota(self, user: User) -> bool:
        """Return True if user still has daily generations left."""
        today = date.today().isoformat()
        config = TIERS.get(user.membership_tier, TIERS["free"])
        limit = config["daily_free"]

        if user.daily_generations_date != today:
            return True  # fresh day — always allowed

        return user.daily_generations < limit

    async def record_generation(self, session: AsyncSession, user: User) -> None:
        """Increment daily generation counter, resetting if new day."""
        today = date.today().isoformat()
        if user.daily_generations_date != today:
            user.daily_generations_date = today
            user.daily_generations = 0
        user.daily_generations += 1
        await session.commit()

    def get_discounted_price(self, tier: str, original_price: float) -> float:
        config = TIERS.get(tier, TIERS["free"])
        return round(original_price * config["price_discount"], 2)

    def tier_daily_left(self, user: User) -> int:
        """Return remaining daily generations for display."""
        today = date.today().isoformat()
        config = TIERS.get(user.membership_tier, TIERS["free"])
        limit = config["daily_free"]
        if user.daily_generations_date != today:
            return limit
        return max(0, limit - user.daily_generations)

    def get_tier_config(self, tier_id: str) -> Optional[dict]:
        return TIERS.get(tier_id)

    def get_all_tiers(self) -> list[dict]:
        return [
            {
                "id": tid,
                "label": cfg["label"],
                "max_points": cfg["max_points"],
                "daily_free": cfg["daily_free"],
                "price_discount": cfg["price_discount"],
                "price": cfg["price"],
            }
            for tid, cfg in TIERS.items()
        ]


membership_service = MembershipService()
