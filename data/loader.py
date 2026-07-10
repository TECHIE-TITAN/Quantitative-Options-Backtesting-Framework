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

from utils.symbols import parse_day_folder
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