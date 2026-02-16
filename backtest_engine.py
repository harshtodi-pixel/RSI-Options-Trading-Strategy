"""
Backtesting Engine for RSI Options Strategy

Strategy: Sell ATM options when RSI crosses above 70.
Entry: Staggered at +5%, +10%, +15% from base price.
Exit: SL 20% / TP 10% / EOD 2:30 PM.
Intraday only: signals expire at end of day.
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import logging
from typing import Dict, List, Optional
import config
import os

# ============================================
# LOGGING SETUP
# ============================================
# Console logger for progress
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# RSI CALCULATOR
# ============================================
class RSICalculator:
    """Calculate RSI indicator."""

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Standard RSI using rolling mean of gains/losses.
        Returns a Series of RSI values (NaN for first `period` rows).
        """
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


# ============================================
# POSITION PART (one leg of staggered entry)
# ============================================
class PositionPart:
    """One part of a staggered position (33.33% each)."""

    def __init__(self, part_num: int, entry_time, entry_price: float, size_pct: float):
        self.part_num = part_num       # 1, 2, or 3
        self.entry_time = entry_time   # datetime of fill
        self.entry_price = entry_price # price at which we sold
        self.size_pct = size_pct       # 33.33 or 33.34


# ============================================
# TRADE (complete trade cycle)
# ============================================
class Trade:
    """
    A complete trade cycle with staggered entries.
    
    Lifecycle:
      1. RSI crosses 70 -> signal generated, base_price set
      2. Entry levels calculated: +5%, +10%, +15%
      3. Parts filled as price reaches each level (same day only)
      4. Exit on SL / TP / EOD (applied to entire position)
    """

    def __init__(self, signal_time, base_price: float, option_type: str,
                 strike: float, expiry_type: str, expiry_code: int, instrument: str):
        # Signal info
        self.signal_time = signal_time
        self.base_price = base_price
        self.option_type = option_type
        self.strike = strike
        self.expiry_type = expiry_type
        self.expiry_code = expiry_code
        self.instrument = instrument

        # Entry levels (sell at these prices)
        self.entry_level_1 = base_price * (1 + config.ENTRY_LEVEL_1_PCT / 100)
        self.entry_level_2 = base_price * (1 + config.ENTRY_LEVEL_2_PCT / 100)
        self.entry_level_3 = base_price * (1 + config.ENTRY_LEVEL_3_PCT / 100)

        # Parts tracking
        self.parts: List[PositionPart] = []
        self.part1_filled = False
        self.part2_filled = False
        self.part3_filled = False

        # Exit info
        self.exit_time = None
        self.exit_price = None
        self.exit_reason = None
        self.status = 'WAITING_ENTRY'

        # P&L
        self.total_pnl = 0.0
        self.total_pnl_pct = 0.0

    def add_entry(self, part_num: int, entry_time, entry_price: float, size_pct: float):
        """Fill one part of the staggered entry."""
        part = PositionPart(part_num, entry_time, entry_price, size_pct)
        self.parts.append(part)

        if part_num == 1:
            self.part1_filled = True
        elif part_num == 2:
            self.part2_filled = True
        elif part_num == 3:
            self.part3_filled = True

        # Update status
        self.status = 'FULL_POSITION' if len(self.parts) == 3 else 'PARTIAL_POSITION'

    def get_avg_entry_price(self) -> Optional[float]:
        """Weighted average entry price across filled parts."""
        if not self.parts:
            return None
        total_weighted = sum(p.entry_price * p.size_pct for p in self.parts)
        total_weight = sum(p.size_pct for p in self.parts)
        return total_weighted / total_weight if total_weight > 0 else None

    def has_position(self) -> bool:
        """True if at least one part is filled."""
        return len(self.parts) > 0

    def close_trade(self, exit_time, exit_price: float, exit_reason: str):
        """Close entire position. P&L = avg_entry - exit (selling options)."""
        if not self.parts:
            return
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        self.status = 'CLOSED'

        avg = self.get_avg_entry_price()
        # Selling options: profit when price drops
        self.total_pnl = avg - exit_price
        self.total_pnl_pct = (self.total_pnl / avg) * 100 if avg else 0

    def get_money_pnl(self) -> float:
        """Actual money P&L = option price P&L * lot size."""
        lot_size = config.LOT_SIZE.get(self.instrument, 1)
        return self.total_pnl * lot_size

    def to_dict(self) -> Dict:
        """Flat dictionary for CSV export."""
        avg = self.get_avg_entry_price()
        lot_size = config.LOT_SIZE.get(self.instrument, 1)
        return {
            'instrument': self.instrument,
            'option_type': self.option_type,
            'strike': self.strike,
            'expiry_type': self.expiry_type,
            'expiry_code': self.expiry_code,
            'signal_time': self.signal_time,
            'base_price': self.base_price,
            'entry_level_1': self.entry_level_1,
            'entry_level_2': self.entry_level_2,
            'entry_level_3': self.entry_level_3,
            'parts_filled': len(self.parts),
            'part1_time': self.parts[0].entry_time if len(self.parts) > 0 else None,
            'part1_price': self.parts[0].entry_price if len(self.parts) > 0 else None,
            'part2_time': self.parts[1].entry_time if len(self.parts) > 1 else None,
            'part2_price': self.parts[1].entry_price if len(self.parts) > 1 else None,
            'part3_time': self.parts[2].entry_time if len(self.parts) > 2 else None,
            'part3_price': self.parts[2].entry_price if len(self.parts) > 2 else None,
            'avg_entry_price': avg,
            'exit_time': self.exit_time,
            'exit_price': self.exit_price,
            'exit_reason': self.exit_reason,
            'pnl': self.total_pnl,
            'pnl_pct': self.total_pnl_pct,
            'money_pnl': self.total_pnl * lot_size,
            'lot_size': lot_size,
            'status': self.status,
        }


