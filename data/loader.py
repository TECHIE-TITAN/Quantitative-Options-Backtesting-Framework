"""
Filesystem discovery layer. Knows nothing about prices -- only about which
files exist for a given day/underlier, and how to pick the nearest expiry
and nearest futures series. This isolates every other module from the
directory-naming convention.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from utils.symbols import OptionContract, parse_day_folder, parse_futures_filename, parse_option_filename
from utils.logging_setup import get_logger

log = get_logger(__name__)

@dataclass
class DayData:
    trade_date: date
    folder: str
    options_dir: str
    futures_dir: str

def _find_child_dir(parent: str, predicate) -> str:
    if not os.path.isdir(parent):
        return parent
    for entry in os.listdir(parent):
        full = os.path.join(parent, entry)
        if os.path.isdir(full) and predicate(entry):
            return full
    return parent

def list_trading_days(data_root: str) -> List[DayData]:
    """Scan data_root for NSE_YYYYMMDD folders, sorted chronologically."""
    days = []
    if not os.path.isdir(data_root):
        log.warning("data_root '%s' does not exist", data_root)
        return days
    for entry in sorted(os.listdir(data_root)):
        full = os.path.join(data_root, entry)
        if not os.path.isdir(full):
            continue
        d = parse_day_folder(entry)
        if d is None:
            continue
        options_dir = _find_child_dir(full, lambda name: name.lower() == "options")
        futures_dir = _find_child_dir(full, lambda name: name.lower().startswith("futures"))
        days.append(DayData(
            trade_date=d,
            folder=full,
            options_dir=options_dir,
            futures_dir=futures_dir,
        ))
    return days

def filter_days(days: List[DayData], start: Optional[str], end: Optional[str]) -> List[DayData]:
    """start/end are 'YYYYMMDD' strings or None."""
    out = days
    if start:
        s = date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        out = [d for d in out if d.trade_date >= s]
    if end:
        e = date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        out = [d for d in out if d.trade_date <= e]
    return out

def list_option_contracts(day: DayData, underlier: str) -> List[OptionContract]:
    """All option contracts available for `underlier` on this trading day."""
    contracts = []
    if not os.path.isdir(day.options_dir):
        return contracts
    for fname in os.listdir(day.options_dir):
        c = parse_option_filename(fname, os.path.join(day.options_dir, fname))
        if c is not None and c.underlier == underlier:
            contracts.append(c)
    return contracts

def nearest_expiry(contracts: List[OptionContract], as_of: date) -> Optional[date]:
    """Nearest expiry that is on/after as_of. Falls back to the closest
    available expiry overall if nothing is >= as_of (defensive, shouldn't
    normally happen with clean data)."""
    future_expiries = sorted({c.expiry for c in contracts if c.expiry >= as_of})
    if future_expiries:
        return future_expiries[0]
    all_expiries = sorted({c.expiry for c in contracts})
    if not all_expiries:
        return None
    return min(all_expiries, key=lambda e: abs((e - as_of).days))

def get_futures_path(day: DayData, underlier: str, series: str = "I") -> Optional[str]:
    if not os.path.isdir(day.futures_dir):
        return None
    for fname in os.listdir(day.futures_dir):
        parsed = parse_futures_filename(fname)
        if parsed and parsed[0] == underlier and parsed[1] == series:
            return os.path.join(day.futures_dir, fname)
    return None

def contracts_for_nearest_expiry(day: DayData, underlier: str) -> Dict[tuple, OptionContract]:
    """Returns {(strike, opt_type): OptionContract} restricted to the
    nearest expiry available on this day for this underlier."""
    all_contracts = list_option_contracts(day, underlier)
    if not all_contracts:
        return {}
    expiry = nearest_expiry(all_contracts, day.trade_date)
    return {
        (c.strike, c.opt_type): c
        for c in all_contracts
        if c.expiry == expiry
    }
