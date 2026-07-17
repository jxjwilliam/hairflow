"""Payment router — points packages, order creation, mock payment callback."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user, require_user
from app.models.user import User
from app.services.points_service import PACKAGES, complete_order, create_order

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payment", tags=["payment"])


# ── Schemas ─────────────────────────────────────────────────────────


class PackageResponse(BaseModel):
    id: str
    name: str
    points: int
    price: float


class CreateOrderRequest(BaseModel):
    package_id: str
    channel: str = "mock"  # "wechat" / "alipay" / "mock"


class CreateOrderResponse(BaseModel):
    order_no: str
    amount: float
    points: int
    status: str


class MockNotifyRequest(BaseModel):
    order_no: str


class MockNotifyResponse(BaseModel):
    status: str
    points_credited: int
    balance_after: int


# ── Endpoints ───────────────────────────────────────────────────────


@router.get("/packages", response_model=list[PackageResponse])
async def list_packages():
    """List available points packages."""
    return [PackageResponse(**p) for p in PACKAGES]


@router.post("/order", response_model=CreateOrderResponse)
async def create_payment_order(
    req: CreateOrderRequest,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user),
):
    """Create a payment order for a points package.

    Requires authentication. Returns order_no for payment processing.
    """
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")

    try:
        order = await create_order(session, user.id, req.package_id, channel=req.channel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return CreateOrderResponse(
        order_no=order.order_no,
        amount=order.amount,
        points=order.points,
        status=order.status,
    )


@router.post("/mock/notify", response_model=MockNotifyResponse)
async def mock_payment_notify(
    req: MockNotifyRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
):
    """Mock payment callback — simulates successful payment.

    Requires authentication and verifies order ownership.
    In production, this would be a webhook called by WeChat/Alipay.
    For local dev, call this directly after creating an order.
    """
    order = await complete_order(session, req.order_no)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作此订单")

    await session.refresh(user)
    return MockNotifyResponse(
        status=order.status,
        points_credited=order.points,
        balance_after=user.points_balance,
    )