# ============================================
# BACKTEST ENGINE
# ============================================
class BacktestEngine:
    """
    Main backtesting engine.
    
    Data assumptions (from schema):
      - expiry_code: 1=nearest, 2=next, 3=far -> we only use 1
      - moneyness: 'ATM' -> we only use ATM
      - atm_strike: already calculated per minute
      - Each row is one minute of one option contract
    """

    def __init__(self, instrument: str, data_path: str):
        self.instrument = instrument
        self.data_path = data_path
        self.df = None
        self.trades: List[Trade] = []
        self.initial_capital = config.BACKTEST_INITIAL_CAPITAL

        # Strategy params from config
        self.rsi_period = config.STRATEGY_CONFIG['rsi_length']
        self.rsi_threshold = 70
        self.stop_loss_pct = config.STRATEGY_CONFIG['stop_loss_pct']
        self.target_pct = config.STRATEGY_CONFIG['target_pct']

        # Trading hours
        self.entry_time = datetime.strptime(config.TRADING_START_TIME, '%H:%M').time()
        self.exit_time = datetime.strptime(config.TRADING_END_TIME, '%H:%M').time()

        logger.info(f"Initialized backtest for {instrument}")

    # ------------------------------------------
    # DATA LOADING
    # ------------------------------------------
    def load_data(self):
        """Load parquet, filter to backtest period + nearest weekly expiry."""
        logger.info(f"Loading {self.data_path}...")
        self.df = pd.read_parquet(self.data_path)

        # Parse datetime
        self.df['datetime'] = pd.to_datetime(self.df['datetime'])

        # Filter: date range
        start = pd.to_datetime(config.BACKTEST_START_DATE).tz_localize('Asia/Kolkata')
        end = pd.to_datetime(config.BACKTEST_END_DATE).tz_localize('Asia/Kolkata') + pd.Timedelta(days=1)
        self.df = self.df[(self.df['datetime'] >= start) & (self.df['datetime'] < end)]

        # Filter: nearest weekly expiry only (expiry_type=WEEK, expiry_code=1)
        # Monthly contracts also have expiry_code=1, so we must filter both.
        self.df = self.df[(self.df['expiry_code'] == 1) & (self.df['expiry_type'] == 'WEEK')]

        # NOTE: We do NOT filter by moneyness here.
        # We need all strikes so we can track a contract's price
        # even after it stops being ATM (spot moved).
        # ATM filter is applied only during signal detection.

        # Sort chronologically
        self.df = self.df.sort_values('datetime').reset_index(drop=True)

        # Add helper columns
        self.df['date'] = self.df['datetime'].dt.date
        self.df['time_only'] = self.df['datetime'].dt.time

        logger.info(f"Loaded {len(self.df):,} rows | "
                     f"{self.df['date'].nunique()} trading days | "
                     f"Range: {self.df['datetime'].min()} to {self.df['datetime'].max()}")

    # ------------------------------------------
    # CALCULATE RSI PER CONTRACT
    # ------------------------------------------
    def calculate_rsi(self):
        """
        Calculate RSI for each unique contract.
        
        Contract = strike + option_type + expiry_type + expiry_code
        (Weekly and monthly contracts at same strike are different)
        
        RSI is continuous per contract across days until expiry.
        After weekly expiry, new contracts start with fresh RSI.
        First 14 candles of each contract will have NaN RSI.
        """
        logger.info("Calculating RSI per contract...")

        # Group by unique contract
        groups = self.df.groupby(['strike', 'option_type', 'expiry_type', 'expiry_code'])

        rsi_list = []
        for _, group in groups:
            group = group.sort_values('datetime')
            rsi = RSICalculator.calculate_rsi(group['close'], self.rsi_period)
            rsi_list.append(rsi)

        self.df['rsi'] = pd.concat(rsi_list).sort_index()

        # Previous RSI for crossover detection
        self.df['rsi_prev'] = self.df.groupby(['strike', 'option_type', 'expiry_type', 'expiry_code'])['rsi'].shift(1)

        logger.info(f"RSI calculated | {self.df['rsi'].notna().sum():,} non-null values")

    # ------------------------------------------
    # HELPERS FOR PER-TRADE LOGIC
    # ------------------------------------------
    def _get_contract_candle(self, trade: Trade, minute_data):
        """Look up the specific contract's candle (no moneyness filter)."""
        match = minute_data[
            (minute_data['strike'] == trade.strike) &
            (minute_data['option_type'] == trade.option_type) &
            (minute_data['expiry_type'] == trade.expiry_type) &
            (minute_data['expiry_code'] == trade.expiry_code)
        ]
        return match.iloc[0] if len(match) > 0 else None

    def _check_staggered_entry(self, trade: Trade, minute_data, t) -> List[str]:
        """
        Check if any staggered entry levels are hit.
        Returns list of event messages for logging.
        """
        events = []
        candle = self._get_contract_candle(trade, minute_data)
        if candle is None:
            return events

        candle_high = candle['high']

        # Part 1: +5%
        if not trade.part1_filled and candle_high >= trade.entry_level_1:
            trade.add_entry(1, t, trade.entry_level_1, 33.33)
            events.append(f"ENTRY Part1: high={candle_high:.2f} >= L1={trade.entry_level_1:.2f} | filled @ {trade.entry_level_1:.2f}")

        # Part 2: +10% (only after part 1)
        if trade.part1_filled and not trade.part2_filled \
           and candle_high >= trade.entry_level_2:
            trade.add_entry(2, t, trade.entry_level_2, 33.33)
            events.append(f"ENTRY Part2: high={candle_high:.2f} >= L2={trade.entry_level_2:.2f} | filled @ {trade.entry_level_2:.2f}")

        # Part 3: +15% (only after part 2)
        if trade.part2_filled and not trade.part3_filled \
           and candle_high >= trade.entry_level_3:
            trade.add_entry(3, t, trade.entry_level_3, 33.34)
            events.append(f"ENTRY Part3: high={candle_high:.2f} >= L3={trade.entry_level_3:.2f} | filled @ {trade.entry_level_3:.2f}")

        return events

    def _check_exit(self, trade: Trade, minute_data, day_data, t, is_exit_time: bool):
        """
        Check SL/TP/EOD exit for this trade.
        Returns (closed: bool, event_msg: str or None).
        """
        if not trade.has_position():
            return False, None

        candle = self._get_contract_candle(trade, minute_data)

        if candle is None:
            # No data at this minute. If exit time, find last available candle.
            if is_exit_time:
                last_candle_df = day_data[
                    (day_data['strike'] == trade.strike) &
                    (day_data['option_type'] == trade.option_type) &
                    (day_data['expiry_type'] == trade.expiry_type) &
                    (day_data['expiry_code'] == trade.expiry_code) &
                    (day_data['time_only'] <= self.exit_time)
                ]
                if len(last_candle_df) > 0:
                    lc = last_candle_df.iloc[-1]
                    trade.close_trade(t, lc['close'], 'EOD')
                    msg = f"EXIT EOD (no data at exit time, used last candle close={lc['close']:.2f})"
                else:
                    trade.close_trade(t, trade.get_avg_entry_price(), 'EOD')
                    msg = f"EXIT EOD (no data, closed flat at avg_entry={trade.get_avg_entry_price():.2f})"
                self.trades.append(trade)
                return True, msg
            return False, None

        avg_entry = trade.get_avg_entry_price()
        if avg_entry is None:
            return False, None

        # Exact SL and TP price levels (fixed 20% SL, 10% TP)
        sl_price = avg_entry * (1 + self.stop_loss_pct / 100)
        tp_price = avg_entry * (1 - self.target_pct / 100)

        exit_reason = None
        exit_price = None
        msg = None

        # Check SL: did candle high breach the SL level?
        if candle['high'] >= sl_price:
            exit_reason = 'STOP_LOSS'
            exit_price = sl_price
            msg = (f"EXIT STOP_LOSS: high={candle['high']:.2f} >= SL={sl_price:.2f} | "
                   f"avg_entry={avg_entry:.2f} | exit @ {sl_price:.2f} | pnl=-20%")
        # Check TP: did candle low breach the TP level?
        elif candle['low'] <= tp_price:
            exit_reason = 'TARGET'
            exit_price = tp_price
            msg = (f"EXIT TARGET: low={candle['low']:.2f} <= TP={tp_price:.2f} | "
                   f"avg_entry={avg_entry:.2f} | exit @ {tp_price:.2f} | pnl=+10%")
        # EOD: at exit time, force close at candle close
        elif is_exit_time:
            exit_reason = 'EOD'
            exit_price = candle['close']
            pnl_pct = ((avg_entry - exit_price) / avg_entry) * 100
            msg = (f"EXIT EOD: close={candle['close']:.2f} | "
                   f"avg_entry={avg_entry:.2f} | pnl={pnl_pct:+.2f}%")

        if exit_reason:
            trade.close_trade(t, exit_price, exit_reason)
            self.trades.append(trade)
            return True, msg

        return False, None

    def _eod_close_trade(self, trade: Trade, day_data, date) -> str:
        """Safety net: close a trade at EOD. Returns event message."""
        if trade.has_position():
            contract_data = day_data[
                (day_data['strike'] == trade.strike) &
                (day_data['option_type'] == trade.option_type) &
                (day_data['expiry_type'] == trade.expiry_type) &
                (day_data['expiry_code'] == trade.expiry_code) &
                (day_data['time_only'] <= self.exit_time)
            ]
            if len(contract_data) > 0:
                last_row = contract_data.iloc[-1]
                trade.close_trade(last_row['datetime'], last_row['close'], 'EOD')
                avg = trade.get_avg_entry_price()
                pnl_pct = ((avg - last_row['close']) / avg) * 100 if avg else 0
                msg = f"EXIT EOD (safety net): close={last_row['close']:.2f} | pnl={pnl_pct:+.2f}%"
            else:
                trade.close_trade(
                    pd.Timestamp(f"{date} {self.exit_time}"),
                    trade.get_avg_entry_price(), 'EOD'
                )
                msg = "EXIT EOD (safety net, no data, closed flat)"
            self.trades.append(trade)
            return msg
        # No position was taken -- just discard the observation
        return "EOD: observation expired (no entry taken)"

    def _get_track_status(self, trade: Optional[Trade], minute_data) -> str:
        """Get a short status string for a CE or PE track."""
        if trade is None:
            return "idle"

        opt = trade.option_type
        strike = int(trade.strike)

        # Get current candle for the observed contract
        candle = self._get_contract_candle(trade, minute_data)
        price_str = f"close={candle['close']:.2f} high={candle['high']:.2f} low={candle['low']:.2f}" if candle is not None else "no data"

        if trade.status == 'WAITING_ENTRY':
            return (f"observing {strike} {opt} | {price_str} | "
                    f"waiting L1={trade.entry_level_1:.2f} (need high >= L1)")
        elif trade.status == 'PARTIAL_POSITION':
            avg = trade.get_avg_entry_price()
            sl = avg * 1.2
            tp = avg * 0.9
            return (f"in position {strike} {opt} ({len(trade.parts)}/3) | {price_str} | "
                    f"avg={avg:.2f} SL={sl:.2f} TP={tp:.2f}")
        elif trade.status == 'FULL_POSITION':
            avg = trade.get_avg_entry_price()
            sl = avg * 1.2
            tp = avg * 0.9
            return (f"in position {strike} {opt} (3/3) | {price_str} | "
                    f"avg={avg:.2f} SL={sl:.2f} TP={tp:.2f}")
        return trade.status

    # ------------------------------------------
    # MAIN BACKTEST LOOP
    # ------------------------------------------
    def run_backtest(self):
        """
        Run the full backtest.
        
        CE and PE are tracked independently:
          - Can observe/trade one CE and one PE at the same time
          - Cannot have two CEs or two PEs active simultaneously
          - Both reset at end of day
        
        Writes a detailed minute-by-minute log for manual verification.
        """
        logger.info("=" * 60)
        logger.info(f"BACKTEST: {self.instrument}")
        logger.info("=" * 60)

        self.load_data()
        self.calculate_rsi()

        # Independent tracks for CE and PE (can run simultaneously)
        active_ce: Optional[Trade] = None
        active_pe: Optional[Trade] = None
        dates = self.df['date'].unique()

        # Open detailed log file
        log_path = f"backtest_detailed_{self.instrument}.log"
        dlog = open(log_path, 'w')
        dlog.write(f"{'=' * 100}\n")
        dlog.write(f"DETAILED BACKTEST LOG: {self.instrument}\n")
        dlog.write(f"Period: {config.BACKTEST_START_DATE} to {config.BACKTEST_END_DATE}\n")
        dlog.write(f"RSI: {self.rsi_period} | SL: {self.stop_loss_pct}% | TP: {self.target_pct}%\n")
        dlog.write(f"Entry levels: +{config.ENTRY_LEVEL_1_PCT}% / +{config.ENTRY_LEVEL_2_PCT}% / +{config.ENTRY_LEVEL_3_PCT}%\n")
        dlog.write(f"Hours: {config.TRADING_START_TIME} - {config.TRADING_END_TIME}\n")
        dlog.write(f"{'=' * 100}\n\n")

        logger.info(f"Processing {len(dates)} trading days...")

        for day_num, date in enumerate(dates, 1):
            if day_num % 50 == 0:
                logger.info(f"Day {day_num}/{len(dates)} | Trades so far: {len(self.trades)}")

            day_data = self.df[self.df['date'] == date]
            minutes = day_data['datetime'].unique()

            # Day header in log
            dlog.write(f"\n{'=' * 100}\n")
            dlog.write(f"  DATE: {date}\n")
            dlog.write(f"{'=' * 100}\n")

            for minute in minutes:
                t = pd.Timestamp(minute)
                t_only = t.time()

                # Skip if before trading start
                if t_only < self.entry_time:
                    continue
                # Skip if AFTER exit time (we still process the exit_time minute)
                if t_only > self.exit_time:
                    continue

                is_exit_time = (t_only >= self.exit_time)
                minute_data = day_data[day_data['datetime'] == minute]

                # Collect events for this minute
                events = []

                # Get ATM RSI info for logging
                atm_data = minute_data[minute_data['moneyness'] == 'ATM']
                ce_rsi_str = "--"
                pe_rsi_str = "--"
                ce_atm_strike = "--"
                pe_atm_strike = "--"
                for _, row in atm_data.iterrows():
                    rsi_val = f"{row['rsi']:.2f}" if pd.notna(row['rsi']) else "NaN"
                    if row['option_type'] == 'CE':
                        ce_rsi_str = rsi_val
                        ce_atm_strike = str(int(row['strike']))
                    elif row['option_type'] == 'PE':
                        pe_rsi_str = rsi_val
                        pe_atm_strike = str(int(row['strike']))

                # ---- CHECK SIGNALS (ATM only, not at exit time) ----
                if not is_exit_time:
                    for _, row in atm_data.iterrows():
                        if pd.isna(row['rsi']) or pd.isna(row['rsi_prev']):
                            continue

                        # RSI crossover: prev <= 70 and current > 70
                        if row['rsi_prev'] <= self.rsi_threshold and row['rsi'] > self.rsi_threshold:
                            opt_type = row['option_type']

                            if opt_type == 'CE' and active_ce is None:
                                active_ce = Trade(
                                    signal_time=t,
                                    base_price=row['close'],
                                    option_type='CE',
                                    strike=row['strike'],
                                    expiry_type=row['expiry_type'],
                                    expiry_code=row['expiry_code'],
                                    instrument=self.instrument,
                                )
                                events.append(
                                    f"CE SIGNAL: RSI crossed 70 ({row['rsi_prev']:.2f} -> {row['rsi']:.2f}) "
                                    f"on {int(row['strike'])} CE | base={row['close']:.2f} | "
                                    f"L1={active_ce.entry_level_1:.2f} L2={active_ce.entry_level_2:.2f} L3={active_ce.entry_level_3:.2f}"
                                )

                            elif opt_type == 'PE' and active_pe is None:
                                active_pe = Trade(
                                    signal_time=t,
                                    base_price=row['close'],
                                    option_type='PE',
                                    strike=row['strike'],
                                    expiry_type=row['expiry_type'],
                                    expiry_code=row['expiry_code'],
                                    instrument=self.instrument,
                                )
                                events.append(
                                    f"PE SIGNAL: RSI crossed 70 ({row['rsi_prev']:.2f} -> {row['rsi']:.2f}) "
                                    f"on {int(row['strike'])} PE | base={row['close']:.2f} | "
                                    f"L1={active_pe.entry_level_1:.2f} L2={active_pe.entry_level_2:.2f} L3={active_pe.entry_level_3:.2f}"
                                )

                # ---- STAGGERED ENTRY (not at exit time) ----
                if not is_exit_time:
                    if active_ce and active_ce.status in ['WAITING_ENTRY', 'PARTIAL_POSITION']:
                        entry_events = self._check_staggered_entry(active_ce, minute_data, t)
                        events.extend([f"CE {e}" for e in entry_events])
                    if active_pe and active_pe.status in ['WAITING_ENTRY', 'PARTIAL_POSITION']:
                        entry_events = self._check_staggered_entry(active_pe, minute_data, t)
                        events.extend([f"PE {e}" for e in entry_events])

                # ---- EXIT MANAGEMENT (CE and PE independently) ----
                if active_ce:
                    closed, exit_msg = self._check_exit(active_ce, minute_data, day_data, t, is_exit_time)
                    if closed:
                        events.append(f"CE {exit_msg}")
                        active_ce = None
                if active_pe:
                    closed, exit_msg = self._check_exit(active_pe, minute_data, day_data, t, is_exit_time)
                    if closed:
                        events.append(f"PE {exit_msg}")
                        active_pe = None

                # ---- WRITE LOG LINE ----
                time_str = t_only.strftime('%H:%M')
                ce_status = self._get_track_status(active_ce, minute_data)
                pe_status = self._get_track_status(active_pe, minute_data)

                dlog.write(
                    f"[{time_str}] "
                    f"ATM CE {ce_atm_strike} RSI={ce_rsi_str} | "
                    f"ATM PE {pe_atm_strike} RSI={pe_rsi_str} | "
                    f"CE: {ce_status} | PE: {pe_status}\n"
                )
                for event in events:
                    dlog.write(f"         >>> {event}\n")

            # ---- END OF DAY: reset both tracks ----
            if active_ce:
                msg = self._eod_close_trade(active_ce, day_data, date)
                dlog.write(f"         >>> CE {msg}\n")
                active_ce = None
            if active_pe:
                msg = self._eod_close_trade(active_pe, day_data, date)
                dlog.write(f"         >>> PE {msg}\n")
                active_pe = None

        dlog.write(f"\n{'=' * 100}\n")
        dlog.write(f"END OF LOG | Total trades: {len(self.trades)}\n")
        dlog.write(f"{'=' * 100}\n")
        dlog.close()

        logger.info(f"Backtest done. Total trades: {len(self.trades)}")
        logger.info(f"Detailed log saved to {log_path}")

    # ------------------------------------------
    # REPORT GENERATION
    # ------------------------------------------
    def generate_report(self) -> Dict:
        """Build a report dict from completed trades."""
        if not self.trades:
            logger.warning("No trades to report")
            return {}

        trades_df = pd.DataFrame([t.to_dict() for t in self.trades])

        # Only trades that actually entered
        trades_df = trades_df[trades_df['parts_filled'] > 0].copy()
        if len(trades_df) == 0:
            logger.warning("No trades with entries")
            return {}

        total = len(trades_df)
        wins = len(trades_df[trades_df['pnl'] > 0])
        losses = len(trades_df[trades_df['pnl'] < 0])
        total_pnl = trades_df['pnl'].sum()

        # Actual money P&L (option price P&L * lot size)
        lot_size = config.LOT_SIZE.get(self.instrument, 1)
        total_money_pnl = trades_df['money_pnl'].sum()

        report = {
            'instrument': self.instrument,
            'lot_size': lot_size,
            'period': f"{config.BACKTEST_START_DATE} to {config.BACKTEST_END_DATE}",
            'initial_capital': self.initial_capital,
            'final_capital': self.initial_capital + total_money_pnl,
            'total_pnl': total_pnl,
            'total_money_pnl': total_money_pnl,
            'return_pct': (total_money_pnl / self.initial_capital) * 100,
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / total) * 100 if total else 0,
            'avg_pnl': trades_df['pnl'].mean(),
            'avg_money_pnl': trades_df['money_pnl'].mean(),
            'avg_win': trades_df[trades_df['pnl'] > 0]['money_pnl'].mean() if wins else 0,
            'avg_loss': trades_df[trades_df['pnl'] < 0]['money_pnl'].mean() if losses else 0,
            'max_win': trades_df['money_pnl'].max(),
            'max_loss': trades_df['money_pnl'].min(),
            'exit_reasons': trades_df['exit_reason'].value_counts().to_dict(),
            'ce_trades': len(trades_df[trades_df['option_type'] == 'CE']),
            'pe_trades': len(trades_df[trades_df['option_type'] == 'PE']),
            'ce_pnl': trades_df[trades_df['option_type'] == 'CE']['money_pnl'].sum(),
            'pe_pnl': trades_df[trades_df['option_type'] == 'PE']['money_pnl'].sum(),
            'full_entries': len(trades_df[trades_df['parts_filled'] == 3]),
            'partial_entries': len(trades_df[trades_df['parts_filled'] < 3]),
            'avg_parts': trades_df['parts_filled'].mean(),
            'trades_df': trades_df,
        }
        return report

    def print_report(self, report: Dict):
        """Print formatted report to console."""
        if not report:
            print("No trades to report.")
            return

        r = report
        print("\n" + "=" * 60)
        print(f"  BACKTEST REPORT: {r['instrument']} (Lot Size: {r['lot_size']})")
        print("=" * 60)
        print(f"  Period:       {r['period']}")
        print(f"  RSI Period:   {self.rsi_period} | SL: {self.stop_loss_pct}% | TP: {self.target_pct}%")
        print(f"  Entry Levels: +{config.ENTRY_LEVEL_1_PCT}% / +{config.ENTRY_LEVEL_2_PCT}% / +{config.ENTRY_LEVEL_3_PCT}%")
        print("-" * 60)

        print(f"  Initial Capital:  Rs {r['initial_capital']:>12,.2f}")
        print(f"  Final Capital:    Rs {r['final_capital']:>12,.2f}")
        print(f"  Total P&L:        Rs {r['total_money_pnl']:>12,.2f}")
        print(f"  Return:           {r['return_pct']:>12.2f}%")
        print("-" * 60)

        print(f"  Total Trades:     {r['total_trades']:>6}")
        print(f"  Wins:             {r['wins']:>6} ({r['win_rate']:.1f}%)")
        print(f"  Losses:           {r['losses']:>6}")
        print(f"  Avg P&L:          Rs {r['avg_money_pnl']:>10,.2f}")
        print(f"  Avg Win:          Rs {r['avg_win']:>10,.2f}")
        print(f"  Avg Loss:         Rs {r['avg_loss']:>10,.2f}")
        print(f"  Max Win:          Rs {r['max_win']:>10,.2f}")
        print(f"  Max Loss:         Rs {r['max_loss']:>10,.2f}")
        print("-" * 60)

        print(f"  Full Entries (3/3):  {r['full_entries']:>4}")
        print(f"  Partial Entries:     {r['partial_entries']:>4}")
        print(f"  Avg Parts Filled:    {r['avg_parts']:.2f} / 3")
        print("-" * 60)

        print("  Exit Reasons:")
        for reason, count in r['exit_reasons'].items():
            pct = (count / r['total_trades']) * 100
            print(f"    {reason:20} {count:>4} ({pct:.1f}%)")
        print("-" * 60)

        print(f"  CE: {r['ce_trades']} trades | P&L: Rs {r['ce_pnl']:,.2f}")
        print(f"  PE: {r['pe_trades']} trades | P&L: Rs {r['pe_pnl']:,.2f}")
        print("=" * 60)


