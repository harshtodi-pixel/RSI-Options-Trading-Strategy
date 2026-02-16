"""
Configuration for RSI Options Trading Strategy

Used by:
  - backtest_engine.py (backtesting)
  - trading_bot_runner.py (live trading)
"""

import os

# ============================================
# DHAN API CREDENTIALS
# ============================================
CLIENT_ID = os.getenv("CLIENT_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")


# ============================================
# STRATEGY PARAMETERS
# ============================================
STRATEGY_CONFIG = {
    'rsi_length': 14,       # RSI period (calculated on option price)
    'stop_loss_pct': 20,    # SL: exit if price rises 20% above avg entry
    'target_pct': 10,       # TP: exit if price drops 10% below avg entry
}


# ============================================
# STAGGERED ENTRY LEVELS
# ============================================
# After RSI crosses 70, sell in 3 parts as price rises:
#   Part 1 (33.33%): base_price + 5%
#   Part 2 (33.33%): base_price + 10%
#   Part 3 (33.34%): base_price + 15%
ENTRY_LEVEL_1_PCT = 5
ENTRY_LEVEL_2_PCT = 10
ENTRY_LEVEL_3_PCT = 15


# ============================================
# TRADING HOURS (IST)
# ============================================
TRADING_START_TIME = "09:30"   # Signal detection starts (9:30 to allow RSI warmup)
TRADING_END_TIME = "14:30"     # Force exit all positions (2:30 PM)


# ============================================
# POSITION SIZING
# ============================================
CAPITAL_PER_POSITION = 200000  # Rs 2,00,000 per lot

# Lot sizes per instrument (number of units per lot)
LOT_SIZE = {
    'NIFTY': 75,
    'BANKNIFTY': 30,
    'SENSEX': 20,
    'RELIANCE': 250,
    'HDFCBANK': 550,
}


# ============================================
# INSTRUMENTS
# ============================================
INSTRUMENTS = ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'HDFCBANK', 'SENSEX']

# Strike rounding per instrument
STRIKE_ROUNDING = {
    'NIFTY': 50,
    'BANKNIFTY': 100,
    'SENSEX': 100,
    'RELIANCE': 5,
    'HDFCBANK': 10,
}


# ============================================
# BACKTEST SETTINGS
# ============================================
BACKTEST_START_DATE = "2025-01-01"
BACKTEST_END_DATE = "2025-12-31"
BACKTEST_INITIAL_CAPITAL = 200000  # Rs 2,00,000

# Data paths (parquet files with 1-min options OHLC)
BACKTEST_DATA_PATH = {
    'NIFTY': 'data/options/nifty/NIFTY_OPTIONS_1m.parquet',
    'SENSEX': 'data/options/sensex/SENSEX_OPTIONS_1m.parquet',
}


# ============================================
# LIVE TRADING SETTINGS
# ============================================
DATA_REFRESH_INTERVAL = 1    # seconds
ATM_UPDATE_INTERVAL = 300    # seconds
MAX_CONCURRENT_POSITIONS = 1

# Logging
LOG_FILE = "trading_bot.log"
LOG_LEVEL = "INFO"

# Telegram (optional)
ENABLE_TELEGRAM_NOTIFICATIONS = True
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token_here"
TELEGRAM_CHAT_ID = "your_telegram_chat_id_here"
