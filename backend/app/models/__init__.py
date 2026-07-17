"""Model registry — imported by init_db() to ensure all models are registered."""

from app.models.user import User
from app.models.order import Order
from app.models.points_ledger import PointsLedger

__all__ = ["User", "Order", "PointsLedger"]