# ============================================
# TRADE LOG WRITER
# ============================================
def write_trade_log(reports: Dict[str, Dict]):
    """Write a clean trade log file with all entries."""
    log_path = "backtest_trades.log"

    with open(log_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("RSI OPTIONS STRATEGY - BACKTEST TRADE LOG\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Period: {config.BACKTEST_START_DATE} to {config.BACKTEST_END_DATE}\n")
        f.write(f"Entry Levels: +{config.ENTRY_LEVEL_1_PCT}% / "
                f"+{config.ENTRY_LEVEL_2_PCT}% / +{config.ENTRY_LEVEL_3_PCT}%\n")
        f.write(f"SL: {config.STRATEGY_CONFIG['stop_loss_pct']}% | "
                f"TP: {config.STRATEGY_CONFIG['target_pct']}%\n")
        f.write("=" * 80 + "\n\n")

        for instrument, report in reports.items():
            if not report:
                f.write(f"\n{instrument}: No trades\n")
                continue

            r = report
            lot = r['lot_size']
            f.write(f"\n{'=' * 60}\n")
            f.write(f"  {instrument} SUMMARY (Lot Size: {lot})\n")
            f.write(f"{'=' * 60}\n")
            f.write(f"  Trades: {r['total_trades']} | "
                    f"Wins: {r['wins']} ({r['win_rate']:.1f}%)\n")
            f.write(f"  Option P&L:  Rs {r['total_pnl']:,.2f} (in price points)\n")
            f.write(f"  Money P&L:   Rs {r['total_money_pnl']:,.2f} "
                    f"(x{lot} lot) | Return: {r['return_pct']:.2f}%\n")
            f.write(f"  Capital:     Rs {r['initial_capital']:,.0f} -> "
                    f"Rs {r['final_capital']:,.0f}\n")
            f.write(f"  Full Entries: {r['full_entries']} | "
                    f"Partial: {r['partial_entries']}\n\n")

            # Individual trades
            trades_df = r['trades_df']
            for i, (_, trade) in enumerate(trades_df.iterrows(), 1):
                f.write(f"  --- Trade #{i} ---\n")
                f.write(f"  {trade['option_type']} | Strike: {trade['strike']} | "
                        f"{trade['expiry_type']} | Expiry Code: {trade['expiry_code']}\n")
                f.write(f"  Signal:     {trade['signal_time']} @ Rs {trade['base_price']:.2f}\n")
                f.write(f"  Levels:     +5%={trade['entry_level_1']:.2f} | "
                        f"+10%={trade['entry_level_2']:.2f} | "
                        f"+15%={trade['entry_level_3']:.2f}\n")

                # Parts filled
                parts = trade['parts_filled']
                if parts >= 1:
                    f.write(f"  Part 1:     {trade['part1_time']} @ Rs {trade['part1_price']:.2f}\n")
                if parts >= 2:
                    f.write(f"  Part 2:     {trade['part2_time']} @ Rs {trade['part2_price']:.2f}\n")
                if parts >= 3:
                    f.write(f"  Part 3:     {trade['part3_time']} @ Rs {trade['part3_price']:.2f}\n")

                f.write(f"  Avg Entry:  Rs {trade['avg_entry_price']:.2f} "
                        f"({parts}/3 parts)\n")
                f.write(f"  Exit:       {trade['exit_time']} @ Rs {trade['exit_price']:.2f} "
                        f"[{trade['exit_reason']}]\n")
                f.write(f"  P&L:        Rs {trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%) | "
                        f"Money: Rs {trade['money_pnl']:,.2f}\n\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF LOG\n")
        f.write("=" * 80 + "\n")

    logger.info(f"Trade log saved to {log_path}")


# ============================================
# SUMMARY FILE WRITER
# ============================================
def write_summary(reports: Dict[str, Dict]):
    """Write a clean backtest summary file."""
    path = "backtest_summary.md"

    with open(path, 'w') as f:
        f.write("# Backtest Summary\n\n")
        f.write(f"**Period**: {config.BACKTEST_START_DATE} to {config.BACKTEST_END_DATE}\n\n")
        f.write("## Strategy\n\n")
        f.write("- **Signal**: Sell ATM option when RSI(14) crosses above 70\n")
        f.write("- **RSI**: Calculated on continuous ATM option price (not underlying), "
                "fresh each day\n")
        f.write(f"- **Entry**: Staggered at "
                f"+{config.ENTRY_LEVEL_1_PCT}% / "
                f"+{config.ENTRY_LEVEL_2_PCT}% / "
                f"+{config.ENTRY_LEVEL_3_PCT}% "
                f"(33.33% each)\n")
        f.write(f"- **Stop Loss**: {config.STRATEGY_CONFIG['stop_loss_pct']}% "
                f"(exact fill assumed)\n")
        f.write(f"- **Target**: {config.STRATEGY_CONFIG['target_pct']}% "
                f"(exact fill assumed)\n")
        f.write(f"- **Hours**: {config.TRADING_START_TIME} - {config.TRADING_END_TIME} IST\n")
        f.write("- **Expiry**: Nearest weekly (expiry_code = 1)\n")
        f.write("- **Strikes**: ATM only\n")
        f.write("- **Intraday**: Signals expire at EOD, positions force-closed at EOD\n")
        f.write(f"- **Capital**: Rs {config.BACKTEST_INITIAL_CAPITAL:,} per instrument\n\n")

        # Combined summary
        total_money = sum(r['total_money_pnl'] for r in reports.values())
        total_trades = sum(r['total_trades'] for r in reports.values())
        total_wins = sum(r['wins'] for r in reports.values())
        combined_capital = config.BACKTEST_INITIAL_CAPITAL * len(reports)

        f.write("---\n\n")
        f.write("## Combined Results\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Capital Deployed | Rs {combined_capital:,.0f} |\n")
        f.write(f"| Total Money P&L | Rs {total_money:,.2f} |\n")
        f.write(f"| Combined Return | {(total_money / combined_capital) * 100:.2f}% |\n")
        f.write(f"| Total Trades | {total_trades} |\n")
        f.write(f"| Total Wins | {total_wins} "
                f"({(total_wins/total_trades*100):.1f}%) |\n\n")

        # Per-instrument tables
        for inst, r in reports.items():
            trades_df = r['trades_df']
            lot = r['lot_size']

            # Exit reason counts
            exit_counts = trades_df['exit_reason'].value_counts()
            target_n = exit_counts.get('TARGET', 0)
            sl_n = exit_counts.get('STOP_LOSS', 0)
            eod_n = exit_counts.get('EOD', 0)

            # Option type splits
            ce_df = trades_df[trades_df['option_type'] == 'CE']
            pe_df = trades_df[trades_df['option_type'] == 'PE']

            # Parts breakdown
            parts_counts = trades_df['parts_filled'].value_counts().sort_index()

            # Win/loss money stats
            wins_df = trades_df[trades_df['money_pnl'] > 0]
            loss_df = trades_df[trades_df['money_pnl'] < 0]
            avg_win = wins_df['money_pnl'].mean() if len(wins_df) > 0 else 0
            avg_loss = loss_df['money_pnl'].mean() if len(loss_df) > 0 else 0

            f.write("---\n\n")
            f.write(f"## {inst} (Lot Size: {lot})\n\n")

            # Performance table
            f.write("### Performance\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Initial Capital | Rs {r['initial_capital']:,.0f} |\n")
            f.write(f"| Final Capital | Rs {r['final_capital']:,.0f} |\n")
            f.write(f"| Money P&L | Rs {r['total_money_pnl']:,.2f} |\n")
            f.write(f"| Return | {r['return_pct']:.2f}% |\n")
            f.write(f"| Option P&L (points) | Rs {r['total_pnl']:,.2f} |\n\n")

            # Trade stats table
            f.write("### Trade Statistics\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Total Trades | {r['total_trades']} |\n")
            f.write(f"| Wins | {r['wins']} ({r['win_rate']:.1f}%) |\n")
            f.write(f"| Losses | {r['losses']} |\n")
            f.write(f"| Avg P&L per Trade | Rs {r['avg_money_pnl']:,.2f} |\n")
            f.write(f"| Avg Win | Rs {avg_win:,.2f} |\n")
            f.write(f"| Avg Loss | Rs {avg_loss:,.2f} |\n")
            f.write(f"| Max Win | Rs {r['max_win']:,.2f} |\n")
            f.write(f"| Max Loss | Rs {r['max_loss']:,.2f} |\n\n")

            # Exit reasons
            f.write("### Exit Reasons\n\n")
            f.write("| Reason | Count | % |\n")
            f.write("|--------|-------|---|\n")
            f.write(f"| Target | {target_n} | "
                    f"{(target_n/r['total_trades']*100):.1f}% |\n")
            f.write(f"| Stop Loss | {sl_n} | "
                    f"{(sl_n/r['total_trades']*100):.1f}% |\n")
            f.write(f"| EOD | {eod_n} | "
                    f"{(eod_n/r['total_trades']*100):.1f}% |\n\n")

            # Option type split
            f.write("### By Option Type\n\n")
            f.write("| Type | Trades | Money P&L |\n")
            f.write("|------|--------|----------|\n")
            f.write(f"| CE | {len(ce_df)} | Rs {ce_df['money_pnl'].sum():,.2f} |\n")
            f.write(f"| PE | {len(pe_df)} | Rs {pe_df['money_pnl'].sum():,.2f} |\n\n")

            # Entry fill breakdown
            f.write("### Entry Fill Breakdown\n\n")
            f.write("| Parts Filled | Count |\n")
            f.write("|-------------|-------|\n")
            for parts, count in parts_counts.items():
                f.write(f"| {int(parts)}/3 | {count} |\n")
            f.write(f"| Avg Parts | {r['avg_parts']:.2f} |\n\n")

    logger.info(f"Summary saved to {path}")


# ============================================
# MAIN
# ============================================
def run_backtest_for_instrument(instrument: str) -> Optional[Dict]:
    """Run backtest for one instrument. Returns report dict."""
    data_path = config.BACKTEST_DATA_PATH.get(instrument)
    if not data_path:
        logger.error(f"No data path for {instrument}")
        return None

    engine = BacktestEngine(instrument, data_path)
    engine.run_backtest()
    report = engine.generate_report()
    engine.print_report(report)
    return report


if __name__ == "__main__":
    instruments = ['NIFTY', 'SENSEX']
    reports = {}

    for inst in instruments:
        try:
            report = run_backtest_for_instrument(inst)
            if report:
                reports[inst] = report
        except Exception as e:
            logger.error(f"Error backtesting {inst}: {e}", exc_info=True)

    # Save CSV + trade log
    if reports:
        for inst, report in reports.items():
            filename = f"backtest_results_{inst}.csv"
            report['trades_df'].to_csv(filename, index=False)
            logger.info(f"Saved {inst} -> {filename}")

        # Write detailed trade log + summary
        write_trade_log(reports)
        write_summary(reports)
