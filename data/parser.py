"""
Turns raw tick CSVs (Date, Time, Price, Volume, Open Interest) into a
normalized DataFrame with a proper datetime index, sorted and de-duplicated.
Both options and futures files share this schema.
"""
from __future__ import annotations
import pandas as pd
from utils.logging_setup import get_logger

log = get_logger(__name__)

_EXPECTED_COLUMNS = ["Date", "Time", "Price", "Volume", "OpenInterest"]

_COLUMN_ALIASES = {
    "date": "Date",
    "time": "Time",
    "price": "Price",
    "volume": "Volume",
    "open interest": "OpenInterest",
    "openinterest": "OpenInterest",
    "oi": "OpenInterest",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for c in df.columns:
        key = c.strip().lower()
        if key in _COLUMN_ALIASES:
            rename[c] = _COLUMN_ALIASES[key]
    return df.rename(columns=rename)


def _read_tick_frame(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = _normalize_columns(df)
    required = {"Date", "Time", "Price"}
    if required.issubset(df.columns):
        return df

    # The attached NSE files are headerless rows in Date,Time,Price,Volume,OI order.
    df = pd.read_csv(path, header=None, names=_EXPECTED_COLUMNS)
    return _normalize_columns(df)


def load_tick_csv(path: str) -> pd.DataFrame:
    """
    Returns a DataFrame indexed by datetime, with columns:
    Price (float), Volume (int), OpenInterest (int)
    Sorted ascending, duplicate timestamps collapsed to the last tick.
    """
    try:
        df = _read_tick_frame(path)
    except Exception as e:
        log.error("Failed to read %s: %s", path, e)
        return pd.DataFrame(columns=["Price", "Volume", "OpenInterest"])
    required = {"Date", "Time", "Price"}
    if not required.issubset(df.columns):
        log.error("File %s missing required columns %s (has %s)", path, required, list(df.columns))
        return pd.DataFrame(columns=["Price", "Volume", "OpenInterest"])

    if "Volume" not in df.columns:
        df["Volume"] = 0
    if "OpenInterest" not in df.columns:
        df["OpenInterest"] = 0

    dt = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
        errors="coerce",
    )
    df = df.assign(datetime=dt)
    df = df.dropna(subset=["datetime", "Price"])
    df = df.set_index("datetime").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df[["Price", "Volume", "OpenInterest"]]
