"""User model — stores auth identities, points balance, and membership."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str | None] = mapped_column(String(11), unique=True, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(64), default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(512), default=None)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    wechat_openid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    wechat_unionid: Mapped[str | None] = mapped_column(String(128), default=None)
    alipay_user_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)

    points_balance: Mapped[int] = mapped_column(Integer, default=0)

    # ── Membership fields ────────────────────────────────────────────
    membership_tier: Mapped[str] = mapped_column(String(16), default="free")  # free / pro / premium
    membership_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    daily_generations: Mapped[int] = mapped_column(Integer, default=0)
    daily_generations_date: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default=None
    )  # "2026-07-17"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        tier = self.membership_tier
        return f"<User id={self.id} phone={self.phone} tier={tier}>"
