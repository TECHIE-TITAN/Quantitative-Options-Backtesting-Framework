from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd

from execution.order import Side
from execution.fills import Fill
from portfolio.position import Position
from utils.logging_setup import get_logger

log = get_logger(__name__)

InstrumentKey = Tuple[str, float, str]  # (underlier, strike, opt_type)

@dataclass
class PortfolioSnapshot:
    timestamp: pd.Timestamp
    cash: float
    realized_pnl_cum: float
    unrealized_pnl: float
    equity: float
    exposure: float
    n_open_positions: int

class Portfolio:
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.open_positions: Dict[InstrumentKey, Position] = {}
        self.closed_positions: List[Position] = []
        self.realized_pnl_cum: float = 0.0
        self.snapshots: List[PortfolioSnapshot] = []
        self._last_prices: Dict[InstrumentKey, float] = {}

    # ---- queries -----------------------------------------------------
    def has_open_position(self, underlier, strike, opt_type) -> bool:
        return (underlier, strike, opt_type) in self.open_positions

    def open_positions_for(self, underlier) -> List[Position]:
        return [p for k, p in self.open_positions.items() if k[0] == underlier]

    # ---- mutation (fills only) ----------------------------------------
    def apply_fill(self, fill: Fill) -> None:
        key = fill.order.instrument_key
        signed_qty = fill.quantity_units if fill.order.side == Side.BUY else -fill.quantity_units

        existing = self.open_positions.get(key)
        if existing is None:
            # New position
            pos = Position(
                underlier=fill.order.underlier,
                strike=fill.order.strike,
                opt_type=fill.order.opt_type,
                quantity_units=signed_qty,
                entry_price=fill.fill_price,
                entry_time=fill.timestamp,
                entry_commission=fill.commission,
                lot_size=fill.quantity_units // max(fill.order.quantity_lots, 1),
            )
            self.open_positions[key] = pos
            self.cash -= fill.gross_notional + fill.commission
            self._last_prices[key] = fill.fill_price
        else:
            # Closing (or reducing) an existing position -- reference strategy
            # always closes in full, but we handle partials safely too.
            closing_units = min(abs(existing.quantity_units), abs(signed_qty))
            is_full_close = closing_units >= abs(existing.quantity_units)

            self.cash += fill.fill_price * fill.quantity_units - fill.commission

            if is_full_close:
                # Set exit fields FIRST, then compute realized PnL against the
                # still-intact entry quantity_units, and only THEN zero it out.
                existing.exit_price = fill.fill_price
                existing.exit_time = fill.timestamp
                existing.exit_commission += fill.commission
                existing.exit_reason = fill.order.reason
                realized = existing.realized_pnl()
                self.realized_pnl_cum += realized
                self.closed_positions.append(existing)
                del self.open_positions[key]
                self._last_prices.pop(key, None)
                log.info(
                    "CLOSED %s %s%s realized_pnl=%.2f holding=%.0fs reason=%s",
                    existing.underlier, existing.strike, existing.opt_type,
                    realized, existing.holding_seconds() or 0.0, existing.exit_reason,
                )
            else:
                # Partial close: realize PnL on the closed portion, keep the
                # remainder open under the original entry price/time.
                closed_signed = -closing_units if signed_qty < 0 else closing_units
                partial_realized = (fill.fill_price - existing.entry_price) * closed_signed - fill.commission
                self.realized_pnl_cum += partial_realized
                existing.quantity_units += signed_qty
                self._last_prices[key] = fill.fill_price
                log.info(
                    "PARTIAL CLOSE %s %s%s realized_pnl=%.2f remaining_units=%d",
                    existing.underlier, existing.strike, existing.opt_type,
                    partial_realized, existing.quantity_units,
                )

    # ---- mark to market -------------------------------------------------
    def mark_to_market(self, timestamp: pd.Timestamp, price_lookup) -> PortfolioSnapshot:
        """
        price_lookup(underlier, strike, opt_type) -> Optional[float]
        Falls back to last known price if the feed has no fresh tick, so
        MTM doesn't spuriously jump to zero on illiquid strikes.
        """
        unrealized = 0.0
        exposure = 0.0
        for key, pos in self.open_positions.items():
            price = price_lookup(*key)
            if price is None:
                price = self._last_prices.get(key, pos.entry_price)
            else:
                self._last_prices[key] = price
            unrealized += pos.mtm_value(price)
            exposure += abs(price * pos.quantity_units)

        equity = self.cash + sum(
            self._last_prices.get(k, p.entry_price) * p.quantity_units
            for k, p in self.open_positions.items()
        )
        snap = PortfolioSnapshot(
            timestamp=timestamp,
            cash=self.cash,
            realized_pnl_cum=self.realized_pnl_cum,
            unrealized_pnl=unrealized,
            equity=equity,
            exposure=exposure,
            n_open_positions=len(self.open_positions),
        )
        self.snapshots.append(snap)
        return snap

    def total_pnl(self) -> float:
        last = self.snapshots[-1] if self.snapshots else None
        if last is None:
            return 0.0
        return last.realized_pnl_cum + last.unrealized_pnl
