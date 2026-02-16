"""
Dhan API Integration Module
Handles live data feed for options and spot prices
Updated for dhanhq v2.0.2 API
"""

from dhanhq import dhanhq
import pandas as pd
from datetime import datetime, timedelta
import pytz
import logging
from typing import Dict, List, Optional, Tuple
import time

logger = logging.getLogger(__name__)


class DhanDataFeed:
    """
    Manages live data feed from Dhan API
    Fetches spot prices and option chain data
    
    Note: Uses dhanhq v2.0.2 API methods:
    - ticker_data() for LTP
    - ohlc_data() for OHLC
    - quote_data() for full market depth
    """
    
    # Security IDs for instruments (Integer IDs as per Dhan API)
    # These are the actual security IDs from Dhan
    SECURITY_IDS = {
        'NIFTY': {'exchange': 'IDX_I', 'security_id': 13},        # Nifty 50 Index
        'SENSEX': {'exchange': 'IDX_I', 'security_id': 51},       # Sensex Index
        'BANKNIFTY': {'exchange': 'IDX_I', 'security_id': 25},    # Bank Nifty Index
        'RELIANCE': {'exchange': 'NSE_EQ', 'security_id': 2885},  # Reliance Stock
        'HDFCBANK': {'exchange': 'NSE_EQ', 'security_id': 1333}   # HDFC Bank Stock
    }
    
    def __init__(self, client_id: str, access_token: str):
        """
        Initialize Dhan client
        
        Args:
            client_id: Dhan client ID
            access_token: Dhan access token
        """
        # Initialize Dhan client with v2.0.2 API (no DhanContext needed)
        self.dhan = dhanhq(client_id, access_token)
        self.ist = pytz.timezone('Asia/Kolkata')
        
        # Cache for option symbols and security IDs
        self.option_symbols_cache = {}
        
        # Security list DataFrame (loaded on demand)
        self.security_list_df = None
        self.security_list_loaded = False
        
        # Rate limiting - track last API call time
        self.last_api_call = 0
        self.min_api_interval = 1.0  # Minimum 1 second between API calls
        
        logger.info("Dhan API client initialized (v2.0.2)")
    
    def _rate_limit(self):
        """
        Enforce rate limiting - wait if needed
        API limit: 1 request per second
        """
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        
        if time_since_last_call < self.min_api_interval:
            sleep_time = self.min_api_interval - time_since_last_call
            time.sleep(sleep_time)
        
        self.last_api_call = time.time()
    
    def get_spot_price(self, instrument: str) -> Optional[float]:
        """
        Get current spot price for an instrument
        
        Args:
            instrument: Instrument name (NIFTY, SENSEX, BANKNIFTY, etc.)
            
        Returns:
            Current spot price or None if error
        """
        try:
            # Get security info
            security_info = self.SECURITY_IDS.get(instrument)
            if not security_info:
                logger.error(f"Security ID not found for {instrument}")
                return None
            
            # Apply rate limiting
            self._rate_limit()
            
            # Get LTP using ticker_data API
            # API expects: {'EXCHANGE': [security_id1, security_id2, ...]}
            response = self.dhan.ticker_data(
                securities={
                    security_info['exchange']: [security_info['security_id']]
                }
            )
            
            # Response structure: 
            # {'status': 'success', 'remarks': '', 'data': {'data': {'IDX_I': {'13': {'last_price': 25471.1}}}, 'status': 'success'}}
            if response and response.get('status') == 'success':
                # Navigate through nested 'data' structure
                outer_data = response.get('data', {})
                inner_data = outer_data.get('data', {})
                exchange_data = inner_data.get(security_info['exchange'], {})
                security_data = exchange_data.get(str(security_info['security_id']), {})
                ltp = security_data.get('last_price')
                
                if ltp:
                    logger.info(f"Fetched {instrument} spot price: ₹{ltp}")
                    return float(ltp)
            
            logger.warning(f"No LTP data found for {instrument}. Response: {response}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching spot price for {instrument}: {e}")
            return None
    
    def get_weekly_expiry(self, instrument: str) -> str:
        """
        Get next weekly expiry date from Dhan API
        
        Uses Dhan's expiry_list API to get accurate expiry dates
        instead of calculating them (which can be inaccurate due to holidays)
        
        Args:
            instrument: Instrument name (NIFTY, BANKNIFTY, etc.)
            
        Returns:
            Expiry date in DD-MMM-YYYY format (e.g., '17-FEB-2026')
        """
        try:
            # Get security info for the underlying
            security_info = self.SECURITY_IDS.get(instrument)
            if not security_info:
                logger.error(f"Security ID not found for {instrument}")
                return self._calculate_expiry_fallback(instrument)
            
            # Apply rate limiting
            self._rate_limit()
            
            # Get expiry list from Dhan API
            response = self.dhan.expiry_list(
                under_security_id=security_info['security_id'],
                under_exchange_segment=security_info['exchange']
            )
            
            if response and response.get('status') == 'success':
                expiry_dates = response.get('data', {}).get('data', [])
                
                if expiry_dates and len(expiry_dates) > 0:
                    # Get the first (nearest) expiry date
                    # Format is 'YYYY-MM-DD', convert to 'DD-MMM-YYYY'
                    next_expiry = expiry_dates[0]
                    expiry_date = datetime.strptime(next_expiry, '%Y-%m-%d')
                    return expiry_date.strftime('%d-%b-%Y').upper()
            
            # Fallback to calculation if API fails
            logger.warning(f"Could not fetch expiry from API, using calculation")
            return self._calculate_expiry_fallback(instrument)
            
        except Exception as e:
            logger.error(f"Error fetching expiry for {instrument}: {e}")
            return self._calculate_expiry_fallback(instrument)
    
    def _calculate_expiry_fallback(self, instrument: str) -> str:
        """
        Fallback method to calculate expiry when API is unavailable
        
        Note: This may be inaccurate due to holidays
        
        Args:
            instrument: Instrument name
            
        Returns:
            Expiry date in DD-MMM-YYYY format
        """
        today = datetime.now(self.ist).date()
        
        # Different expiry days for different instruments
        if instrument in ['NIFTY', 'BANKNIFTY']:
            # Thursday expiry
            target_weekday = 3  # Thursday
        elif instrument == 'SENSEX':
            # Friday expiry
            target_weekday = 4  # Friday
        else:
            # Monthly expiry for stocks (last Thursday)
            return self.get_monthly_expiry()
        
        # Calculate days until next expiry
        days_ahead = (target_weekday - today.weekday()) % 7
        
        # If today is expiry day and time is past 3:30 PM, get next week
        if days_ahead == 0:
            current_time = datetime.now(self.ist).time()
            if current_time.hour >= 15 and current_time.minute >= 30:
                days_ahead = 7
        
        expiry_date = today + timedelta(days=days_ahead)
        
        # Format: DD-MMM-YYYY (e.g., 15-FEB-2026)
        return expiry_date.strftime('%d-%b-%Y').upper()
    
    def get_monthly_expiry(self) -> str:
        """
        Get monthly expiry (last Thursday of the month)
        
        Returns:
            Expiry date in DD-MMM-YYYY format
        """
        today = datetime.now(self.ist).date()
        
        # Get last day of current month
        if today.month == 12:
            last_day = datetime(today.year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(today.year, today.month + 1, 1).date() - timedelta(days=1)
        
        # Find last Thursday
        while last_day.weekday() != 3:  # Thursday = 3
            last_day -= timedelta(days=1)
        
        return last_day.strftime('%d-%b-%Y').upper()
    
    def get_atm_strike(self, spot_price: float, instrument: str) -> int:
        """
        Calculate ATM strike based on spot price
        
        Args:
            spot_price: Current spot price
            instrument: Instrument name
            
        Returns:
            ATM strike price
        """
        # Strike rounding intervals
        rounding_map = {
            'NIFTY': 50,
            'BANKNIFTY': 100,
            'SENSEX': 100,
            'RELIANCE': 5,
            'HDFCBANK': 10
        }
        
        rounding = rounding_map.get(instrument, 50)
        atm_strike = round(spot_price / rounding) * rounding
        
        return int(atm_strike)
    
    def _load_security_list(self):
        """
        Load security list from Dhan API
        This is called on-demand and cached for the session
        """
        if self.security_list_loaded:
            return
        
        try:
            logger.info("Loading security list from Dhan API (this may take a few seconds)...")
            # Fetch security list - returns a DataFrame
            self.security_list_df = self.dhan.fetch_security_list('compact')
            self.security_list_loaded = True
            logger.info(f"Security list loaded: {len(self.security_list_df)} instruments")
        except Exception as e:
            logger.error(f"Error loading security list: {e}")
            self.security_list_loaded = False
    
    def get_option_security_id(self, instrument: str, strike: int, 
                                expiry: str, option_type: str) -> Optional[int]:
        """
        Get security ID for an option contract
        
        Searches Dhan's security list for the matching option contract
        and caches the result for future use
        
        Args:
            instrument: Instrument name (NIFTY, BANKNIFTY, etc.)
            strike: Strike price (integer)
            expiry: Expiry date in DD-MMM-YYYY format (e.g., '19-FEB-2026')
            option_type: 'CE' for call, 'PE' for put
            
        Returns:
            Security ID (integer) or None if not found
        """
        # Cache key for this option
        cache_key = f"{instrument}_{strike}_{expiry}_{option_type}"
        
        # Check cache first
        if cache_key in self.option_symbols_cache:
            return self.option_symbols_cache[cache_key]
        
        # Load security list if not already loaded
        self._load_security_list()
        
        if self.security_list_df is None:
            logger.error("Security list not available")
            return None
        
        try:
            # Convert expiry from DD-MMM-YYYY to YYYY-MM-DD for matching
            # e.g., '19-FEB-2026' -> '2026-02-19'
            expiry_date = datetime.strptime(expiry, '%d-%b-%Y')
            expiry_str = expiry_date.strftime('%Y-%m-%d')
            
            # Search for the option in security list
            # Filter by: instrument name, strike price, expiry date, option type
            filtered = self.security_list_df[
                (self.security_list_df['SEM_TRADING_SYMBOL'].str.contains(instrument, na=False, case=False)) &
                (self.security_list_df['SEM_STRIKE_PRICE'] == float(strike)) &
                (self.security_list_df['SEM_EXPIRY_DATE'].str.contains(expiry_str, na=False)) &
                (self.security_list_df['SEM_OPTION_TYPE'] == option_type)
            ]
            
            if len(filtered) == 0:
                logger.warning(f"No security found for {instrument} {strike} {expiry} {option_type}")
                return None
            
            # If multiple matches, take the first one (usually NSE)
            if len(filtered) > 1:
                # Prefer NSE over BSE
                nse_options = filtered[filtered['SEM_EXM_EXCH_ID'] == 'NSE']
                if len(nse_options) > 0:
                    filtered = nse_options
            
            security_id = int(filtered.iloc[0]['SEM_SMST_SECURITY_ID'])
            
            # Cache the result
            self.option_symbols_cache[cache_key] = security_id
            
            logger.info(f"Found security ID {security_id} for {instrument} {strike} {expiry} {option_type}")
            return security_id
            
        except Exception as e:
            logger.error(f"Error looking up security ID for {cache_key}: {e}")
            return None
    
    def get_option_price(self, instrument: str, strike: int, 
                        expiry: str, option_type: str) -> Optional[Dict]:
        """
        Get option price and OHLC data
        
        Uses Dhan's ohlc_data API to fetch current option prices
        
        Args:
            instrument: Instrument name (NIFTY, BANKNIFTY, etc.)
            strike: Strike price (integer)
            expiry: Expiry date in DD-MMM-YYYY format (e.g., '19-FEB-2026')
            option_type: 'CE' for call, 'PE' for put
            
        Returns:
            Dictionary with LTP, high, low, open or None if error
        """
        try:
            # Get security ID for this option
            security_id = self.get_option_security_id(instrument, strike, expiry, option_type)
            
            if not security_id:
                logger.error(f"Could not find security ID for {instrument} {strike} {expiry} {option_type}")
                return None
            
            # Determine exchange segment for options
            # NSE_FNO = NSE Futures & Options
            # BSE_FNO = BSE Futures & Options
            if instrument in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY']:
                exchange = 'NSE_FNO'
            elif instrument == 'SENSEX':
                exchange = 'BSE_FNO'
            else:
                # Stock options are on NSE_FNO
                exchange = 'NSE_FNO'
            
            # Apply rate limiting
            self._rate_limit()
            
            # Get OHLC data using ohlc_data API
            response = self.dhan.ohlc_data(
                securities={exchange: [security_id]}
            )
            
            # Parse response
            # Response structure: {'status': 'success', 'data': {'data': {'NSE_FNO': {'48211': {'last_price': 100.5, 'ohlc': {...}}}}}}
            if response and response.get('status') == 'success':
                outer_data = response.get('data', {})
                inner_data = outer_data.get('data', {})
                exchange_data = inner_data.get(exchange, {})
                security_data = exchange_data.get(str(security_id), {})
                
                if security_data:
                    ohlc = security_data.get('ohlc', {})
                    ltp = security_data.get('last_price', 0)
                    
                    return {
                        'ltp': float(ltp) if ltp else 0.0,
                        'high': float(ohlc.get('high', 0)),
                        'low': float(ohlc.get('low', 0)),
                        'open': float(ohlc.get('open', 0)),
                        'volume': 0,  # Not available in ohlc_data, use quote_data for this
                        'oi': 0       # Not available in ohlc_data, use quote_data for this
                    }
                else:
                    logger.warning(f"No data found for security ID {security_id}")
            else:
                logger.warning(f"API returned failure: {response}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching option price: {e}", exc_info=True)
            return None
    
    def get_option_chain(self, instrument: str, spot_price: float, 
                        expiry: str, num_strikes: int = 5) -> Optional[pd.DataFrame]:
        """
        Get option chain data for ATM strikes
        
        Note: Uses Dhan's option_chain API which is more efficient
        than fetching individual options
        
        Args:
            instrument: Instrument name
            spot_price: Current spot price
            expiry: Expiry date (YYYY-MM-DD format)
            num_strikes: Number of strikes above and below ATM (not used with Dhan API)
            
        Returns:
            DataFrame with option chain or None
        """
        try:
            # Get security info for the underlying
            security_info = self.SECURITY_IDS.get(instrument)
            if not security_info:
                logger.error(f"Security ID not found for {instrument}")
                return None
            
            # Apply rate limiting
            self._rate_limit()
            
            # Use Dhan's option_chain API
            # Note: expiry should be in YYYY-MM-DD format
            response = self.dhan.option_chain(
                under_security_id=security_info['security_id'],
                under_exchange_segment=security_info['exchange'],
                expiry=expiry
            )
            
            # Parse response and convert to DataFrame
            if response and response.get('status') == 'success':
                data = response.get('data', [])
                if data:
                    return pd.DataFrame(data)
            
            logger.warning(f"No option chain data found for {instrument}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching option chain for {instrument}: {e}")
            return None
    
    def get_historical_data(self, instrument: str, strike: int, 
                           expiry: str, option_type: str,
                           from_date: str, to_date: str,
                           interval: str = '1') -> Optional[pd.DataFrame]:
        """
        Get historical intraday data for an option
        
        Note: Requires security ID for the option
        
        Args:
            instrument: Instrument name
            strike: Strike price
            expiry: Expiry date
            option_type: 'CE' or 'PE'
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: '1' for 1-min, '5' for 5-min, etc.
            
        Returns:
            DataFrame with OHLC data
        """
        try:
            # Get security ID for this option
            security_id = self.get_option_security_id(instrument, strike, expiry, option_type)
            
            if not security_id:
                logger.error(f"Could not find security ID for option")
                return None
            
            # Determine exchange and instrument type
            if instrument in ['NIFTY', 'BANKNIFTY']:
                exchange = 'NSE_FNO'
                instrument_type = 'OPTIDX'
            elif instrument == 'SENSEX':
                exchange = 'BSE_FNO'
                instrument_type = 'OPTIDX'
            else:
                exchange = 'NSE_FNO'
                instrument_type = 'OPTSTK'
            
            # Apply rate limiting
            self._rate_limit()
            
            # Get historical data using intraday_minute_data API
            response = self.dhan.intraday_minute_data(
                security_id=str(security_id),
                exchange_segment=exchange,
                instrument_type=instrument_type,
                from_date=from_date,
                to_date=to_date
            )
            
            # Parse response
            if response and response.get('status') == 'success':
                data = response.get('data', [])
                if data:
                    df = pd.DataFrame(data)
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                    return df
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None


# Example usage and testing
if __name__ == "__main__":
    import os
    
    # Load credentials from .env.local file
    env_file = '.env.local'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value
    
    CLIENT_ID = os.getenv("CLIENT_ID", "your_client_id")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "your_access_token")
    
    if CLIENT_ID == "your_client_id" or ACCESS_TOKEN == "your_access_token":
        print("ERROR: Please set CLIENT_ID and ACCESS_TOKEN in .env.local file")
        exit(1)
    
    print("="*60)
    print("TESTING DHAN DATA FEED (v2.0.2)")
    print("="*60)
    
    # Create data feed instance
    feed = DhanDataFeed(CLIENT_ID, ACCESS_TOKEN)
    
    # Test 1: Spot price fetch
    print("\n[TEST 1] Fetching spot prices...")
    print("-" * 60)
    
    for instrument in ['NIFTY', 'BANKNIFTY', 'SENSEX']:
        spot = feed.get_spot_price(instrument)
        if spot:
            print(f"✓ {instrument:12} Spot: ₹{spot:,.2f}")
        else:
            print(f"✗ {instrument:12} Failed to fetch spot price")
    
    # Test 2: Expiry calculation
    print("\n[TEST 2] Calculating expiry dates...")
    print("-" * 60)
    
    for instrument in ['NIFTY', 'BANKNIFTY', 'SENSEX']:
        expiry = feed.get_weekly_expiry(instrument)
        print(f"{instrument:12} Next Expiry: {expiry}")
    
    # Test 3: ATM strike calculation
    print("\n[TEST 3] Calculating ATM strikes...")
    print("-" * 60)
    
    nifty_spot = feed.get_spot_price('NIFTY')
    if nifty_spot:
        atm = feed.get_atm_strike(nifty_spot, 'NIFTY')
        print(f"NIFTY Spot: ₹{nifty_spot:,.2f}")
        print(f"ATM Strike: {atm}")
        print(f"Strike Rounding: 50")
    
    # Test 4: Option chain (if market is open)
    print("\n[TEST 4] Fetching option chain...")
    print("-" * 60)
    print("Note: Option chain requires market to be open")
    print("Skipping option chain test (market closed on Sunday)")
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)
    print("\nNotes:")
    print("- Market is closed on weekends")
    print("- Option prices will only work during market hours")
    print("- Rate limiting: 1 request per second")
    print("="*60)