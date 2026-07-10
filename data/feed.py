from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from data.loader import DayData, contracts_for_nearest_expiry, get_futures_path
from data.parser import load_tick_csv
from utils.logging_setup import get_logger

log = get_logger(__name__)

@dataclass
class MarketEvent:
    timestamp: pd.Timestamp
    underlier: str
    futures_price: float

class DataFeed:
    def __init__(self, day: DayData, underlier: str, max_staleness_sec: int = 300):
        self.day = day
        self.underlier = underlier
        self.max_staleness = timedelta(seconds=max_staleness_sec)

        fut_path = get_futures_path(day, underlier, series="I")
        self.futures = load_tick_csv(fut_path) if fut_path else pd.DataFrame(columns=["Price"])

        self.contracts = contracts_for_nearest_expiry(day, underlier)  # {(strike, type): OptionContract}
        self._option_ticks: Dict[Tuple[float, str], pd.DataFrame] = {}
        for key, contract in self.contracts.items():
            self._option_ticks[key] = load_tick_csv(contract.path)

        self.strikes: List[float] = sorted({k[0] for k in self.contracts.keys()})

        if self.futures.empty:
            log.warning("No futures data for %s on %s", underlier, day.trade_date)
        if not self.contracts:
            log.warning("No option contracts for %s on %s", underlier, day.trade_date)

    @property
    def is_tradeable(self) -> bool:
        return not self.futures.empty and bool(self.contracts)

    def timeline(self) -> pd.DatetimeIndex:
        """1-second resampled timeline spanning the futures session, per spec."""
        if self.futures.empty:
            return pd.DatetimeIndex([])
        start, end = self.futures.index.min(), self.futures.index.max()
        return pd.date_range(start=start, end=end, freq="1s")

    def futures_price_asof(self, ts: pd.Timestamp) -> Optional[float]:
        if self.futures.empty:
            return None
        idx = self.futures.index.searchsorted(ts, side="right") - 1
        if idx < 0:
            return None
        row_ts = self.futures.index[idx]
        if ts - row_ts > self.max_staleness:
            return None
        return float(self.futures.iloc[idx]["Price"])

    def option_price_asof(self, strike: float, opt_type: str, ts: pd.Timestamp) -> Optional[float]:
        key = (strike, opt_type)
        df = self._option_ticks.get(key)
        if df is None or df.empty:
            return None
        idx = df.index.searchsorted(ts, side="right") - 1
        if idx < 0:
            return None
        row_ts = df.index[idx]
        if ts - row_ts > self.max_staleness:
            return None
        return float(df.iloc[idx]["Price"])

    def atm_strike(self, futures_price: float) -> Optional[float]:
        if not self.strikes:
            return None
        return min(self.strikes, key=lambda k: abs(k - futures_price))

    def session_end(self) -> Optional[pd.Timestamp]:
        if self.futures.empty:
            return None
        return self.futures.index.max()
