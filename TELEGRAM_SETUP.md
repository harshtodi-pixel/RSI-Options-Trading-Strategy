# Telegram Notifications Setup Guide

This guide will help you set up Telegram notifications for the RSI Options Trading Bot.

## 📱 What You'll Get

Your trading bot will send you Telegram messages for:
- 🔔 **New Signals** - When RSI crosses 70
- 📍 **Entry Alerts** - Part 1, 2, and 3 entries
- 🎯 **Target Hit** - When profit target is reached
- ⚠️ **Stop Loss** - When stop loss is triggered
- 🔚 **End of Day** - Force close at 3:15 PM
- 🔄 **ATM Updates** - When strike changes
- 🤖 **Bot Status** - Start/Stop notifications

## 🚀 Step-by-Step Setup

### Step 1: Create a Telegram Bot

1. Open Telegram on your phone or desktop
2. Search for `@BotFather` (it's an official Telegram bot)
3. Start a chat with BotFather
4. Send the command: `/newbot`
5. BotFather will ask for a name for your bot
   - Example: "My Trading Signals Bot"
6. BotFather will ask for a username (must end with 'bot')
   - Example: "my_trading_signals_bot"
7. BotFather will give you a **Bot Token** that looks like:
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
   ```
8. **SAVE THIS TOKEN** - You'll need it in Step 3

### Step 2: Get Your Chat ID

#### Option A: Using the Setup Script (Recommended)

1. Open terminal/command prompt
2. Navigate to your project folder
3. Run:
   ```bash
   python telegram_notifier.py
   ```
4. Follow the prompts:
   - Paste your bot token when asked
   - Start a chat with your bot on Telegram
   - Send any message to your bot (e.g., "Hello")
   - Press Enter in the terminal
5. The script will display your **Chat ID**
6. You'll also receive a test message on Telegram

#### Option B: Manual Method

1. Start a chat with your bot on Telegram
2. Send any message to your bot
3. Open this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":123456789}`
5. The number is your **Chat ID**

### Step 3: Configure the Bot

#### Using config.py (Recommended):

1. Open `config.py`
2. Find the Telegram section:
   ```python
   ENABLE_TELEGRAM_NOTIFICATIONS = True
   TELEGRAM_BOT_TOKEN = "your_telegram_bot_token_here"
   TELEGRAM_CHAT_ID = "your_telegram_chat_id_here"
   ```
3. Replace with your actual values:
   ```python
   ENABLE_TELEGRAM_NOTIFICATIONS = True
   TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890"
   TELEGRAM_CHAT_ID = "123456789"
   ```
4. Save the file

#### Or using trading_bot_runner.py directly:

1. Open `trading_bot_runner.py`
2. Find the `main()` function
3. Update these lines:
   ```python
   ENABLE_TELEGRAM = True
   TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890"
   TELEGRAM_CHAT_ID = "123456789"
   ```

### Step 4: Test the Setup

1. Run the bot:
   ```bash
   python trading_bot_runner.py
   ```
2. You should receive a "🤖 TRADING BOT STARTED" message on Telegram
3. If you receive this message, **setup is complete! ✅**

## 📨 Example Notifications

### New Signal
```
🔔 NEW SIGNAL GENERATED 🔔

📊 Instrument: NIFTY
📈 Option: CALL
💰 Base Price: ₹150.50
📉 RSI: 72.34
⏰ Time: 15-Feb-2026 10:30:00

📍 Entry Levels:
├ Part 1 (33.33%): ₹158.03 (+5%)
├ Part 2 (33.33%): ₹165.55 (+10%)
└ Part 3 (33.34%): ₹173.08 (+15%)

Position Type: SELL CALL
```

### Entry Signal
```
1️⃣ ENTRY SIGNAL - PART 1

📊 Instrument: NIFTY CALL
💰 Entry Price: ₹158.03
📦 Quantity: 33.33% of capital
⏰ Time: 15-Feb-2026 10:35:00

Action: SELL at ₹158.03
```

### Target Hit
```
🎯 TARGET HIT - PROFIT BOOKED 💰

📊 Instrument: NIFTY CALL
📥 Avg Entry: ₹165.54
📤 Exit Price: ₹148.99
💵 Profit: +10.00%
⏰ Time: 15-Feb-2026 11:15:00

✅ Position closed successfully!
```

### Stop Loss
```
⚠️ STOP LOSS HIT ⚠️

📊 Instrument: BANKNIFTY PUT
📥 Avg Entry: ₹220.50
📤 Exit Price: ₹264.60
📉 Loss: -20.00%
⏰ Time: 15-Feb-2026 14:25:00

⛔ Position stopped out
```

## 🔒 Security Tips

1. **Keep your bot token private** - Anyone with the token can send messages through your bot
2. **Don't share your chat ID** - This identifies your personal chat
3. **Bot is private** - Only you can interact with your bot (others can't see messages)
4. **Revoke token if compromised** - Contact @BotFather and use `/revoke`

## ❓ Troubleshooting

### Problem: "Telegram connection test failed"

**Solutions:**
- Check your bot token is correct
- Ensure there are no extra spaces in the token
- Make sure you copied the entire token

### Problem: "No messages found. Please send a message to your bot first"

**Solutions:**
- Open Telegram
- Search for your bot's username
- Click Start
- Send any message to your bot
- Run the setup script again

### Problem: Bot receives test message but not trading signals

**Solutions:**
- Check `ENABLE_TELEGRAM_NOTIFICATIONS = True` in config
- Restart the trading bot
- Check logs for any error messages

### Problem: "401 Unauthorized" error

**Solutions:**
- Your bot token is incorrect
- Get a new token from @BotFather
- Update config.py with the new token

### Problem: Messages arrive delayed

**Solutions:**
- This is normal - Telegram may have slight delays
- Critical signals still arrive within seconds
- Check your internet connection

## 🛠️ Advanced Configuration

### Disable Specific Notifications

Edit `rsi_options_strategy.py` and comment out unwanted notifications:

```python
# Disable ATM update notifications
# if self.telegram:
#     self.telegram.send_atm_update(...)
```

### Custom Message Format

Edit `telegram_notifier.py` to customize message templates:

```python
def send_new_signal(self, ...):
    message = f"""
    🔔 YOUR CUSTOM MESSAGE HERE
    ...
    """
```

### Multiple Chat IDs (Send to Group)

To send notifications to a Telegram group:

1. Add your bot to a Telegram group
2. Get the group chat ID (negative number, e.g., -123456789)
3. Update `TELEGRAM_CHAT_ID` with the group ID

## 📞 Support

If you encounter issues:

1. Run the test script: `python telegram_notifier.py`
2. Check the logs in `trading_bot.log`
3. Verify your bot token with @BotFather: `/token`
4. Try creating a new bot and starting fresh

## ✅ Checklist

Before running the bot, make sure:

- [ ] Created a bot with @BotFather
- [ ] Saved the bot token
- [ ] Started a chat with your bot
- [ ] Obtained your chat ID
- [ ] Updated config.py with token and chat ID
- [ ] Set `ENABLE_TELEGRAM_NOTIFICATIONS = True`
- [ ] Ran test script successfully
- [ ] Received test message on Telegram

---

**You're all set! Your trading signals will now be sent to Telegram! 📱📈**
