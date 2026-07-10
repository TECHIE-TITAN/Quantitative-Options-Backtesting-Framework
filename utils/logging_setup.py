"""
Shared logging configuration. All modules pull loggers via get_logger(__name__)
so log output is consistent and can be redirected to a file per backtest run.
"""
from __future__ import annotations
import logging
import os
import sys

_CONFIGURED = False


def setup_logging(output_dir: str = "output", level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "backtest.log")

    root = logging.getLogger()
    root.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_path, mode="w")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
