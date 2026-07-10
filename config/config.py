"""
Central configuration for the backtesting framework.

Keeping all tunables in one place means strategies, execution and
portfolio code never hard-code numbers -- they all read from a
BacktestConfig instance that is threaded through the engine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ExecutionConfig:
    # Slippage applied against the trader: buys fill higher, sells fill lower.
    slippage_pct: float = 0.001            # 0.10% of price
    # Flat brokerage charged per executed lot (₹), applied on both entry & exit.
    brokerage_per_lot: float = 20.0
    # Proxy for STT + exchange transaction charges + GST, as % of trade notional.
    transaction_cost_pct: float = 0.0006
    # Lot size per underlier (NSE F&O contract multiplier).
    lot_size: Dict[str, int] = field(default_factory=lambda: {
        "NIFTY": 50,
        "BANKNIFTY": 15,
        "FINNIFTY": 40,
    })
    # Max allowed staleness (seconds) when looking up the last traded price
    # for an option before we consider it "no data" and skip the fill.
    max_price_staleness_sec: int = 300


@dataclass
class BacktestConfig:
    initial_capital: float = 1_000_000.0
    instruments: List[str] = field(default_factory=lambda: ["NIFTY", "BANKNIFTY"])
    data_root: str = "allData"
    output_dir: str = "output"
    # Number of lots traded per leg, per signal.
    lots_per_trade: int = 1
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    # Restrict backtest to a date range (YYYYMMDD strings), None = all available.
    start_date: str | None = None
    end_date: str | None = None
