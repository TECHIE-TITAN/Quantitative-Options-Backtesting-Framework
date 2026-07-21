"""
Usage:
    python main.py --data-root allData --output output \
        --instruments NIFTY BANKNIFTY --capital 1000000 \
        --start 20221101 --end 20221130

Adding a new strategy to the CLI only requires registering it in
STRATEGY_REGISTRY -- no engine changes needed.
"""
from __future__ import annotations
import argparse
import os
import sys

from config.config import BacktestConfig, ExecutionConfig
from engine import BacktestEngine

from utils.logging_setup import setup_logging, get_logger
from analytics.reports import (
    export_trade_log, export_portfolio_history, export_rejected_orders,
    export_performance_summary,
)
from analytics.metrics import full_summary

STRATEGY_REGISTRY = {
    
}

def _strategy_output_dir(base_output_dir: str, strategy_name: str) -> str:
    return os.path.join(base_output_dir, strategy_name)

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Event-driven options backtesting framework")
    p.add_argument("--data-root", default="allData", help="Path to the allData/ directory")
    p.add_argument("--output", default="output", help="Directory to write logs/reports/plots")
    p.add_argument("--instruments", nargs="+", default=["NIFTY", "BANKNIFTY"])
    p.add_argument("--capital", type=float, default=1_000_000.0)
    p.add_argument("--lots-per-trade", type=int, default=1)
    p.add_argument("--strategy", default="atm_straddle", choices=list(STRATEGY_REGISTRY.keys()))
    p.add_argument("--start", default=None, help="YYYYMMDD")
    p.add_argument("--end", default=None, help="YYYYMMDD")
    p.add_argument("--slippage-pct", type=float, default=0.001)
    p.add_argument("--brokerage-per-lot", type=float, default=20.0)
    p.add_argument("--transaction-cost-pct", type=float, default=0.0006)
    return p

def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    strategy_output_dir = _strategy_output_dir(args.output, args.strategy)

    setup_logging(strategy_output_dir)
    log = get_logger("main")

    exec_cfg = ExecutionConfig(
        slippage_pct=args.slippage_pct,
        brokerage_per_lot=args.brokerage_per_lot,
        transaction_cost_pct=args.transaction_cost_pct,
    )
    config = BacktestConfig(
        initial_capital=args.capital,
        instruments=args.instruments,
        data_root=args.data_root,
        output_dir=strategy_output_dir,
        lots_per_trade=args.lots_per_trade,
        execution=exec_cfg,
        start_date=args.start,
        end_date=args.end,
    )

    strategy = STRATEGY_REGISTRY[args.strategy](config)
    log.info("Starting backtest | strategy=%s | instruments=%s | capital=%.2f",
              args.strategy, args.instruments, args.capital)
    
    engine = BacktestEngine(config, strategy)
    portfolio = engine.run()

    export_trade_log(portfolio.closed_positions, strategy_output_dir)
    export_portfolio_history(portfolio, strategy_output_dir)
    export_rejected_orders(engine.broker.rejected_orders, strategy_output_dir)
    export_performance_summary(portfolio, config.initial_capital, strategy_output_dir)

    summary = full_summary(portfolio, config.initial_capital)
    log.info("=== PERFORMANCE SUMMARY ===")
    for k, v in summary.items():
        log.info("%-28s %s", k, v)

    return summary

if __name__ == "__main__":
    main(sys.argv[1:])
