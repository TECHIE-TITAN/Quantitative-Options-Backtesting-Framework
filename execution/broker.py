from typing import List, Optional

from execution.order import Order
from execution.fills import Fill, compute_fill
from config.config import ExecutionConfig
from utils.logging_setup import get_logger

log = get_logger(__name__)

class ExecutionEngine:
    def __init__(self, exec_cfg: ExecutionConfig):
        self.exec_cfg = exec_cfg
        self.rejected_orders: List[Order] = []

    def execute(self, order: Order, feed) -> Optional[Fill]:
        price = feed.option_price_asof(order.strike, order.opt_type, order.timestamp)
        if price is None:
            log.warning(
                "REJECTED order #%d %s %s %s %s @ %s -- no priceable market data",
                order.order_id, order.underlier, order.strike, order.opt_type,
                order.side.value, order.timestamp,
            )
            self.rejected_orders.append(order)
            return None
        fill = compute_fill(order, price, self.exec_cfg)
        log.info(
            "FILLED order #%d %s %s%s %s qty=%d @ %.2f (ref=%.2f) commission=%.2f reason=%s",
            order.order_id, order.underlier, order.strike, order.opt_type,
            order.side.value, order.quantity_lots, fill.fill_price, price,
            fill.commission, order.reason,
        )
        return fill
