"""
Exports the backtest's raw artifacts to CSV/JSON in the output directory:
trade log, portfolio (equity) history, rejected orders, and a performance
summary. This is the audit trail deliverable required by the spec.
"""
from __future__ import annotations
import json
import os
from typing import List

import pandas as pd

from portfolio.position import Position
from portfolio.portfolio import Portfolio
from analytics.metrics import snapshots_to_frame, full_summary
from utils.logging_setup import get_logger

log = get_logger(__name__)


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def export_trade_log(closed_positions: List[Position], output_dir: str) -> str:
    _ensure_dir(output_dir)
    rows = []
    for p in closed_positions:
        rows.append({
            "underlier": p.underlier,
            "strike": p.strike,
            "opt_type": p.opt_type,
            "quantity_units": p.quantity_units,
            "entry_time": p.entry_time,
            "entry_price": p.entry_price,
            "entry_commission": p.entry_commission,
            "exit_time": p.exit_time,
            "exit_price": p.exit_price,
            "exit_commission": p.exit_commission,
            "exit_reason": p.exit_reason,
            "realized_pnl": p.realized_pnl(),
            "holding_seconds": p.holding_seconds(),
        })
    df = pd.DataFrame(rows)
    path = os.path.join(output_dir, "trade_log.csv")
    df.to_csv(path, index=False)
    log.info("Wrote trade log (%d trades) -> %s", len(df), path)
    return path


def export_portfolio_history(portfolio: Portfolio, output_dir: str) -> str:
    _ensure_dir(output_dir)
    df = snapshots_to_frame(portfolio.snapshots)
    path = os.path.join(output_dir, "portfolio_history.csv")
    df.to_csv(path)
    log.info("Wrote portfolio history (%d snapshots) -> %s", len(df), path)
    return path


def export_rejected_orders(rejected_orders, output_dir: str) -> str:
    _ensure_dir(output_dir)
    rows = [{
        "order_id": o.order_id, "timestamp": o.timestamp, "underlier": o.underlier,
        "strike": o.strike, "opt_type": o.opt_type, "side": o.side.value,
        "quantity_lots": o.quantity_lots, "reason": o.reason,
    } for o in rejected_orders]
    df = pd.DataFrame(rows)
    path = os.path.join(output_dir, "rejected_orders.csv")
    df.to_csv(path, index=False)
    log.info("Wrote rejected orders (%d) -> %s", len(df), path)
    return path


def export_performance_summary(portfolio: Portfolio, initial_capital: float, output_dir: str) -> str:
    _ensure_dir(output_dir)
    summary = full_summary(portfolio, initial_capital)
    path = os.path.join(output_dir, "performance_summary.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    # also a flat CSV for spreadsheet users
    csv_path = os.path.join(output_dir, "performance_summary.csv")
    pd.DataFrame([summary]).to_csv(csv_path, index=False)
    log.info("Wrote performance summary -> %s", path)
    return path
