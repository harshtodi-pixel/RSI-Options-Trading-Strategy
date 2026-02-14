# RSI Options Trading Strategy - Python Implementation

Complete Python implementation of the PineScript RSI 70 Premium Staggered Short strategy for options trading.

## 🎯 Strategy Overview

This strategy:
- Monitors **ATM Call and Put options** for 5 instruments (Nifty, Sensex, BankNifty, Reliance, HDFC Bank)
- Calculates **RSI on option prices** (not underlying) using 1-minute candles
- Generates **sell signals** when option price RSI crosses above 70
- Implements **staggered entries** at +5%, +10%, and +15% premium levels
- Manages positions with **10% target** and **20% stop loss**
- Trades only **one position at a time**

## 📋 Features

- ✅ Real-time data from Dhan API
- ✅ Automatic ATM strike selection
- ✅ Weekly expiry handling
- ✅ 1-minute candle formation
- ✅ RSI calculation on option prices
- ✅ Signal generation only (no order placement)
- ✅ Comprehensive logging
- ✅ **📱 Telegram notifications for all signals**
- ✅ Risk management with stop loss and targets
- ✅ IST timezone support
- ✅ Trading hours enforcement (9:18 AM - 3:15 PM)

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Dhan trading account with API access
- pip package manager

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- pandas (data manipulation)
- numpy (numerical calculations)
- dhanhq (Dhan API client)
- pytz (timezone handling)

### Step 2: Get Dhan API Credentials

1. Login to your Dhan account: https://dhan.co
2. Navigate to Settings → API
3. Generate API credentials
4. Note down your:
   - Client ID
   - Access Token

### Step 3: Configure the Bot

Open `config.py` and update:

```python
CLIENT_ID = "your_actual_client_id"
ACCESS_TOKEN = "your_actual_access_token"
```

You can also customize:
- RSI length (default: 14)
- Stop loss % (default: 20%)
- Target % (default: 10%)
- Instruments to monitor
- Entry levels

### Step 4: Validate Configuration

```bash
python config.py
```

This will check if your configuration is valid.

### Step 5: Setup Telegram Notifications (Optional but Recommended)

Get instant alerts on your phone for every trading signal!

**Quick Setup:**
```bash
python telegram_notifier.py
```

Follow the prompts to:
1. Create a Telegram bot
2. Get your chat ID
3. Configure notifications

**Detailed Instructions:** See [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) for complete guide.

**Skip Telegram:** Set `ENABLE_TELEGRAM_NOTIFICATIONS = False` in config.py

## 📊 Project Structure

```
.
├── rsi_options_strategy.py    # Core strategy logic
├── dhan_datafeed.py           # Dhan API integration
├── trading_bot_runner.py      # Main execution script
├── telegram_notifier.py       # Telegram notifications
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── TELEGRAM_SETUP.md          # Telegram setup guide
```

## 🎮 Usage

### Running the Bot

```bash
python trading_bot_runner.py
```

The bot will:
1. Initialize connection to Dhan API
2. Calculate ATM strikes for all instruments
3. Start monitoring option prices
4. Build 1-minute candles
5. Calculate RSI on option prices
6. Generate signals when RSI crosses 70
7. Log all activities to console and `trading_bot.log`

### Understanding the Logs

The bot generates detailed logs for:

**New Signal Generated:**
```
============================================================
NEW SIGNAL GENERATED
============================================================
Instrument: NIFTY
Option Type: CALL
Base Price: ₹150.50
RSI: 72.34
Time: 2026-02-15 10:30:00

Entry Levels:
  Part 1 (33.33%): ₹158.03 (+5%)
  Part 2 (33.33%): ₹165.55 (+10%)
  Part 3 (33.33%): ₹173.08 (+15%)
============================================================
```

**Entry Signals:**
```
************************************************************
ENTRY SIGNAL - PART 1
************************************************************
Instrument: NIFTY CALL
Entry Price: ₹158.03
Quantity: 33.33% of allocated capital
Time: 2026-02-15 10:35:00
************************************************************
```

**Exit Signals:**
```
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
TARGET HIT - PROFIT BOOKED
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
Instrument: NIFTY CALL
Average Entry: ₹165.54
Exit Price: ₹148.99
Profit: 10.00%
Time: 2026-02-15 11:15:00
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
```

## 🔧 Configuration Options

### Strategy Parameters

```python
STRATEGY_CONFIG = {
    'rsi_length': 14,        # RSI calculation period
    'stop_loss_pct': 20,     # Stop loss percentage
    'target_pct': 10,        # Target profit percentage
}
```

### Instruments

```python
INSTRUMENTS = ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'HDFCBANK', 'SENSEX']
```

### Entry Levels

```python
ENTRY_LEVEL_1_PCT = 5   # +5% premium
ENTRY_LEVEL_2_PCT = 10  # +10% premium
ENTRY_LEVEL_3_PCT = 15  # +15% premium
```

### Trading Hours

```python
TRADING_START_TIME = "09:18"
TRADING_END_TIME = "15:15"
```

## 📈 How It Works

### 1. Initialization
- Connects to Dhan API
- Fetches spot prices for all instruments
- Calculates ATM strikes
- Determines current week's expiry

