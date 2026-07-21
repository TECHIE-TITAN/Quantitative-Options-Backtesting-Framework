"""
Pure functions that compute performance analytics from a Portfolio's
snapshots and closed positions. No side effects, no I/O -- reports.py and
plots.py consume these.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List
import numpy as np
import pandas as pd

from portfolio.position import Position
from portfolio.portfolio import PortfolioSnapshot

TRADING_SECONDS_PER_YEAR = 252 * 6.25 * 3600  # ~252 sessions, 6h15m/session


def snapshots_to_frame(snapshots: List[PortfolioSnapshot]) -> pd.DataFrame:
    if not snapshots:
        return pd.DataFrame(columns=[
            "timestamp", "cash", "realized_pnl_cum", "unrealized_pnl",
            "equity", "exposure", "n_open_positions",
        ])
    df = pd.DataFrame([asdict(s) for s in snapshots])
    df = df.set_index("timestamp").sort_index()
    return df


def daily_pnl(equity_df: pd.DataFrame) -> pd.Series:
    if equity_df.empty:
        return pd.Series(dtype=float)
    daily_last = equity_df["equity"].resample("1D").last().dropna()
    return daily_last.diff().fillna(daily_last - daily_last.iloc[0] if len(daily_last) else 0)


def drawdown_series(equity_df: pd.DataFrame) -> pd.Series:
    if equity_df.empty:
        return pd.Series(dtype=float)
    running_max = equity_df["equity"].cummax()
    return (equity_df["equity"] - running_max) / running_max.replace(0, np.nan)


def max_drawdown(equity_df: pd.DataFrame) -> float:
    dd = drawdown_series(equity_df)
    return float(dd.min()) if not dd.empty else 0.0


def sharpe_ratio(daily_returns: pd.Series, risk_free: float = 0.0, periods_per_year: int = 252) -> float:
    if daily_returns.empty or daily_returns.std(ddof=0) == 0:
        return 0.0
    excess = daily_returns - risk_free / periods_per_year
    return float(np.sqrt(periods_per_year) * excess.mean() / daily_returns.std(ddof=0))


def sortino_ratio(daily_returns: pd.Series, risk_free: float = 0.0, periods_per_year: int = 252) -> float:
    if daily_returns.empty:
        return 0.0
    excess = daily_returns - risk_free / periods_per_year
    downside = excess[excess < 0]
    downside_std = downside.std(ddof=0)
    if downside_std == 0 or np.isnan(downside_std):
        return 0.0
    return float(np.sqrt(periods_per_year) * excess.mean() / downside_std)


def profit_factor(closed: List[Position]) -> float:
    gains = sum(p.realized_pnl() for p in closed if p.realized_pnl() > 0)
    losses = -sum(p.realized_pnl() for p in closed if p.realized_pnl() < 0)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def trade_stats(closed: List[Position]) -> dict:
    if not closed:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
            "win_rate": 0.0, "avg_profit_per_trade": 0.0, "avg_loss_per_trade": 0.0,
            "avg_holding_seconds": 0.0, "profit_factor": 0.0,
        }
    pnls = [p.realized_pnl() for p in closed]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    holdings = [p.holding_seconds() for p in closed if p.holding_seconds() is not None]
    return {
        "total_trades": len(closed),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": len(wins) / len(closed) if closed else 0.0,
        "avg_profit_per_trade": float(np.mean(wins)) if wins else 0.0,
        "avg_loss_per_trade": float(np.mean(losses)) if losses else 0.0,
        "avg_holding_seconds": float(np.mean(holdings)) if holdings else 0.0,
        "profit_factor": profit_factor(closed),
    }


def turnover(closed: List[Position]) -> float:
    """Sum of absolute notional traded (entry + exit legs)."""
    total = 0.0
    for p in closed:
        total += abs(p.entry_price * p.quantity_units)
        if p.exit_price is not None:
            total += abs(p.exit_price * p.quantity_units)
    return total


def volatility_of_returns(daily_returns: pd.Series, periods_per_year: int = 252) -> float:
    if daily_returns.empty:
        return 0.0
    return float(daily_returns.std(ddof=0) * np.sqrt(periods_per_year))


def full_summary(portfolio, initial_capital: float) -> dict:
    equity_df = snapshots_to_frame(portfolio.snapshots)
    dpnl = daily_pnl(equity_df)
    daily_ret = (dpnl / initial_capital) if initial_capital else dpnl * 0

    summary = {
        "initial_capital": initial_capital,
        "final_equity": float(equity_df["equity"].iloc[-1]) if not equity_df.empty else initial_capital,
        "total_realized_pnl": float(portfolio.realized_pnl_cum),
        "total_unrealized_pnl": float(equity_df["unrealized_pnl"].iloc[-1]) if not equity_df.empty else 0.0,
        "cumulative_pnl": portfolio.total_pnl(),
        "max_drawdown_pct": max_drawdown(equity_df) * 100,
        "sharpe_ratio": sharpe_ratio(daily_ret),
        "sortino_ratio": sortino_ratio(daily_ret),
        "volatility_annualized_pct": volatility_of_returns(daily_ret) * 100,
        "turnover": turnover(portfolio.closed_positions),
    }
    summary.update(trade_stats(portfolio.closed_positions))
    return summary
