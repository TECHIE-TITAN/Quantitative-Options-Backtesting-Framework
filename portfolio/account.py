from execution.order import Order
from portfolio.portfolio import Portfolio
from config.config import ExecutionConfig
from utils.logging_setup import get_logger

log = get_logger(__name__)

class Account:
    def __init__(self, portfolio: Portfolio, exec_cfg: ExecutionConfig, max_exposure_pct: float = 0.9):
        self.portfolio = portfolio
        self.exec_cfg = exec_cfg
        self.max_exposure_pct = max_exposure_pct

    def pre_trade_check(self, order: Order, reference_price: float) -> bool:
        """Rough affordability check using the last known reference price.
        Real fill price (with slippage) is only known after execution, so
        this is deliberately conservative (uses ask-side slippage buffer)."""
        lot_size = self.exec_cfg.lot_size.get(order.underlier, 1)
        est_price = reference_price * (1 + self.exec_cfg.slippage_pct)
        est_cost = est_price * lot_size * order.quantity_lots
        if est_cost > self.portfolio.cash:
            log.warning(
                "Order #%d rejected by risk check: est_cost=%.2f > cash=%.2f",
                order.order_id, est_cost, self.portfolio.cash,
            )
            return False
        return True
