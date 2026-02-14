"""
Main Runner Script
Integrates RSI Options Strategy with Dhan Live Data Feed
"""

import time
import logging
from datetime import datetime
import pytz
from typing import Dict
import sys

from rsi_options_strategy import RSIOptionsStrategy
from dhan_datafeed import DhanDataFeed
from telegram_notifier import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main trading bot that connects strategy with live data
    """
    
    def __init__(self, client_id: str, access_token: str, config: Dict, 
                 telegram_config: Dict = None):
        """
        Initialize trading bot
        
        Args:
            client_id: Dhan client ID
            access_token: Dhan access token
            config: Strategy configuration
            telegram_config: Telegram configuration dict with bot_token and chat_id
        """
        self.ist = pytz.timezone('Asia/Kolkata')
        
        # Initialize Telegram notifier (optional)
        self.telegram = None
        if telegram_config and telegram_config.get('enabled'):
            try:
                logger.info("Initializing Telegram notifications...")
                self.telegram = TelegramNotifier(
                    telegram_config['bot_token'],
                    telegram_config['chat_id']
                )
            except Exception as e:
                logger.warning(f"Telegram initialization failed: {e}")
                logger.warning("Continuing without Telegram notifications")
        
        # Initialize data feed
        logger.info("Initializing Dhan data feed...")
        self.data_feed = DhanDataFeed(client_id, access_token)
        
        # Initialize strategy
        logger.info("Initializing RSI strategy...")
        self.strategy = RSIOptionsStrategy(self.data_feed, config, self.telegram)
        
        # Tracking variables
        self.current_atm_strikes = {}
        self.last_candle_time = {}
        self.candle_data = {}  # Store OHLC for 1-min candles
        
        logger.info("Trading bot initialized successfully")
    
    def initialize_instruments(self):
        """
        Initialize ATM strikes and option symbols for all instruments
        """
        logger.info("\n" + "="*60)
        logger.info("INITIALIZING INSTRUMENTS")
        logger.info("="*60)
        
        for instrument in self.strategy.instruments:
            try:
                # Get spot price
                spot_price = self.data_feed.get_spot_price(instrument)
                if not spot_price:
                    logger.error(f"Failed to get spot price for {instrument}")
                    continue
                
                # Calculate ATM strike
                atm_strike = self.data_feed.get_atm_strike(spot_price, instrument)
                
                # Get expiry
                expiry = self.data_feed.get_weekly_expiry(instrument)
                
                # Store for this instrument
                self.current_atm_strikes[instrument] = {
                    'spot': spot_price,
                    'strike': atm_strike,
                    'expiry': expiry
                }
                
                # Initialize candle tracking
                self.last_candle_time[instrument] = None
                self.candle_data[instrument] = {
                    'call': {'open': None, 'high': None, 'low': None, 'close': None},
                    'put': {'open': None, 'high': None, 'low': None, 'close': None}
                }
                
                logger.info(f"\n{instrument}:")
                logger.info(f"  Spot Price: ₹{spot_price:.2f}")
                logger.info(f"  ATM Strike: {atm_strike}")
                logger.info(f"  Expiry: {expiry}")
                
            except Exception as e:
                logger.error(f"Error initializing {instrument}: {e}")
        
        logger.info("\n" + "="*60 + "\n")
    
    def update_atm_strikes(self):
        """
        Update ATM strikes periodically (every 5 minutes)
        Only updates if spot has moved significantly
        """
        for instrument in self.strategy.instruments:
            try:
                # Get current spot
                spot_price = self.data_feed.get_spot_price(instrument)
                if not spot_price:
                    continue
                
                # Calculate new ATM
                new_atm = self.data_feed.get_atm_strike(spot_price, instrument)
                
                # Check if ATM has changed
                if instrument in self.current_atm_strikes:
                    old_atm = self.current_atm_strikes[instrument]['strike']
                    
                    if new_atm != old_atm:
                        logger.info(f"\n{'~'*60}")
                        logger.info(f"ATM STRIKE UPDATED - {instrument}")
                        logger.info(f"{'~'*60}")
                        logger.info(f"Old ATM: {old_atm}")
                        logger.info(f"New ATM: {new_atm}")
                        logger.info(f"Spot: ₹{spot_price:.2f}")
                        logger.info(f"{'~'*60}\n")
                        
                        # Send Telegram notification
                        if self.telegram:
                            self.telegram.send_atm_update(
                                instrument, old_atm, new_atm, spot_price
                            )
                        
                        # Update strike
                        self.current_atm_strikes[instrument]['strike'] = new_atm
                        self.current_atm_strikes[instrument]['spot'] = spot_price
                        
                        # Reset candle data for new strike
                        self.candle_data[instrument] = {
                            'call': {'open': None, 'high': None, 'low': None, 'close': None},
                            'put': {'open': None, 'high': None, 'low': None, 'close': None}
                        }
                
            except Exception as e:
                logger.error(f"Error updating ATM for {instrument}: {e}")
    
    def process_option_tick(self, instrument: str, option_type: str, 
                           ltp: float, current_time: datetime):
        """
        Process tick data and build 1-minute candles
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            ltp: Last traded price
            current_time: Current time
        """
        # Get current minute (floor to minute)
        current_minute = current_time.replace(second=0, microsecond=0)
        
        # Check if this is a new candle
        last_minute = self.last_candle_time.get(instrument)
        
        if last_minute is None or current_minute > last_minute:
            # New candle - process previous candle if exists
            if last_minute is not None:
                candle = self.candle_data[instrument][option_type]
                
                if candle['close'] is not None:
                    # Process completed candle
                    self.strategy.process_tick(
                        instrument,
                        option_type,
                        candle['close'],
                        candle['high']
                    )
            
            # Start new candle
            self.candle_data[instrument][option_type] = {
                'open': ltp,
                'high': ltp,
                'low': ltp,
                'close': ltp
            }
            
            self.last_candle_time[instrument] = current_minute
        
        else:
            # Update current candle
            candle = self.candle_data[instrument][option_type]
            candle['high'] = max(candle['high'], ltp)
            candle['low'] = min(candle['low'], ltp)
            candle['close'] = ltp
    
    def run(self):
        """
        Main loop - fetch data and process ticks
        """
        logger.info("\n" + "="*60)
        logger.info("TRADING BOT STARTED")
        logger.info("="*60)
        logger.info(f"Instruments: {', '.join(self.strategy.instruments)}")
        logger.info(f"RSI Length: {self.strategy.rsi_length}")
        logger.info(f"Stop Loss: {self.strategy.stop_loss_pct * 100}%")
        logger.info(f"Target: {self.strategy.target_pct * 100}%")
        logger.info(f"Trading Hours: 09:18 to 15:15 IST")
        logger.info("="*60 + "\n")
        
        # Send Telegram notification
        if self.telegram:
            self.telegram.send_bot_started(
                self.strategy.instruments,
                {
                    'rsi_length': self.strategy.rsi_length,
                    'stop_loss_pct': self.strategy.stop_loss_pct * 100,
                    'target_pct': self.strategy.target_pct * 100
                }
            )
        
        # Initialize instruments
        self.initialize_instruments()
        
        # Track iterations for periodic updates
        iteration = 0
        
        try:
            while True:
                current_time = datetime.now(self.ist)
                
                # Check trading hours
                if not self.strategy.is_trading_hours():
                    if current_time.time().hour < 9:
                        logger.info("Market not yet open. Waiting...")
                        time.sleep(60)
                    else:
                        logger.info("Market closed for the day.")
                        break
                    continue
                
                # Update ATM strikes every 5 minutes (300 iterations at 1 sec interval)
                if iteration % 300 == 0 and iteration > 0:
                    self.update_atm_strikes()
                
                # Process each instrument
                for instrument in self.strategy.instruments:
                    if instrument not in self.current_atm_strikes:
                        continue
                    
                    try:
                        strike = self.current_atm_strikes[instrument]['strike']
                        expiry = self.current_atm_strikes[instrument]['expiry']
                        
                        # Get call option data
                        call_data = self.data_feed.get_option_price(
                            instrument, strike, expiry, 'CE'
                        )
                        
                        if call_data:
                            self.process_option_tick(
                                instrument,
                                'call',
                                call_data['ltp'],
                                current_time
                            )
                        
                        # Get put option data
                        put_data = self.data_feed.get_option_price(
                            instrument, strike, expiry, 'PE'
                        )
                        
                        if put_data:
                            self.process_option_tick(
                                instrument,
                                'put',
                                put_data['ltp'],
                                current_time
                            )
                        
                        # Small delay to avoid rate limiting
                        time.sleep(0.2)
                        
                    except Exception as e:
                        logger.error(f"Error processing {instrument}: {e}")
                
                # Check for end of day
                if current_time.time() >= self.strategy.end_time:
                    self.strategy.force_close_eod()
                    logger.info("End of trading day. Stopping bot.")
                    break
                
                iteration += 1
                
                # Wait before next iteration (adjust based on needs)
                # 1 second interval means we update every second
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n\nBot stopped by user (Ctrl+C)")
            if self.strategy.position_state['cycle_active']:
                logger.info("WARNING: Active position exists. Please manage manually.")
        
        except Exception as e:
            logger.error(f"Critical error in main loop: {e}", exc_info=True)
        
        finally:
            # Send Telegram notification
            if self.telegram:
                self.telegram.send_bot_stopped()
            
            logger.info("\n" + "="*60)
            logger.info("TRADING BOT STOPPED")
            logger.info("="*60)


def main():
    """
    Entry point for the trading bot
    """
    # Configuration
    CLIENT_ID = "YOUR_DHAN_CLIENT_ID"
    ACCESS_TOKEN = "YOUR_DHAN_ACCESS_TOKEN"
    
    # Telegram configuration
    ENABLE_TELEGRAM = True  # Set to False to disable
    TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
    
    # Strategy configuration
    config = {
        'rsi_length': 14,
        'stop_loss_pct': 20,  # 20%
        'target_pct': 10      # 10%
    }
    
    # Validate credentials
    if CLIENT_ID == "YOUR_DHAN_CLIENT_ID" or ACCESS_TOKEN == "YOUR_DHAN_ACCESS_TOKEN":
        print("\n" + "="*60)
        print("ERROR: Please update CLIENT_ID and ACCESS_TOKEN")
        print("="*60)
        print("\nSteps to get credentials:")
        print("1. Login to Dhan: https://dhan.co")
        print("2. Go to API section in settings")
        print("3. Generate API credentials")
        print("4. Update CLIENT_ID and ACCESS_TOKEN in this script")
        print("="*60 + "\n")
        sys.exit(1)
    
    # Telegram configuration
    telegram_config = None
    if ENABLE_TELEGRAM:
        if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or TELEGRAM_CHAT_ID == "YOUR_TELEGRAM_CHAT_ID":
            print("\n" + "="*60)
            print("WARNING: Telegram credentials not configured")
            print("="*60)
            print("\nTo enable Telegram notifications:")
            print("1. Run: python telegram_notifier.py")
            print("2. Follow the instructions to get bot token and chat ID")
            print("3. Update TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            print("\nContinuing without Telegram notifications...")
            print("="*60 + "\n")
            time.sleep(3)
        else:
            telegram_config = {
                'enabled': True,
                'bot_token': TELEGRAM_BOT_TOKEN,
                'chat_id': TELEGRAM_CHAT_ID
            }
    
    # Create and run bot
    try:
        bot = TradingBot(CLIENT_ID, ACCESS_TOKEN, config, telegram_config)
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)


if __name__ == "__main__":
    main()
