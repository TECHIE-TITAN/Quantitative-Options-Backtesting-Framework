from dataclasses import dataclass
from typing import Optional
import pandas as pd

@dataclass
class Position:
    underlier: str
    strike: float
    opt_type: str
    quantity_units: int          # signed: +ve long, -ve short
    entry_price: float
    entry_time: pd.Timestamp
    entry_commission: float
    lot_size: int

    exit_price: Optional[float] = None
    exit_time: Optional[pd.Timestamp] = None
    exit_commission: float = 0.0
    exit_reason: str = ""

    @property
    def is_open(self) -> bool:
        return self.exit_price is None

    @property
    def instrument_key(self):
        return (self.underlier, self.strike, self.opt_type)

    def mtm_value(self, current_price: float) -> float:
        """Mark-to-market P&L on this position at current_price (unrealized)."""
        return (current_price - self.entry_price) * self.quantity_units

    def realized_pnl(self) -> float:
        if self.is_open:
            return 0.0
        gross = (self.exit_price - self.entry_price) * self.quantity_units
        return gross - self.entry_commission - self.exit_commission

    def holding_seconds(self) -> Optional[float]:
        if self.is_open or self.exit_time is None:
            return None
        return (self.exit_time - self.entry_time).total_seconds()
