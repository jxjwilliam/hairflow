"""Order model — tracks payment orders and their status."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # 实付金额（元）
    points: Mapped[int] = mapped_column(Integer, nullable=False)  # 购买点数
    channel: Mapped[str | None] = mapped_column(
        String(16), default=None  # "wechat" / "alipay" / "mock"
    )
    status: Mapped[str] = mapped_column(
        String(16), default="pending"  # pending / paid / failed / refunded
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} order_no={self.order_no} status={self.status}>"
