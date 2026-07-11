from dataclasses import dataclass
from datetime import date
from enum import Enum
import itertools

import pandas as pd

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"

_id_counter = itertools.count(1)

@dataclass
class Order:
    timestamp: pd.Timestamp
    underlier: str
    strike: float
    opt_type: str          # "CE" or "PE"
    side: Side
    quantity_lots: int
    reason: str = ""        # e.g. "ENTRY", "EXIT_STRIKE_ROLL", "EOD_FLATTEN"
    order_type: OrderType = OrderType.MARKET
    order_id: int = None

    def __post_init__(self):
        if self.order_id is None:
            self.order_id = next(_id_counter)

    @property
    def instrument_key(self):
        return (self.underlier, self.strike, self.opt_type)
