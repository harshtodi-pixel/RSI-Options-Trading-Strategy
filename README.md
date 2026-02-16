# RSI Options Trading Strategy

Sell ATM options when RSI crosses above 70, with staggered entries.

## Strategy

1. **Signal**: RSI (14-period, on option price) crosses above 70
2. **Entry**: Staggered sell in 3 parts as premium rises
   - Part 1 (33.33%): base price + 5%
   - Part 2 (33.33%): base price + 10%
   - Part 3 (33.34%): base price + 15%
3. **Exit**: Target 10% / Stop Loss 20% / EOD 2:30 PM
4. **Scope**: ATM strikes, nearest weekly expiry, intraday only
5. **Trading hours**: 9:30 AM - 2:30 PM (9:30 start allows RSI warmup on new contracts)
6. **One trade at a time** per instrument

## Project Structure

```
├── backtest_engine.py         # Backtesting engine
├── config.py                  # All settings
├── rsi_options_strategy.py    # Core strategy logic
├── dhan_datafeed.py           # Dhan API integration
├── trading_bot_runner.py      # Live trading runner
├── telegram_notifier.py       # Telegram alerts
├── data/options/              # Historical parquet data
│   ├── nifty/NIFTY_OPTIONS_1m.parquet
│   └── sensex/SENSEX_OPTIONS_1m.parquet
└── README.md
```

## Data Schema

The parquet files contain 1-minute options data with these columns:

| Column | Description |
|--------|-------------|
| `ts` | Epoch seconds |
| `datetime` | ISO 8601 with IST offset |
| `underlying` | NIFTY or SENSEX |
| `option_type` | CE or PE |
| `expiry_type` | WEEK or MONTH |
| `expiry_code` | 1=nearest, 2=next, 3=far |
| `atm_strike` | ATM strike (spot rounded to nearest step) |
| `strike_offset` | Offset from ATM: 0, +1, -1, ... |
| `moneyness` | ITM, ATM, or OTM |
| `strike` | Actual strike price |
| `spot` | Underlying spot price |
| `open/high/low/close` | Option OHLC |
| `volume` | Volume traded |
| `oi` | Open interest |
| `iv` | Implied volatility |

## Installation

```bash
pip install -r requirements.txt
```

## Running Backtest

```bash
python backtest_engine.py
```

Outputs:
- Console report with performance metrics
- `backtest_results_NIFTY.csv` and `backtest_results_SENSEX.csv`
- `backtest_trades.log` with detailed trade entries

## Running Live Bot

1. Set credentials in `.env.local`:
   ```
   CLIENT_ID = "your_client_id"
   ACCESS_TOKEN = "your_access_token"
   ```
2. Run:
   ```bash
   python trading_bot_runner.py
   ```

**Note**: The bot generates signals only. It does not place orders.

## Configuration

All settings are in `config.py`:

```python
# Strategy
STRATEGY_CONFIG = {
    'rsi_length': 14,
    'stop_loss_pct': 20,
    'target_pct': 10,
}

# Entry levels
ENTRY_LEVEL_1_PCT = 5    # +5%
ENTRY_LEVEL_2_PCT = 10   # +10%
ENTRY_LEVEL_3_PCT = 15   # +15%

# Trading hours
TRADING_START_TIME = "09:30"   # 9:30 AM (allows RSI warmup after contract reset)
TRADING_END_TIME = "14:30"     # 2:30 PM

# Backtest
BACKTEST_START_DATE = "2025-01-01"
BACKTEST_END_DATE = "2025-12-31"
BACKTEST_INITIAL_CAPITAL = 200000
```

## Disclaimer

For educational purposes only. Options trading involves substantial risk.