### 2. Data Collection
- Fetches option prices every second
- Builds 1-minute OHLC candles
- Maintains price history for RSI calculation

### 3. RSI Calculation
- Calculates RSI on **option price** (not underlying)
- Uses 14-period RSI (configurable)
- Separate RSI for Call and Put options

### 4. Signal Generation
When RSI crosses above 70:
- Logs the signal
- Sets base price
- Calculates 3 entry levels (+5%, +10%, +15%)
- Marks position as active

### 5. Entry Execution
- Part 1: When price reaches +5% above base
- Part 2: When price reaches +10% above base
- Part 3: When price reaches +15% above base
- Each entry is 33.33% of position size

### 6. Exit Management
- **Target**: -10% from average entry (profit for short position)
- **Stop Loss**: +20% from average entry (loss for short position)
- **Force Close**: At 3:15 PM IST

### 7. Position Tracking
- Only 1 position active at a time
- Ignores new signals while position is active
- Resets after exit for next signal

## ⚠️ Important Notes

### Signal Generation Only
This implementation **DOES NOT place actual orders**. It only:
- Generates signals
- Logs entry/exit levels
- Tracks positions virtually

You need to manually place orders based on the signals logged.

### Strike Selection
- ATM strike is recalculated every 5 minutes
- Rounded to nearest:
  - Nifty: 50
  - BankNifty: 100
  - Sensex: 100
  - Reliance: 5
  - HDFC Bank: 10

### Expiry Selection
- **Nifty/BankNifty**: Current week Thursday expiry
- **Sensex**: Current week Friday expiry
- **Stocks**: Monthly expiry (last Thursday)

### Trading Hours
Strictly enforces 9:18 AM to 3:15 PM IST trading window.

## 🐛 Troubleshooting

### Connection Issues
```
Error: Failed to connect to Dhan API
```
**Solution**: Check your CLIENT_ID and ACCESS_TOKEN

### No Data Received
```
Error: Failed to get spot price for NIFTY
```
**Solution**: 
- Verify market is open
- Check Dhan API status
- Ensure instrument symbols are correct

### ATM Strike Not Updating
**Solution**: 
- Check if spot price is changing
- Verify ATM update interval (default: 5 minutes)

### RSI Not Calculating
```
Warning: Insufficient data for RSI calculation
```
**Solution**: Wait for at least 15 minutes (14 periods + 1)

## 📝 Customization

### Adding More Instruments

Edit `config.py`:
```python
INSTRUMENTS = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
```

Don't forget to add strike rounding:
```python
STRIKE_ROUNDING = {
    'NIFTY': 50,
    'BANKNIFTY': 100,
    'FINNIFTY': 50  # Add new instrument
}
```

### Changing Timeframe

To use 5-minute candles instead of 1-minute, modify `trading_bot_runner.py`:
```python
# In process_option_tick method, change:
current_minute = current_time.replace(second=0, microsecond=0)

# To:
current_minute = current_time.replace(
    minute=(current_time.minute // 5) * 5, 
    second=0, 
    microsecond=0
)
```

### Adding Notifications

Implement in `rsi_options_strategy.py`:
```python
def send_notification(self, message):
    # Add email/Telegram/SMS logic here
    pass
```

## 📊 Example Output

**Console:**
```
============================================================
TRADING BOT STARTED
============================================================
Instruments: NIFTY, BANKNIFTY, RELIANCE, HDFCBANK, SENSEX
RSI Length: 14
Stop Loss: 20.0%
Target: 10.0%
Trading Hours: 09:18 to 15:15 IST
============================================================

✅ Telegram notifications enabled

============================================================
INITIALIZING INSTRUMENTS
============================================================

NIFTY:
  Spot Price: ₹24125.50
  ATM Strike: 24100
  Expiry: 20-FEB-2026

BANKNIFTY:
  Spot Price: ₹52345.80
  ATM Strike: 52300
  Expiry: 20-FEB-2026

...

2026-02-15 09:18:30 - INFO - Monitoring started
2026-02-15 10:25:45 - INFO - NEW SIGNAL GENERATED - NIFTY CALL
2026-02-15 10:30:12 - INFO - ENTRY SIGNAL - PART 1
...
```

**Telegram:**

You'll receive formatted messages on your phone for every signal! 📱

See [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) for examples of Telegram notifications.

## 🔒 Security

- Never share your API credentials
- Use environment variables for production:
  ```bash
  export DHAN_CLIENT_ID="your_client_id"
  export DHAN_ACCESS_TOKEN="your_access_token"
  ```
- Keep logs secure (they may contain sensitive data)

## 📞 Support

For issues:
1. Check logs in `trading_bot.log`
2. Verify configuration with `python config.py`
3. Review Dhan API documentation: https://dhanhq.co/docs/

## ⚖️ Disclaimer

**This software is for educational purposes only.**

- Past performance does not guarantee future results
- Options trading involves substantial risk
- You can lose more than your initial investment
- Always test with paper trading first
- The author is not responsible for any financial losses

## 📄 License

This project is provided as-is without any warranty.

---

**Happy Trading! 📈**
