"""User model — stores auth identities and points balance."""

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} phone={self.phone}>"
