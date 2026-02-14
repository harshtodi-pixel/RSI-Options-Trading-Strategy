"""
Telegram Notification Module
Sends trading signals and alerts to Telegram
"""

import requests
import logging
from typing import Optional, Dict, List
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Handles sending notifications to Telegram
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Your Telegram chat ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.ist = pytz.timezone('Asia/Kolkata')
        
        # Test connection
        if self.test_connection():
            logger.info("✅ Telegram notifications enabled")
        else:
            logger.warning("⚠️ Telegram connection test failed")
    
    def test_connection(self) -> bool:
        """
        Test Telegram bot connection
        
        Returns:
            True if connection successful
        """
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_name = data.get('result', {}).get('username', 'Unknown')
                    logger.info(f"Connected to Telegram bot: @{bot_name}")
                    return True
            
            logger.error(f"Telegram API error: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message to Telegram
        
        Args:
            message: Message text (supports HTML formatting)
            parse_mode: 'HTML' or 'Markdown'
            
        Returns:
            True if sent successfully
        """
        try:
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_new_signal(self, instrument: str, option_type: str, 
                       base_price: float, rsi: float,
                       entry_levels: Dict[str, float]) -> bool:
        """
        Send new signal notification
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            base_price: Base price when signal generated
            rsi: RSI value
            entry_levels: Dictionary with entry prices
            
        Returns:
            True if sent successfully
        """
        time_str = datetime.now(self.ist).strftime('%d-%b-%Y %H:%M:%S')
        
        message = f"""
🔔 <b>NEW SIGNAL GENERATED</b> 🔔

📊 <b>Instrument:</b> {instrument}
📈 <b>Option:</b> {option_type.upper()}
💰 <b>Base Price:</b> ₹{base_price:.2f}
📉 <b>RSI:</b> {rsi:.2f}
⏰ <b>Time:</b> {time_str}

<b>📍 Entry Levels:</b>
├ Part 1 (33.33%): ₹{entry_levels['part1']:.2f} (+5%)
├ Part 2 (33.33%): ₹{entry_levels['part2']:.2f} (+10%)
└ Part 3 (33.34%): ₹{entry_levels['part3']:.2f} (+15%)

<i>Position Type: SELL {option_type.upper()}</i>
        """
        
        return self.send_message(message)
    
    def send_entry_signal(self, instrument: str, option_type: str,
                         part: int, entry_price: float, quantity_pct: float) -> bool:
        """
        Send entry signal notification
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            part: Entry part number (1, 2, or 3)
            entry_price: Entry price
            quantity_pct: Quantity percentage
            
        Returns:
            True if sent successfully
        """
        time_str = datetime.now(self.ist).strftime('%d-%b-%Y %H:%M:%S')
        
        emoji_map = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣"}
        emoji = emoji_map.get(part, "✅")
        
        message = f"""
{emoji} <b>ENTRY SIGNAL - PART {part}</b>

📊 <b>Instrument:</b> {instrument} {option_type.upper()}
💰 <b>Entry Price:</b> ₹{entry_price:.2f}
📦 <b>Quantity:</b> {quantity_pct:.2f}% of capital
⏰ <b>Time:</b> {time_str}

<i>Action: SELL at ₹{entry_price:.2f}</i>
        """
        
        return self.send_message(message)
    
    def send_target_hit(self, instrument: str, option_type: str,
                       avg_entry: float, exit_price: float,
                       profit_pct: float) -> bool:
        """
        Send target hit notification
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            avg_entry: Average entry price
            exit_price: Exit price
            profit_pct: Profit percentage
            
        Returns:
            True if sent successfully
        """
        time_str = datetime.now(self.ist).strftime('%d-%b-%Y %H:%M:%S')
        
        message = f"""
🎯 <b>TARGET HIT - PROFIT BOOKED</b> 💰

📊 <b>Instrument:</b> {instrument} {option_type.upper()}
📥 <b>Avg Entry:</b> ₹{avg_entry:.2f}
📤 <b>Exit Price:</b> ₹{exit_price:.2f}
💵 <b>Profit:</b> +{profit_pct:.2f}%
⏰ <b>Time:</b> {time_str}

<i>✅ Position closed successfully!</i>
        """
        
        return self.send_message(message)
    
    def send_stop_loss_hit(self, instrument: str, option_type: str,
                          avg_entry: float, exit_price: float,
                          loss_pct: float) -> bool:
        """
        Send stop loss hit notification
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            avg_entry: Average entry price
            exit_price: Exit price
            loss_pct: Loss percentage
            
        Returns:
            True if sent successfully
        """
        time_str = datetime.now(self.ist).strftime('%d-%b-%Y %H:%M:%S')
        
        message = f"""
⚠️ <b>STOP LOSS HIT</b> ⚠️

📊 <b>Instrument:</b> {instrument} {option_type.upper()}
📥 <b>Avg Entry:</b> ₹{avg_entry:.2f}
📤 <b>Exit Price:</b> ₹{exit_price:.2f}
📉 <b>Loss:</b> -{loss_pct:.2f}%
⏰ <b>Time:</b> {time_str}

<i>⛔ Position stopped out</i>
        """
        
        return self.send_message(message)
    
    def send_eod_close(self, instrument: str, option_type: str) -> bool:
        """
        Send end-of-day force close notification
        
        Args:
            instrument: Instrument name
            option_type: 'call' or 'put'
            
        Returns:
            True if sent successfully
        """
        time_str = datetime.now(self.ist).strftime('%d-%b-%Y %H:%M:%S')
        
        message = f"""
🔚 <b>FORCE CLOSE - END OF DAY</b>

📊 <b>Instrument:</b> {instrument} {option_type.upper()}
⏰ <b>Time:</b> {time_str}

<i>Position closed at 3:15 PM</i>
        """
        
        return self.send_message(message)
    
    def send_bot_started(self, instruments: List[str], config: Dict) -> bool:
        """
        Send bot started notification
        
        Args:
            instruments: List of instruments being monitored
            config: Strategy configuration
            
        Returns:
            True if sent successfully
        """
        time_str = datetime.now(self.ist).strftime('%d-%b-%Y %H:%M:%S')
        
        instruments_str = ", ".join(instruments)
        
        message = f"""
🤖 <b>TRADING BOT STARTED</b> 🚀

📊 <b>Instruments:</b> {instruments_str}
📈 <b>RSI Length:</b> {config.get('rsi_length', 14)}
🛑 <b>Stop Loss:</b> {config.get('stop_loss_pct', 20)}%
🎯 <b>Target:</b> {config.get('target_pct', 10)}%
⏰ <b>Started At:</b> {time_str}

<i>Monitoring for RSI signals...</i>
        """
        
        return self.send_message(message)
    
    def send_bot_stopped(self) -> bool:
        """
        Send bot stopped notification
        
        Returns:
            True if sent successfully
        """
        time_str = datetime.now(self.ist).strftime('%d-%b-%Y %H:%M:%S')
        
        message = f"""
🛑 <b>TRADING BOT STOPPED</b>

⏰ <b>Stopped At:</b> {time_str}

<i>Bot has been shut down</i>
        """
        
        return self.send_message(message)
    
    def send_error_alert(self, error_type: str, error_message: str) -> bool:
        """
        Send error alert notification
        
        Args:
            error_type: Type of error
            error_message: Error message
            
        Returns:
            True if sent successfully
        """
        time_str = datetime.now(self.ist).strftime('%d-%b-%Y %H:%M:%S')
        
        message = f"""
❌ <b>ERROR ALERT</b>

🔴 <b>Type:</b> {error_type}
📝 <b>Message:</b> {error_message}
⏰ <b>Time:</b> {time_str}

<i>Please check the bot!</i>
        """
        
        return self.send_message(message)
    
    def send_atm_update(self, instrument: str, old_strike: int, 
                       new_strike: int, spot: float) -> bool:
        """
        Send ATM strike update notification
        
        Args:
            instrument: Instrument name
            old_strike: Old ATM strike
            new_strike: New ATM strike
            spot: Current spot price
            
        Returns:
            True if sent successfully
        """
        time_str = datetime.now(self.ist).strftime('%d-%b-%Y %H:%M:%S')
        
        message = f"""
🔄 <b>ATM STRIKE UPDATED</b>

📊 <b>Instrument:</b> {instrument}
📍 <b>Old Strike:</b> {old_strike}
🆕 <b>New Strike:</b> {new_strike}
💹 <b>Spot Price:</b> ₹{spot:.2f}
⏰ <b>Time:</b> {time_str}
        """
        
        return self.send_message(message)
    
    def send_daily_summary(self, summary: Dict) -> bool:
        """
        Send daily trading summary
        
        Args:
            summary: Dictionary with daily statistics
            
        Returns:
            True if sent successfully
        """
        date_str = datetime.now(self.ist).strftime('%d-%b-%Y')
        
        message = f"""
📊 <b>DAILY SUMMARY - {date_str}</b>

📈 <b>Total Signals:</b> {summary.get('total_signals', 0)}
✅ <b>Profitable Trades:</b> {summary.get('winning_trades', 0)}
❌ <b>Loss Trades:</b> {summary.get('losing_trades', 0)}
💰 <b>Total P&L:</b> {summary.get('total_pnl', 0):.2f}%
📊 <b>Win Rate:</b> {summary.get('win_rate', 0):.2f}%

<i>End of day summary</i>
        """
        
        return self.send_message(message)


# Utility function to get chat ID
def get_telegram_chat_id(bot_token: str) -> Optional[str]:
    """
    Helper function to get your Telegram chat ID
    
    Steps:
    1. Start a chat with your bot on Telegram
    2. Send any message to your bot
    3. Run this function
    4. It will return your chat ID
    
    Args:
        bot_token: Your bot token from BotFather
        
    Returns:
        Chat ID as string or None
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                updates = data['result']
                if updates:
                    # Get the most recent message
                    latest_update = updates[-1]
                    chat_id = latest_update.get('message', {}).get('chat', {}).get('id')
                    
                    if chat_id:
                        print(f"✅ Your Telegram Chat ID: {chat_id}")
                        return str(chat_id)
            
            print("❌ No messages found. Please send a message to your bot first.")
            return None
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting chat ID: {e}")
        return None


if __name__ == "__main__":
    """
    Test script for Telegram notifications
    """
    print("="*60)
    print("TELEGRAM NOTIFICATION TEST")
    print("="*60)
    
    # Get credentials from user
    print("\nStep 1: Create a Telegram Bot")
    print("- Open Telegram and search for @BotFather")
    print("- Send /newbot and follow instructions")
    print("- Copy the bot token provided")
    
    bot_token = input("\nEnter your bot token: ").strip()
    
    if not bot_token:
        print("❌ Bot token is required!")
        exit(1)
    
    print("\nStep 2: Get your Chat ID")
    print("- Start a chat with your bot")
    print("- Send any message to your bot")
    print("- Press Enter to continue...")
    input()
    
    chat_id = get_telegram_chat_id(bot_token)
    
    if not chat_id:
        print("❌ Could not get chat ID. Please try again.")
        exit(1)
    
    print(f"\n✅ Chat ID found: {chat_id}")
    print(f"\nAdd these to your config.py:")
    print(f"TELEGRAM_BOT_TOKEN = '{bot_token}'")
    print(f"TELEGRAM_CHAT_ID = '{chat_id}'")
    
    # Test notification
    print("\n" + "="*60)
    print("Sending test notification...")
    print("="*60)
    
    notifier = TelegramNotifier(bot_token, chat_id)
    
    # Send test message
    test_message = """
🧪 <b>TEST NOTIFICATION</b>

✅ Your Telegram bot is configured correctly!

You will receive trading signals here.
    """
    
    if notifier.send_message(test_message):
        print("✅ Test message sent successfully!")
        print("Check your Telegram to confirm.")
    else:
        print("❌ Failed to send test message.")
    
    print("\n" + "="*60)
