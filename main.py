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

from utils.logging_setup import setup_logging, get_logger

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

if __name__ == "__main__":
    main(sys.argv[1:])
