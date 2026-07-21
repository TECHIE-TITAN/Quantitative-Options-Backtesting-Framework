"""
BacktestEngine: the event loop. This is the only module that knows how to
wire data -> strategy -> execution -> portfolio together. It is strategy-
agnostic: swapping ATMStraddleStrategy for any other Strategy subclass
requires zero changes here.

Loop, per trading day, per configured underlier:
    1. Build a DataFeed (loads futures + nearest-expiry option ticks).
    2. strategy.on_start(underlier)
    3. For every 1-second timestamp in the session:
         a. build StrategyContext
         b. orders = strategy.on_market_event(ctx)
         c. each order -> Account risk check -> ExecutionEngine.execute -> Fill -> Portfolio.apply_fill
         d. Portfolio.mark_to_market(timestamp, price_lookup)
    4. strategy.on_end_of_day(ctx) -> flatten orders -> execute -> portfolio
"""
from typing import List

import pandas as pd

from config.config import BacktestConfig
from data.loader import list_trading_days, filter_days, DayData
from data.feed import DataFeed
from execution.broker import ExecutionEngine
from portfolio.portfolio import Portfolio
from portfolio.account import Account
from strategies.base_strategy import Strategy, StrategyContext
from utils.logging_setup import get_logger

log = get_logger(__name__)


class BacktestEngine:
    def __init__(self, config: BacktestConfig, strategy: Strategy):
        self.config = config
        self.strategy = strategy
        self.portfolio = Portfolio(initial_capital=config.initial_capital)
        self.broker = ExecutionEngine(config.execution)
        self.account = Account(self.portfolio, config.execution)
        self.days_processed = 0
        self.days_skipped = 0

    def _price_lookup_factory(self, feeds_by_underlier):
        def _lookup(underlier, strike, opt_type):
            feed = feeds_by_underlier.get(underlier)
            if feed is None:
                return None
            return feed.option_price_asof(strike, opt_type, self._current_ts)
        return _lookup

    def run(self) -> Portfolio:
        days = list_trading_days(self.config.data_root)
        days = filter_days(days, self.config.start_date, self.config.end_date)
        if not days:
            log.warning("No trading days found under '%s' -- nothing to backtest.", self.config.data_root)
            return self.portfolio

        log.info("Running backtest over %d trading day(s) for %s", len(days), self.config.instruments)

        for day in days:
            self._run_day(day)

        log.info(
            "Backtest complete. days_processed=%d days_skipped=%d trades=%d rejected_orders=%d final_equity=%.2f",
            self.days_processed, self.days_skipped, len(self.portfolio.closed_positions),
            len(self.broker.rejected_orders),
            self.portfolio.snapshots[-1].equity if self.portfolio.snapshots else self.portfolio.cash,
        )
        return self.portfolio

    def _run_day(self, day: DayData):
        feeds = {}
        for underlier in self.config.instruments:
            feed = DataFeed(day, underlier, self.config.execution.max_price_staleness_sec)
            if feed.is_tradeable:
                feeds[underlier] = feed

        if not feeds:
            log.info("Skipping %s -- no tradeable data for configured instruments", day.trade_date)
            self.days_skipped += 1
            return

        self.days_processed += 1
        price_lookup = self._price_lookup_factory(feeds)

        for underlier in feeds:
            self.strategy.on_start(underlier)

        # Union timeline across underliers so every instrument gets ticked
        # at every second, even if session lengths differ slightly.
        timelines = [f.timeline() for f in feeds.values()]
        full_timeline = sorted(set().union(*[set(t) for t in timelines])) if timelines else []

        for ts in full_timeline:
            self._current_ts = ts
            for underlier, feed in feeds.items():
                ctx = StrategyContext(feed=feed, portfolio=self.portfolio, timestamp=ts, underlier=underlier)
                orders = self.strategy.on_market_event(ctx)
                self._route_orders(orders, feed)
            self.portfolio.mark_to_market(ts, price_lookup)

        # End of day: flatten everything, per instrument.
        eod_ts = full_timeline[-1] if full_timeline else pd.Timestamp(day.trade_date)
        self._current_ts = eod_ts
        for underlier, feed in feeds.items():
            ctx = StrategyContext(feed=feed, portfolio=self.portfolio, timestamp=eod_ts, underlier=underlier)
            eod_orders = self.strategy.on_end_of_day(ctx)
            self._route_orders(eod_orders, feed)
        self.portfolio.mark_to_market(eod_ts, price_lookup)

        log.info("Day %s complete. open_positions=%d equity=%.2f",
                  day.trade_date, len(self.portfolio.open_positions),
                  self.portfolio.snapshots[-1].equity)

    def _route_orders(self, orders: List, feed: DataFeed):
        for order in orders:
            ref_price = feed.option_price_asof(order.strike, order.opt_type, order.timestamp)
            if ref_price is None:
                log.warning("No reference price for order #%d, skipping risk check/execution", order.order_id)
                self.broker.rejected_orders.append(order)
                continue
            # Risk check only meaningfully applies to opening (BUY) orders.
            from execution.order import Side
            if order.side == Side.BUY and not self.account.pre_trade_check(order, ref_price):
                continue
            fill = self.broker.execute(order, feed)
            if fill is not None:
                self.portfolio.apply_fill(fill)
