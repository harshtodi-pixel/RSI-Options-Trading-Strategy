"""
Configuration file for RSI Options Trading Strategy
Modify these settings according to your requirements
"""

# ============================================
# DHAN API CREDENTIALS
# ============================================
# Get these from: https://dhan.co/api
CLIENT_ID = "YOUR_CLIENT_ID_HERE"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN_HERE"


# ============================================
# STRATEGY PARAMETERS
# ============================================
STRATEGY_CONFIG = {
    # RSI calculation period
    'rsi_length': 14,
    
    # Stop loss percentage (20 means 20% loss)
    'stop_loss_pct': 20,
    
    # Target profit percentage (10 means 10% profit)
    'target_pct': 10,
}


# ============================================
# INSTRUMENTS TO MONITOR
# ============================================
# Select which instruments to trade
# Available: NIFTY, SENSEX, BANKNIFTY, RELIANCE, HDFCBANK
INSTRUMENTS = ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'HDFCBANK', 'SENSEX']


# ============================================
# POSITION SIZING
# ============================================
# Capital allocation per position
# Each position is divided into 3 parts: 33.33%, 33.33%, 33.34%
CAPITAL_PER_POSITION = 100000  # Example: ₹1,00,000


# ============================================
# TRADING HOURS
# ============================================
# IST timezone
TRADING_START_TIME = "09:18"  # HH:MM format
TRADING_END_TIME = "15:15"    # HH:MM format


# ============================================
# ENTRY LEVELS
# ============================================
# Staggered entry at premium levels
ENTRY_LEVEL_1_PCT = 5   # Entry 1 at +5% premium
ENTRY_LEVEL_2_PCT = 10  # Entry 2 at +10% premium
ENTRY_LEVEL_3_PCT = 15  # Entry 3 at +15% premium


# ============================================
# STRIKE SELECTION
# ============================================
# Strike rounding for each instrument
STRIKE_ROUNDING = {
    'NIFTY': 50,
    'BANKNIFTY': 100,
    'SENSEX': 100,
    'RELIANCE': 5,
    'HDFCBANK': 10
}


# ============================================
# RISK MANAGEMENT
# ============================================
# Maximum concurrent positions (set to 1 for one at a time)
MAX_CONCURRENT_POSITIONS = 1

# Risk per trade as % of capital
RISK_PER_TRADE_PCT = 2  # 2% of capital


# ============================================
# DATA REFRESH SETTINGS
# ============================================
# How often to check for new data (in seconds)
DATA_REFRESH_INTERVAL = 1  # 1 second

# How often to update ATM strikes (in seconds)
ATM_UPDATE_INTERVAL = 300  # 5 minutes


# ============================================
# LOGGING SETTINGS
# ============================================
# Log file location
LOG_FILE = "trading_bot.log"

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"


# ============================================
# NOTIFICATION SETTINGS (Optional)
# ============================================
# Telegram notifications
# To set up:
# 1. Open Telegram and search for @BotFather
# 2. Send /newbot and follow instructions to create a bot
# 3. Copy the bot token
# 4. Start a chat with your bot and send any message
# 5. Run: python telegram_notifier.py to get your chat ID
# 6. Update the values below

ENABLE_TELEGRAM_NOTIFICATIONS = True  # Set to True to enable
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token_here"  # From BotFather
TELEGRAM_CHAT_ID = "your_telegram_chat_id_here"      # From telegram_notifier.py script


# ============================================
# BACKTEST SETTINGS
# ============================================
# For backtesting mode
BACKTEST_START_DATE = "2024-01-01"
BACKTEST_END_DATE = "2024-12-31"
BACKTEST_INITIAL_CAPITAL = 1000000  # ₹10,00,000


# ============================================
# VALIDATION
# ============================================
def validate_config():
    """Validate configuration parameters"""
    errors = []
    
    if CLIENT_ID == "YOUR_CLIENT_ID_HERE":
        errors.append("CLIENT_ID not set")
    
    if ACCESS_TOKEN == "YOUR_ACCESS_TOKEN_HERE":
        errors.append("ACCESS_TOKEN not set")
    
    if STRATEGY_CONFIG['rsi_length'] < 2:
        errors.append("RSI length must be at least 2")
    
    if STRATEGY_CONFIG['stop_loss_pct'] <= 0:
        errors.append("Stop loss must be positive")
    
    if STRATEGY_CONFIG['target_pct'] <= 0:
        errors.append("Target must be positive")
    
    if not INSTRUMENTS:
        errors.append("At least one instrument must be selected")
    
    return errors


if __name__ == "__main__":
    # Validate configuration
    errors = validate_config()
    
    if errors:
        print("\n" + "="*60)
        print("CONFIGURATION ERRORS:")
        print("="*60)
        for error in errors:
            print(f"  ❌ {error}")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("CONFIGURATION VALID ✓")
        print("="*60)
        print(f"Instruments: {', '.join(INSTRUMENTS)}")
        print(f"RSI Length: {STRATEGY_CONFIG['rsi_length']}")
        print(f"Stop Loss: {STRATEGY_CONFIG['stop_loss_pct']}%")
        print(f"Target: {STRATEGY_CONFIG['target_pct']}%")
        print(f"Trading Hours: {TRADING_START_TIME} - {TRADING_END_TIME} IST")
        print("="*60 + "\n")
