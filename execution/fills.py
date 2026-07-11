from dataclasses import dataclass
import pandas as pd

from execution.order import Order, Side
from config.config import ExecutionConfig

@dataclass
class Fill:
    order: Order
    fill_price: float
    quantity_units: int      # quantity_lots * lot_size
    commission: float
    timestamp: pd.Timestamp

    @property
    def gross_notional(self) -> float:
        return self.fill_price * self.quantity_units

def compute_fill(order: Order, reference_price: float, exec_cfg: ExecutionConfig) -> Fill:
    lot_size = exec_cfg.lot_size.get(order.underlier, 1)
    units = order.quantity_lots * lot_size

    # Slippage always works against the trader.
    if order.side == Side.BUY:
        fill_price = reference_price * (1 + exec_cfg.slippage_pct)
    else:
        fill_price = reference_price * (1 - exec_cfg.slippage_pct)
    fill_price = max(fill_price, 0.05)  # options can't price negative/zero

    notional = fill_price * units
    commission = (
        exec_cfg.brokerage_per_lot * order.quantity_lots
        + exec_cfg.transaction_cost_pct * notional
    )

    return Fill(
        order=order,
        fill_price=fill_price,
        quantity_units=units,
        commission=commission,
        timestamp=order.timestamp,
    )
