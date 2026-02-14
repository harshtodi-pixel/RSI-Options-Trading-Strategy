"""
RSI 70 Premium Staggered Short Strategy - Options Version
Calculates RSI on ATM Call and Put option prices
Generates signals when option price RSI crosses above 70
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz
import logging
from typing import Dict, List, Optional, Tuple
import time as time_module

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rsi_strategy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RSIOptionsStrategy:
    """
    RSI-based options trading strategy
    - Monitors ATM Call and Put options for 5 instruments
    - Calculates RSI on 1-minute option price candles
    - Generates sell signals when RSI crosses above 70
    - Implements staggered entry at +5%, +10%, +15% premium levels
    """
    
    def __init__(self, dhan_client, config: Dict, telegram_notifier=None):
        """
        Initialize the strategy
        
        Args:
            dhan_client: Dhan API client instance
            config: Configuration dictionary with strategy parameters
            telegram_notifier: TelegramNotifier instance (optional)
        """
        self.dhan = dhan_client
        self.config = config
        self.telegram = telegram_notifier
        
        # Strategy parameters
        self.rsi_length = config.get('rsi_length', 14)
        self.stop_loss_pct = config.get('stop_loss_pct', 20) / 100
        self.target_pct = config.get('target_pct', 10) / 100
        
        # Trading hours (IST)
        self.ist = pytz.timezone('Asia/Kolkata')
        self.start_time = time(9, 18)
        self.end_time = time(15, 15)
        
        # Instruments to monitor
        self.instruments = ['NIFTY', 'SENSEX', 'BANKNIFTY', 'RELIANCE', 'HDFCBANK']
        
        # Data storage for each instrument
        self.option_data = {
            instrument: {
                'call': {'prices': [], 'timestamps': [], 'rsi': []},
                'put': {'prices': [], 'timestamps': [], 'rsi': []}
            }
            for instrument in self.instruments
        }
        
        # Position tracking
        self.active_position = None  # Only one position at a time
        self.position_state = {
            'instrument': None,
            'option_type': None,  # 'call' or 'put'
            'base_price': None,
            'entry_prices': [],
            'quantities': [],
            'part1_taken': False,
            'part2_taken': False,
            'part3_taken': False,
            'cycle_active': False
        }
        
        # Strike selection parameters
        self.strike_rounding = {
            'NIFTY': 50,
            'BANKNIFTY': 100,
            'SENSEX': 100,
            'RELIANCE': 5,
            'HDFCBANK': 5
        }
        
    def get_atm_strike(self, spot_price: float, instrument: str) -> int:
        """
        Calculate ATM strike price based on spot price
        
        Args:
            spot_price: Current spot price of underlying
            instrument: Instrument name
            
        Returns:
            ATM strike price
        """
        rounding = self.strike_rounding.get(instrument, 50)
        atm_strike = round(spot_price / rounding) * rounding
        return int(atm_strike)
    
    def get_weekly_expiry(self) -> str:
        """
        Get current week's expiry date for options
        
        Returns:
            Expiry date in 'YYYY-MM-DD' format
        """
        today = datetime.now(self.ist).date()
        # For Nifty/BankNifty: Thursday expiry
        # For others: check exchange calendar
        days_until_thursday = (3 - today.weekday()) % 7
        if days_until_thursday == 0 and datetime.now(self.ist).time() > time(15, 30):
            days_until_thursday = 7
        
        expiry = today + timedelta(days=days_until_thursday)
        return expiry.strftime('%Y-%m-%d')
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Calculate RSI for given price series
        
        Args:
            prices: List of prices
            period: RSI period (default 14)
            
        Returns:
            Current RSI value or None if insufficient data
        """
        if len(prices) < period + 1:
            return None
        
        prices_array = np.array(prices)
        deltas = np.diff(prices_array)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        now = datetime.now(self.ist).time()
        return self.start_time <= now <= self.end_time
    
    def update_option_data(self, instrument: str, option_type: str, 
                          price: float, timestamp: datetime):
        """
        Update option price data and calculate RSI
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            price: Option price
            timestamp: Price timestamp
        """
        data = self.option_data[instrument][option_type]
        
        # Add new price
        data['prices'].append(price)
        data['timestamps'].append(timestamp)
        
        # Keep only last 100 prices (enough for RSI calculation)
        if len(data['prices']) > 100:
            data['prices'] = data['prices'][-100:]
            data['timestamps'] = data['timestamps'][-100:]
        
        # Calculate RSI
        rsi = self.calculate_rsi(data['prices'], self.rsi_length)
        if rsi is not None:
            data['rsi'].append(rsi)
            if len(data['rsi']) > 100:
                data['rsi'] = data['rsi'][-100:]
    
    def check_rsi_crossover(self, instrument: str, option_type: str) -> bool:
        """
        Check if RSI crossed above 70
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            
        Returns:
            True if RSI just crossed above 70
        """
        rsi_values = self.option_data[instrument][option_type]['rsi']
        
        if len(rsi_values) < 2:
            return False
        
        # Check for crossover: previous RSI <= 70 and current RSI > 70
        return rsi_values[-2] <= 70 and rsi_values[-1] > 70
    
    def generate_signal(self, instrument: str, option_type: str, 
                       current_price: float, rsi: float):
        """
        Generate trading signal when RSI crosses 70
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            current_price: Current option price
            rsi: Current RSI value
        """
        # Check if we already have an active position
        if self.position_state['cycle_active']:
            logger.info(f"Signal ignored - Position already active on "
                       f"{self.position_state['instrument']} "
                       f"{self.position_state['option_type'].upper()}")
            return
        
        # Initialize new position
        self.position_state = {
            'instrument': instrument,
            'option_type': option_type,
            'base_price': current_price,
            'entry_prices': [],
            'quantities': [],
            'part1_taken': False,
            'part2_taken': False,
            'part3_taken': False,
            'cycle_active': True,
            'start_time': datetime.now(self.ist)
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"NEW SIGNAL GENERATED")
        logger.info(f"{'='*60}")
        logger.info(f"Instrument: {instrument}")
        logger.info(f"Option Type: {option_type.upper()}")
        logger.info(f"Base Price: ₹{current_price:.2f}")
        logger.info(f"RSI: {rsi:.2f}")
        logger.info(f"Time: {datetime.now(self.ist).strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"\nEntry Levels:")
        logger.info(f"  Part 1 (33.33%): ₹{current_price * 1.05:.2f} (+5%)")
        logger.info(f"  Part 2 (33.33%): ₹{current_price * 1.10:.2f} (+10%)")
        logger.info(f"  Part 3 (33.33%): ₹{current_price * 1.15:.2f} (+15%)")
        logger.info(f"{'='*60}\n")
        
        # Send Telegram notification
        if self.telegram:
            entry_levels = {
                'part1': current_price * 1.05,
                'part2': current_price * 1.10,
                'part3': current_price * 1.15
            }
            self.telegram.send_new_signal(
                instrument, option_type, current_price, rsi, entry_levels
            )
    
    def check_entry_levels(self, current_price: float, high_price: float):
        """
        Check if entry levels are hit and generate entry signals
        
        Args:
            current_price: Current option price
            high_price: High of current candle
        """
        if not self.position_state['cycle_active']:
            return
        
        state = self.position_state
        base_price = state['base_price']
        
        # Calculate entry prices
        price1 = base_price * 1.05
        price2 = base_price * 1.10
        price3 = base_price * 1.15
        
        # Check Part 1
        if not state['part1_taken'] and high_price >= price1:
            state['part1_taken'] = True
            state['entry_prices'].append(price1)
            state['quantities'].append(33.33)
            
            logger.info(f"\n{'*'*60}")
            logger.info(f"ENTRY SIGNAL - PART 1")
            logger.info(f"{'*'*60}")
            logger.info(f"Instrument: {state['instrument']} {state['option_type'].upper()}")
            logger.info(f"Entry Price: ₹{price1:.2f}")
            logger.info(f"Quantity: 33.33% of allocated capital")
            logger.info(f"Time: {datetime.now(self.ist).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'*'*60}\n")
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.send_entry_signal(
                    state['instrument'], state['option_type'], 1, price1, 33.33
                )
        
        # Check Part 2
        if state['part1_taken'] and not state['part2_taken'] and high_price >= price2:
            state['part2_taken'] = True
            state['entry_prices'].append(price2)
            state['quantities'].append(33.33)
            
            logger.info(f"\n{'*'*60}")
            logger.info(f"ENTRY SIGNAL - PART 2")
            logger.info(f"{'*'*60}")
            logger.info(f"Instrument: {state['instrument']} {state['option_type'].upper()}")
            logger.info(f"Entry Price: ₹{price2:.2f}")
            logger.info(f"Quantity: 33.33% of allocated capital")
            logger.info(f"Time: {datetime.now(self.ist).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'*'*60}\n")
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.send_entry_signal(
                    state['instrument'], state['option_type'], 2, price2, 33.33
                )
        
        # Check Part 3
        if state['part2_taken'] and not state['part3_taken'] and high_price >= price3:
            state['part3_taken'] = True
            state['entry_prices'].append(price3)
            state['quantities'].append(33.34)  # Remaining
            
            logger.info(f"\n{'*'*60}")
            logger.info(f"ENTRY SIGNAL - PART 3 (FINAL)")
            logger.info(f"{'*'*60}")
            logger.info(f"Instrument: {state['instrument']} {state['option_type'].upper()}")
            logger.info(f"Entry Price: ₹{price3:.2f}")
            logger.info(f"Quantity: 33.34% of allocated capital")
            logger.info(f"Time: {datetime.now(self.ist).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'*'*60}\n")
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.send_entry_signal(
                    state['instrument'], state['option_type'], 3, price3, 33.34
                )
    
    def check_exit_levels(self, current_price: float):
        """
        Check if stop loss or target is hit
        
        Args:
            current_price: Current option price
        """
        if not self.position_state['cycle_active']:
            return
        
        state = self.position_state
        
        # Only check exits if at least one entry is taken
        if not (state['part1_taken'] or state['part2_taken'] or state['part3_taken']):
            return
        
        # Calculate average entry price
        total_qty = sum(state['quantities'])
        if total_qty == 0:
            return
        
        avg_price = sum(p * q for p, q in zip(state['entry_prices'], state['quantities'])) / total_qty
        
        # For short positions: higher price = loss, lower price = profit
        stop_price = avg_price * (1 + self.stop_loss_pct)
        target_price = avg_price * (1 - self.target_pct)
        
        # Check stop loss
        if current_price >= stop_price:
            loss_pct = ((current_price - avg_price) / avg_price) * 100
            
            logger.info(f"\n{'!'*60}")
            logger.info(f"STOP LOSS HIT")
            logger.info(f"{'!'*60}")
            logger.info(f"Instrument: {state['instrument']} {state['option_type'].upper()}")
            logger.info(f"Average Entry: ₹{avg_price:.2f}")
            logger.info(f"Exit Price: ₹{current_price:.2f}")
            logger.info(f"Loss: {loss_pct:.2f}%")
            logger.info(f"Time: {datetime.now(self.ist).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'!'*60}\n")
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.send_stop_loss_hit(
                    state['instrument'], state['option_type'],
                    avg_price, current_price, loss_pct
                )
            
            self.reset_position()
        
        # Check target
        elif current_price <= target_price:
            profit_pct = ((avg_price - current_price) / avg_price) * 100
            
            logger.info(f"\n{'$'*60}")
            logger.info(f"TARGET HIT - PROFIT BOOKED")
            logger.info(f"{'$'*60}")
            logger.info(f"Instrument: {state['instrument']} {state['option_type'].upper()}")
            logger.info(f"Average Entry: ₹{avg_price:.2f}")
            logger.info(f"Exit Price: ₹{current_price:.2f}")
            logger.info(f"Profit: {profit_pct:.2f}%")
            logger.info(f"Time: {datetime.now(self.ist).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'$'*60}\n")
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.send_target_hit(
                    state['instrument'], state['option_type'],
                    avg_price, current_price, profit_pct
                )
            
            self.reset_position()
    
    def reset_position(self):
        """Reset position state after exit"""
        self.position_state = {
            'instrument': None,
            'option_type': None,
            'base_price': None,
            'entry_prices': [],
            'quantities': [],
            'part1_taken': False,
            'part2_taken': False,
            'part3_taken': False,
            'cycle_active': False
        }
    
    def force_close_eod(self):
        """Force close position at end of day"""
        if self.position_state['cycle_active']:
            logger.info(f"\n{'#'*60}")
            logger.info(f"FORCE CLOSE - END OF DAY (3:15 PM)")
            logger.info(f"{'#'*60}")
            logger.info(f"Instrument: {self.position_state['instrument']} "
                       f"{self.position_state['option_type'].upper()}")
            logger.info(f"Time: {datetime.now(self.ist).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'#'*60}\n")
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.send_eod_close(
                    self.position_state['instrument'],
                    self.position_state['option_type']
                )
            
            self.reset_position()
    
    def process_tick(self, instrument: str, option_type: str, 
                     ltp: float, high: float):
        """
        Process incoming tick data
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            ltp: Last traded price
            high: High of current minute candle
        """
        now = datetime.now(self.ist)
        
        # Update option data
        self.update_option_data(instrument, option_type, ltp, now)
        
        # Get current RSI
        rsi_values = self.option_data[instrument][option_type]['rsi']
        if len(rsi_values) == 0:
            return
        
        current_rsi = rsi_values[-1]
        
        # Check for new signal (RSI crossover)
        if self.check_rsi_crossover(instrument, option_type) and self.is_trading_hours():
            self.generate_signal(instrument, option_type, ltp, current_rsi)
        
        # If position is active on this instrument and option type
        if (self.position_state['cycle_active'] and 
            self.position_state['instrument'] == instrument and
            self.position_state['option_type'] == option_type):
            
            # Check entry levels
            self.check_entry_levels(ltp, high)
            
            # Check exit levels
            self.check_exit_levels(ltp)
        
        # Force close at 3:15 PM
        if now.time() >= self.end_time:
            self.force_close_eod()


def main():
    """
    Main function to run the strategy
    Note: This is a template - you need to integrate with actual Dhan API
    """
    
    # Strategy configuration
    config = {
        'rsi_length': 14,
        'stop_loss_pct': 20,
        'target_pct': 10
    }
    
    # Initialize Dhan client (placeholder - replace with actual implementation)
    # from dhanhq import dhanhq
    # dhan = dhanhq("client_id", "access_token")
    
    dhan = None  # Replace with actual Dhan client
    
    # Initialize strategy
    strategy = RSIOptionsStrategy(dhan, config)
    
    logger.info("RSI Options Strategy Started")
    logger.info(f"Monitoring: {', '.join(strategy.instruments)}")
    logger.info(f"Trading Hours: {strategy.start_time} to {strategy.end_time} IST")
    logger.info(f"RSI Length: {strategy.rsi_length}")
    logger.info(f"Stop Loss: {strategy.stop_loss_pct * 100}%")
    logger.info(f"Target: {strategy.target_pct * 100}%")
    logger.info("="*60 + "\n")
    
    # Main loop - replace with actual data feed integration
    # This is a placeholder structure
    try:
        while True:
            # Check if trading hours
            if not strategy.is_trading_hours():
                time_module.sleep(60)
                continue
            
            # TODO: Fetch live option prices from Dhan API
            # For each instrument:
            #   1. Get spot price
            #   2. Calculate ATM strike
            #   3. Get ATM call and put option prices
            #   4. Process the tick data
            
            # Example (replace with actual API calls):
            # for instrument in strategy.instruments:
            #     spot_price = get_spot_price(instrument)
            #     atm_strike = strategy.get_atm_strike(spot_price, instrument)
            #     expiry = strategy.get_weekly_expiry()
            #     
            #     call_price = get_option_price(instrument, atm_strike, expiry, 'CE')
            #     put_price = get_option_price(instrument, atm_strike, expiry, 'PE')
            #     
            #     strategy.process_tick(instrument, 'call', call_price, call_price)
            #     strategy.process_tick(instrument, 'put', put_price, put_price)
            
            time_module.sleep(60)  # 1-minute interval
            
    except KeyboardInterrupt:
        logger.info("\nStrategy stopped by user")
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)


if __name__ == "__main__":
    main()
