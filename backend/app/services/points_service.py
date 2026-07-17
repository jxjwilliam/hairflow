"""Points service — deduct/credit points with audit trail."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.order import Order
from app.models.points_ledger import PointsLedger
from app.models.user import User

logger = logging.getLogger(__name__)

PACKAGES = [
    {"id": "basic", "name": "基础包", "points": 10, "price": 9.90},
    {"id": "advanced", "name": "进阶包", "points": 30, "price": 19.90},
    {"id": "unlimited", "name": "畅享包", "points": 100, "price": 49.90},
]


async def deduct_points(
    session: AsyncSession, user: User, amount: int, txn_type: str, description: str | None = None
) -> bool:
    """Deduct points from user balance. Returns True if successful, False if insufficient."""
    if settings.skip_points_check:
        logger.info("[DEV] Skipping points deduction (skip_points_check=True)")
        return True

    if user.points_balance < amount:
        logger.warning("Insufficient points: user=%d balance=%d need=%d", user.id, user.points_balance, amount)
        return False

    user.points_balance -= amount
    ledger = PointsLedger(
        user_id=user.id,
        amount=-amount,
        type=txn_type,
        balance_after=user.points_balance,
        description=description or f"{txn_type} 消耗 {amount} 点",
    )
    session.add(ledger)
    await session.commit()
    logger.info("Points deducted: user=%d amount=%d balance=%d", user.id, amount, user.points_balance)
    return True


async def credit_points(
    session: AsyncSession,
    user: User,
    amount: int,
    txn_type: str,
    description: str | None = None,
) -> None:
    """Credit points to user balance (for recharge or bonus)."""
    user.points_balance += amount
    ledger = PointsLedger(
        user_id=user.id,
        amount=amount,
        type=txn_type,
        balance_after=user.points_balance,
        description=description or f"{txn_type} 获得 {amount} 点",
    )
    session.add(ledger)
    await session.commit()
    logger.info("Points credited: user=%d amount=%d balance=%d", user.id, amount, user.points_balance)


def generate_order_no() -> str:
    """Generate a unique order number: HR + timestamp + random."""
    ts = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    rand = uuid.uuid4().hex[:6].upper()
    return f"HR{ts}{rand}"


async def create_order(
    session: AsyncSession,
    user_id: int,
    package_id: str,
    channel: str = "mock",
) -> Order:
    """Create a new order for a points package. Returns the Order."""
    package = next((p for p in PACKAGES if p["id"] == package_id), None)
    if package is None:
        raise ValueError(f"Unknown package: {package_id}")

    order = Order(
        order_no=generate_order_no(),
        user_id=user_id,
        amount=package["price"],
        points=package["points"],
        channel=channel,
        status="pending",
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    logger.info("Order created: order_no=%s user=%d amount=%.2f", order.order_no, user_id, order.amount)
    return order


async def complete_order(session: AsyncSession, order_no: str) -> Order | None:
    """Mark an order as paid and credit points to user. Returns the updated Order."""
    result = await session.execute(select(Order).where(Order.order_no == order_no))
    order = result.scalar_one_or_none()
    if order is None:
        logger.warning("Order not found: %s", order_no)
        return None

    if order.status == "paid":
        logger.warning("Order already paid: %s", order_no)
        return order

    # Update order
    order.status = "paid"
    order.paid_at = datetime.now(timezone.utc)

    # Credit points to user
    user_result = await session.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        await credit_points(session, user, order.points, "recharge", f"充值 {order.points} 点")

    await session.commit()
    await session.refresh(order)
    logger.info("Order completed: %s user=%d points=%d", order_no, order.user_id, order.points)
    return order
