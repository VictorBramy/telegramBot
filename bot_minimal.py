"""
Emergency Minimal Bot - Cloud Stable Version
"""
import os
import logging
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

# Load environment variables
load_dotenv()

# Simple logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Try to import optional modules - graceful fallback
STOCK_AVAILABLE = False
NETWORK_AVAILABLE = False
IP_LOCATION_AVAILABLE = False
VULN_SCANNER_AVAILABLE = False
CRYPTO_ALERTS_AVAILABLE = False

try:
    from stock_analyzer import stock_analyzer, format_stock_analysis
    STOCK_AVAILABLE = True
    logger.info("Stock analysis loaded successfully")
except Exception as e:
    logger.warning(f"Stock analysis not available: {e}")

try:
    from crypto_alerts import (
        CryptoAlertManager, SimpleAlert, TechnicalAlert,
        parse_cooldown, get_indicators_list, SIMPLE_COMPARISONS, BINANCE_TIMEFRAMES
    )
    CRYPTO_ALERTS_AVAILABLE = True
    logger.info("Crypto alerts loaded successfully")
except Exception as e:
    logger.warning(f"Crypto alerts not available: {e}")

try:
    from network_tools import NetworkTools
    NETWORK_AVAILABLE = True
    logger.info("Network tools loaded successfully")
except Exception as e:
    logger.warning(f"Network tools not available: {e}")

try:
    from locate_ip import analyze_single_ip, geoip_ipapi, geoip_ipinfo
    IP_LOCATION_AVAILABLE = True
    logger.info("IP location tools loaded successfully")
except Exception as e:
    logger.warning(f"IP location tools not available: {e}")

try:
    from vulnerability_scanner import VulnerabilityScanner, format_vulnerability_report
    VULN_SCANNER_AVAILABLE = True
    logger.info("Vulnerability scanner loaded successfully")
except Exception as e:
    logger.warning(f"Vulnerability scanner not available: {e}")

class MinimalBot:
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
        
        # Initialize crypto alerts manager if available
        self.crypto_manager = None
        if CRYPTO_ALERTS_AVAILABLE:
            self.crypto_manager = CryptoAlertManager(self._send_crypto_alert)
            logger.info("Crypto alerts manager initialized")
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command handlers"""
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Stock analysis command (if available)
        if STOCK_AVAILABLE:
            self.application.add_handler(CommandHandler("stock", self.stock_command))
        
        # Crypto alerts (if available)
        if CRYPTO_ALERTS_AVAILABLE:
            self.application.add_handler(CommandHandler("newalert", self.new_alert_command))
            self.application.add_handler(CommandHandler("viewalerts", self.view_alerts_command))
            self.application.add_handler(CommandHandler("cancelalert", self.cancel_alert_command))
            self.application.add_handler(CommandHandler("getprice", self.get_price_command))
            self.application.add_handler(CommandHandler("priceall", self.price_all_command))
            self.application.add_handler(CommandHandler("getindicator", self.get_indicator_command))
            self.application.add_handler(CommandHandler("indicators", self.indicators_command))
            
        # Network tools (if available)  
        if NETWORK_AVAILABLE:
            self.application.add_handler(CommandHandler("ping", self.ping_command))
            self.application.add_handler(CommandHandler("scan", self.scan_command))
            self.application.add_handler(CommandHandler("rangescan", self.range_scan_command))
            self.application.add_handler(CommandHandler("vulnscan", self.vuln_scan_command))
            self.application.add_handler(CommandHandler("vulninfo", self.vulninfo_command))
            self.application.add_handler(CommandHandler("exploitinfo", self.exploitinfo_command))
            self.application.add_handler(CommandHandler("exploitscan", self.exploitscan_command))
            
        # IP location tools (if available)
        if IP_LOCATION_AVAILABLE:
            self.application.add_handler(CommandHandler("locate", self.locate_command))
            self.application.add_handler(CommandHandler("ip", self.ip_command))
        
        # Menu and callback handlers
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            await update.message.reply_text(
                "🤖 Bot is running!\n"
                "/help - Show available commands\n"
                "/status - Check bot status"
            )
        except Exception as e:
            logger.error(f"Start command error: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            user_name = update.effective_user.first_name
            user_id = update.effective_user.id
            username = update.effective_user.username or "ללא שם משתמש"
            
            logger.info(f"❓ /help - משתמש: {user_name} (@{username}) | ID: {user_id}")
            
            help_text = """
📋 **פקודות זמינות:**

🔹 **בסיסיות:**
/start - התחלת השיחה עם הבוט
/help - הצגת עזרה זו
/menu - תפריט אינטראקטיבי יפה
/status - מצב הבוט

🔹 **כלי רשת:**"""
            
            if IP_LOCATION_AVAILABLE:
                help_text += """
/locate <IP או דומיין> - איתור מיקום IP מפורט
/ip <IP> - מידע מהיר על IP"""
                
            if NETWORK_AVAILABLE:
                help_text += """
/scan <IP או דומיין> [סוג] - בדיקת פורטים פתוחים
/rangescan <טווח IP> <פורט> - סריקת טווח IP לפורט ספציפי
/ping <IP או דומיין> - בדיקת זמינות שרת"""
                
            if VULN_SCANNER_AVAILABLE:
                help_text += """
/vulnscan <IP או דומיין> - בדיקת פגיעויות אבטחה
/exploitscan <יעד> - ניתוח exploits מתקדם עם תוכנית ניצול
/vulninfo <סוג פגיעות> - מידע מפורט על פגיעויות
/exploitinfo <שירות> - מידע על exploits ידועים"""
                
            if STOCK_AVAILABLE:
                help_text += """

🔹 **כלי מניות:**
/stock <סימול> - ניתוח מניה מפורט"""
            
            if CRYPTO_ALERTS_AVAILABLE:
                help_text += """

🔹 **התראות קריפטו:**
/newalert - יצירת התראה חדשה
/viewalerts - צפייה בהתראות
/cancelalert - ביטול התראה
/getprice <זוג> - קבלת מחיר נוכחי
/priceall - מחירים לכל ההתראות
/getindicator - קבלת אינדיקטור טכני
/indicators - רשימת אינדיקטורים"""
                
            help_text += """

🔹 **דוגמאות:**
/locate 8.8.8.8
/ip 1.1.1.1
/scan google.com quick
/rangescan 192.168.1.0/24 22
/ping github.com"""
                
            if VULN_SCANNER_AVAILABLE:
                help_text += """
/vulnscan google.com
/exploitscan example.com
/vulninfo ssl
/exploitinfo apache
"""
            else:
                help_text += """
"""
            
            if STOCK_AVAILABLE:
                help_text += "/stock AAPL\n"
            
            if CRYPTO_ALERTS_AVAILABLE:
                help_text += "/newalert BTC/USDT PRICE ABOVE 50000\n"
                
            help_text += """
💡 **טיפ:** השתמש ב-/menu לתפריט אינטראקטיבי נוח!

פשוט שלח לי הודעה ואני אענה לך! 💬"""
            
            await update.message.reply_text(help_text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Help command error: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            status_text = "✅ Bot Status: ONLINE\n🌐 Environment: Cloud\n🐍 Python: OK\n📡 Telegram API: Connected\n\n🔧 **פיצ'רים זמינים:**\n"
            
            if STOCK_AVAILABLE:
                status_text += "📈 ניתוח מניות: ✅\n"
            else:
                status_text += "📈 ניתוח מניות: ❌\n"
                
            if NETWORK_AVAILABLE:
                status_text += "🌐 כלי רשת: ✅\n"
            else:
                status_text += "🌐 כלי רשת: ❌\n"
                
            if IP_LOCATION_AVAILABLE:
                status_text += "📍 זיהוי מיקום IP: ✅\n"
            else:
                status_text += "📍 זיהוי מיקום IP: ❌\n"
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Status command error: {e}")

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command with beautiful inline keyboard"""
        try:
            user_name = update.effective_user.first_name
            user_id = update.effective_user.id
            username = update.effective_user.username or "ללא שם משתמש"
            
            logger.info(f"📋 /menu - משתמש: {user_name} (@{username}) | ID: {user_id}")
            
            keyboard = []
            
            # Add available features to menu
            if NETWORK_AVAILABLE or IP_LOCATION_AVAILABLE:
                keyboard.append([InlineKeyboardButton("🔍 כלי רשת", callback_data='network_tools')])
                
            if STOCK_AVAILABLE:
                keyboard.append([InlineKeyboardButton("� ניתוח מניות", callback_data='stock_tools')])
                
            keyboard.extend([
                [InlineKeyboardButton("📊 דוגמאות מהירות", callback_data='quick_examples')],
                [InlineKeyboardButton("❓ עזרה ומידע", callback_data='help_info')],
                [InlineKeyboardButton("📞 יצירת קשר", callback_data='contact')]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🤖 **שלום {user_name}!**\n\n"
                "בחר אפשרות מהתפריט:\n"
                "💡 לחץ על הכפתורים למטה לגישה מהירה",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Menu command error: {e}")
    
    async def stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stock command"""
        if not STOCK_AVAILABLE:
            await update.message.reply_text("❌ Stock analysis not available in this deployment")
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "📈 **Stock Analysis**\n\n"
                    "Usage: `/stock <SYMBOL>`\n\n"
                    "Examples:\n"
                    "• `/stock AAPL` - Apple Inc.\n"
                    "• `/stock MSFT` - Microsoft\n"
                    "• `/stock GOOGL` - Google"
                )
                return
            
            symbol = context.args[0].upper()
            
            # Send "analyzing" message
            status_msg = await update.message.reply_text(f"📊 Analyzing {symbol}...")
            
            # Get stock analysis
            result = await stock_analyzer.analyze_stock(symbol, prediction_days=3)
            
            # Format and send result
            if 'error' in result:
                await status_msg.edit_text(f"❌ Error: {result['error']}")
            else:
                response = format_stock_analysis(result)
                await status_msg.edit_text(response, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Stock command error: {e}")
            await update.message.reply_text(f"❌ Error analyzing {symbol}: {str(e)}")

    async def new_alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create new crypto price/indicator alert"""
        if not CRYPTO_ALERTS_AVAILABLE or not self.crypto_manager:
            await update.message.reply_text("❌ Crypto alerts not available")
            return
        
        user_id = str(update.effective_user.id)
        
        if not context.args:
            help_text = """
📊 **יצירת התראת קריפטו**

🔹 **התראת מחיר פשוטה:**
`/newalert <PAIR> PRICE <COMP> <TARGET> [COOLDOWN]`

**דוגמאות:**
• `/newalert BTC/USDT PRICE ABOVE 50000`
• `/newalert ETH/USDT PRICE BELOW 2000 1h`
• `/newalert BTC/USDT PRICE PCTCHG 5 30000`
• `/newalert BTC/USDT PRICE 24HRCHG 10 1h`

**השוואות:** ABOVE, BELOW, PCTCHG, 24HRCHG
**Cooldown:** 30s, 5m, 1h, 2h, 1d

🔹 **התראה טכנית:**
`/newalert <PAIR> <IND> <TIME> <PARAMS> <OUTPUT> <COMP> <TARGET> [COOLDOWN]`

**דוגמאות:**
• `/newalert ETH/USDT RSI 1h default value BELOW 30`
• `/newalert BTC/USDT MACD 4h default valueMACD ABOVE 0 1h`
• `/newalert ETH/USDT BBANDS 1d default valueUpperBand ABOVE 3000`

📚 **לרשימת אינדיקטורים:** `/indicators`
            """
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return
        
        try:
            args = context.args
            pair = args[0].upper()
            indicator_type = args[1].upper()
            
            # Simple price alert
            if indicator_type == "PRICE":
                if len(args) < 4:
                    await update.message.reply_text("❌ פורמט שגוי. דוגמה: /newalert BTC/USDT PRICE ABOVE 50000")
                    return
                
                comparison = args[2].upper()
                target = float(args[3])
                entry_price = args[4] if len(args) > 4 and comparison in ["PCTCHG"] else None
                cooldown_str = args[5] if len(args) > 5 else (args[4] if comparison not in ["PCTCHG"] and len(args) > 4 else None)
                
                if comparison not in SIMPLE_COMPARISONS:
                    await update.message.reply_text(f"❌ השוואה לא תקינה. אפשרויות: {', '.join(SIMPLE_COMPARISONS)}")
                    return
                
                # Get entry price for PCTCHG
                if comparison == "PCTCHG":
                    from crypto_alerts import BinanceAPI
                    entry_price = float(entry_price) if entry_price else BinanceAPI.get_price(pair)
                    target = target / 100  # Convert percentage to decimal
                
                cooldown = parse_cooldown(cooldown_str)
                
                alert = SimpleAlert(
                    pair=pair,
                    indicator="PRICE",
                    comparison=comparison,
                    target=target,
                    entry_price=entry_price,
                    cooldown=cooldown
                )
                
                result = self.crypto_manager.add_alert(user_id, alert)
                await update.message.reply_text(result)
            
            # Technical indicator alert
            elif indicator_type in ['RSI', 'MACD', 'BBANDS', 'SMA', 'EMA']:
                if len(args) < 7:
                    await update.message.reply_text(
                        "❌ פורמט שגוי. דוגמה:\n"
                        "/newalert BTC/USDT RSI 1h default value BELOW 30"
                    )
                    return
                
                timeframe = args[2].lower()
                params_str = args[3]
                output_value = args[4]
                comparison = args[5].upper()
                target = float(args[6])
                cooldown_str = args[7] if len(args) > 7 else None
                
                if timeframe not in BINANCE_TIMEFRAMES:
                    await update.message.reply_text(f"❌ טווח זמן לא תקין. אפשרויות: {', '.join(BINANCE_TIMEFRAMES)}")
                    return
                
                # Parse params
                params = {}
                if params_str.lower() != "default":
                    for param in params_str.split(','):
                        key, value = param.split('=')
                        params[key] = value
                
                cooldown = parse_cooldown(cooldown_str)
                
                alert = TechnicalAlert(
                    pair=pair,
                    indicator=indicator_type,
                    timeframe=timeframe,
                    params=params,
                    output_value=output_value,
                    comparison=comparison,
                    target=target,
                    cooldown=cooldown
                )
                
                result = self.crypto_manager.add_alert(user_id, alert)
                await update.message.reply_text(result)
            
            else:
                await update.message.reply_text("❌ אינדיקטור לא ידוע. השתמש ב-/indicators לרשימה מלאה")
        
        except Exception as e:
            logger.error(f"Error in new_alert_command: {e}")
            await update.message.reply_text(f"❌ שגיאה: {str(e)}")
    
    async def view_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View all active alerts"""
        if not CRYPTO_ALERTS_AVAILABLE or not self.crypto_manager:
            await update.message.reply_text("❌ Crypto alerts not available")
            return
        
        user_id = str(update.effective_user.id)
        pair = context.args[0].upper() if context.args else None
        
        formatted = self.crypto_manager.format_alerts(user_id, pair)
        await update.message.reply_text(formatted, parse_mode='Markdown')
    
    async def cancel_alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel/delete an alert"""
        if not CRYPTO_ALERTS_AVAILABLE or not self.crypto_manager:
            await update.message.reply_text("❌ Crypto alerts not available")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ שימוש: `/cancelalert <PAIR> <INDEX>`\n\n"
                "דוגמה: `/cancelalert BTC/USDT 0`\n\n"
                "💡 השתמש ב-/viewalerts לראות את האינדקסים",
                parse_mode='Markdown'
            )
            return
        
        user_id = str(update.effective_user.id)
        pair = context.args[0].upper()
        index = int(context.args[1])
        
        result = self.crypto_manager.remove_alert(user_id, pair, index)
        await update.message.reply_text(result)
    
    async def get_price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get current crypto price"""
        if not CRYPTO_ALERTS_AVAILABLE:
            await update.message.reply_text("❌ Crypto alerts not available")
            return
        
        if not context.args:
            await update.message.reply_text(
                "💰 **קבלת מחיר קריפטו**\n\n"
                "שימוש: `/getprice <PAIR>`\n\n"
                "דוגמאות:\n"
                "• `/getprice BTC/USDT`\n"
                "• `/getprice ETH/USDT`\n"
                "• `/getprice BNB/USDT`",
                parse_mode='Markdown'
            )
            return
        
        pair = context.args[0].upper()
        
        try:
            from crypto_alerts import BinanceAPI
            price = BinanceAPI.get_price(pair)
            change_24h = BinanceAPI.get_price_change(pair, "1d")
            
            direction = "📈" if change_24h > 0 else "📉"
            
            message = f"💰 **{pair}**\n\n"
            message += f"**מחיר נוכחי:** ${price:,.2f}\n"
            message += f"**שינוי 24 שעות:** {direction} {abs(change_24h):.2f}%"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        
        except Exception as e:
            await update.message.reply_text(f"❌ שגיאה: {str(e)}")
    
    async def price_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get prices for all pairs with active alerts"""
        if not CRYPTO_ALERTS_AVAILABLE or not self.crypto_manager:
            await update.message.reply_text("❌ Crypto alerts not available")
            return
        
        user_id = str(update.effective_user.id)
        alerts = self.crypto_manager.get_alerts(user_id)
        
        if not alerts:
            await update.message.reply_text("📭 אין לך התראות פעילות")
            return
        
        # Get unique pairs
        pairs = list(set([alert.pair for alert in alerts]))
        
        message = "💰 **מחירים נוכחיים:**\n\n"
        
        from crypto_alerts import BinanceAPI
        for pair in pairs:
            try:
                price = BinanceAPI.get_price(pair)
                change = BinanceAPI.get_price_change(pair, "1d")
                direction = "📈" if change > 0 else "📉"
                message += f"**{pair}:** ${price:,.2f} {direction} {abs(change):.2f}%\n"
            except Exception as e:
                message += f"**{pair}:** ❌ Error\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def get_indicator_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get current technical indicator value"""
        if not CRYPTO_ALERTS_AVAILABLE or not self.crypto_manager:
            await update.message.reply_text("❌ Crypto alerts not available")
            return
        
        if not self.crypto_manager.taapi or not self.crypto_manager.taapi.enabled:
            await update.message.reply_text(
                "❌ אינדיקטורים טכניים לא זמינים\n"
                "נדרש TAAPIIO_APIKEY"
            )
            return
        
        if len(context.args) < 4:
            await update.message.reply_text(
                "📊 **קבלת אינדיקטור טכני**\n\n"
                "שימוש: `/getindicator <PAIR> <IND> <TIME> <PARAMS>`\n\n"
                "דוגמאות:\n"
                "• `/getindicator BTC/USDT RSI 1h default`\n"
                "• `/getindicator ETH/USDT MACD 4h default`\n"
                "• `/getindicator BTC/USDT BBANDS 1d period=20,stddev=2`",
                parse_mode='Markdown'
            )
            return
        
        pair = context.args[0].upper()
        indicator = context.args[1].upper()
        timeframe = context.args[2].lower()
        params_str = context.args[3]
        
        try:
            # Parse params
            params = {}
            if params_str.lower() != "default":
                for param in params_str.split(','):
                    key, value = param.split('=')
                    params[key] = value
            
            result = self.crypto_manager.taapi.get_indicator(pair, indicator, timeframe, params)
            
            message = f"📊 **{indicator} - {pair}**\n\n"
            message += f"**Timeframe:** {timeframe}\n"
            message += f"**Value:** {result}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        
        except Exception as e:
            await update.message.reply_text(f"❌ שגיאה: {str(e)}")
    
    async def indicators_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show list of available technical indicators"""
        if not CRYPTO_ALERTS_AVAILABLE:
            await update.message.reply_text("❌ Crypto alerts not available")
            return
        
        indicators_list = get_indicators_list()
        await update.message.reply_text(indicators_list, parse_mode='Markdown')
    
    def _send_crypto_alert(self, user_id: str, message: str):
        """Callback to send crypto alerts via Telegram"""
        async def send():
            try:
                await self.application.bot.send_message(
                    chat_id=int(user_id),
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send crypto alert to {user_id}: {e}")
        
        # Run async function in event loop
        asyncio.create_task(send())

    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ping command"""
        if not NETWORK_AVAILABLE:
            await update.message.reply_text("❌ Network tools not available in this deployment")
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "🌐 **Ping Tool**\n\n"
                    "Usage: `/ping <HOST>`\n\n"
                    "Examples:\n"
                    "• `/ping google.com`\n"
                    "• `/ping 8.8.8.8`"
                )
                return
                
            host = context.args[0]
            status_msg = await update.message.reply_text(f"🔍 Pinging {host}...")
            
            # Perform ping
            network_tools = NetworkTools()
            result = await network_tools.ping_host(host, count=4)
            
            if result['success']:
                response = f"🌐 **Ping Results - {host}**\n\n"
                response += f"📊 **Statistics:**\n"
                response += f"• Sent: {result['packets_sent']}\n"
                response += f"• Received: {result['packets_received']}\n"
                response += f"• Loss: {result['packet_loss']:.1f}%\n"
                response += f"• Avg Time: {result['avg_time']:.1f}ms"
            else:
                response = f"❌ Ping failed: {result['error']}"
                
            await status_msg.edit_text(response)
            
        except Exception as e:
            logger.error(f"Ping command error: {e}")
            await update.message.reply_text(f"❌ Error pinging {host}: {str(e)}")

    async def scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scan command - Advanced port scanning with multiple types"""
        if not NETWORK_AVAILABLE:
            await update.message.reply_text("❌ Network tools not available in this deployment")
            return
            
        try:
            user_name = update.effective_user.first_name
            user_id = update.effective_user.id
            username = update.effective_user.username or "ללא שם משתמש"
            
            if not context.args:
                logger.info(f"🔍 /scan (ללא פרמטר) - משתמש: {user_name} (@{username}) | ID: {user_id}")
                await update.message.reply_text(
                    "🔍 **סריקת פורטים מתקדמת**\n\n"
                    "**שימוש:** `/scan <IP או דומיין> [סוג]`\n\n"
                    "🔹 **דוגמאות:**\n"
                    "• `/scan google.com`\n"
                    "• `/scan 192.168.1.1 quick`\n"
                    "• `/scan github.com top100`\n"
                    "• `/scan mysite.com web`\n\n"
                    "🔹 **סוגי סריקה:**\n"
                    "• `quick` - 13 פורטים חשובים (מהיר)\n"
                    "• `common` - 19 פורטים נפוצים (ברירת מחדל)\n"
                    "• `top100` - 100 הפורטים הנפוצים ביותר\n"
                    "• `web` - פורטי שירותי אינטרנט\n"
                    "• `full` - כל הפורטים 1-65535 (איטי מאוד!)\n\n"
                    "⚠️ **לשימוש חוקי בלבד!**",
                    parse_mode='Markdown'
                )
                return
                
            target = context.args[0]
            scan_type = context.args[1] if len(context.args) > 1 else "common"
            
            logger.info(f"🔍 /scan '{target}' ({scan_type}) - משתמש: {user_name} (@{username}) | ID: {user_id}")
            
            # Import network tools with advanced functions
            from network_tools import NetworkTools, format_port_scan_result
            network_tools = NetworkTools()
            
            # Get ports for scan type
            ports = network_tools.get_port_ranges(scan_type)
            ports_count = len(ports)
            
            # Time estimates
            time_estimates = {
                "quick": "3-5 שניות",
                "common": "5-8 שניות", 
                "top100": "15-30 שניות",
                "web": "3-5 שניות",
                "full": "5-15 דקות ⚠️"
            }
            estimated_time = time_estimates.get(scan_type, "מספר שניות")
            
            # Show enhanced processing message
            processing_msg = await update.message.reply_text(
                f"🔍 **סורק פורטים עבור:** `{target}`\n\n"
                f"📊 **סוג סריקה:** {scan_type.upper()}\n"
                f"🎯 **פורטים לסריקה:** {ports_count:,}\n"
                f"⏱️ **זמן משוער:** {estimated_time}\n\n"
                f"⏳ מתחיל סריקה... אנא המתן",
                parse_mode='Markdown'
            )
            
            # Perform advanced scan
            result = await network_tools.scan_ports_async(target, ports)
            
            # Format results with advanced formatting
            result_text = format_port_scan_result(result)
            
            # Create enhanced inline keyboard
            keyboard = [
                [InlineKeyboardButton("🔄 סרוק מחדש", callback_data='scan_demo')],
                [InlineKeyboardButton("🏓 Ping Test", callback_data='ping_demo')],
                [InlineKeyboardButton("📍 איתור IP", callback_data='locate_demo')],
                [InlineKeyboardButton("🔙 תפריט ראשי", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Advanced scan command error: {e}")
            # Fallback to basic scan if advanced fails
            try:
                target = context.args[0] if context.args else "unknown"
                await update.message.reply_text(
                    f"⚠️ הסריקה המתקדמת נכשלה עבור {target}\n\n"
                    f"🔄 נסה שוב מאוחר יותר או עם target אחר.\n\n"
                    f"📝 וודא שהפורמט נכון:\n"
                    f"`/scan {target} [quick/common/top100/web]`",
                    parse_mode='Markdown'
                )
            except:
                await update.message.reply_text(f"❌ שגיאה בסריקת פורטים: {str(e)}")

    async def range_scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rangescan command for IP range scanning"""
        if not NETWORK_AVAILABLE:
            await update.message.reply_text("❌ Network tools not available in this deployment")
            return
            
        try:
            user_name = update.effective_user.first_name
            user_id = update.effective_user.id
            username = update.effective_user.username or "ללא שם משתמש"
            
            # Check if range and port were provided
            if len(context.args) < 2:
                logger.info(f"🎯 /rangescan (פרמטרים חסרים) - משתמש: {user_name} (@{username}) | ID: {user_id}")
                await update.message.reply_text(
                    "🎯 **סריקת טווח IP מתקדמת**\n\n"
                    "**שימוש:** `/rangescan <טווח IP> <פורט>`\n\n"
                    "🔹 **פורמטים נתמכים:**\n"
                    "• **CIDR:** `/rangescan 192.168.1.0/24 22`\n"
                    "• **טווח:** `/rangescan 213.0.0.0-213.0.0.255 5900`\n"
                    "• **IP יחיד:** `/rangescan 8.8.8.8 80`\n\n"
                    "🚀 **דוגמאות נפוצות:**\n"
                    "• SSH: `/rangescan 192.168.1.0/24 22`\n"
                    "• VNC: `/rangescan 10.0.0.0/16 5900`\n"
                    "• Web: `/rangescan 172.16.0.0/24 80`\n\n"
                    "⚠️ **הערה:** טווחים גדולים יכולים לקחת זמן רב!\n"
                    "💡 **טיפ:** התחל עם טווח קטן כמו /24\n"
                    "🛡️ **לשימוש חוקי בלבד!**",
                    parse_mode='Markdown'
                )
                return
                
            ip_range = context.args[0]
            try:
                port = int(context.args[1])
            except ValueError:
                await update.message.reply_text(
                    "❌ **פורט לא תקין**\n\n"
                    "הפורט חייב להיות מספר בין 1-65535\n\n"
                    "דוגמה: `/rangescan 192.168.1.0/24 22`",
                    parse_mode='Markdown'
                )
                return
                
            if not (1 <= port <= 65535):
                await update.message.reply_text(
                    "❌ **פורט מחוץ לטווח**\n\n"
                    "הפורט חייב להיות בין 1-65535\n\n"
                    f"הפורט שלך: `{port}`",
                    parse_mode='Markdown'
                )
                return
                
            logger.info(f"🎯 /rangescan '{ip_range}' פורט {port} - משתמש: {user_name} (@{username}) | ID: {user_id}")
            
            # Import advanced range scanning
            from network_tools import RangeScanner, format_range_scan_result
            range_scanner = RangeScanner()
            
            # Parse range to estimate size
            try:
                test_ips = range_scanner.parse_ip_range(ip_range)
                estimated_count = len(test_ips)
                
                # Estimate time
                if estimated_count <= 256:
                    time_est = "10-30 שניות"
                elif estimated_count <= 1000:
                    time_est = "30-60 שניות"
                elif estimated_count <= 10000:
                    time_est = "2-5 דקות"
                elif estimated_count <= 100000:
                    time_est = "10-20 דקות"
                else:
                    time_est = "20+ דקות"
                    
                # Warning for large scans
                if estimated_count > 10000:
                    await update.message.reply_text(
                        f"⚠️ **אזהרה: סריקה גדולה מאוד**\n\n"
                        f"📊 **טווח:** `{ip_range}`\n"
                        f"🎯 **פורט:** `{port}`\n"
                        f"📈 **מוערך:** ~`{estimated_count:,}` IPs\n"
                        f"⏱️ **זמן משוער:** {time_est}\n\n"
                        f"🚨 **זה יכול להעמיס על הרשת!**\n"
                        f"🛡️ **השתמש רק ברשתות מורשות**\n\n"
                        f"נסה טווח קטן יותר כמו /24 או פחות.",
                        parse_mode='Markdown'
                    )
                    return
                    
            except Exception as e:
                await update.message.reply_text(
                    f"❌ **טווח IP לא תקין**\n\n"
                    f"שגיאה: `{str(e)}`\n\n"
                    f"🔹 **פורמטים נכונים:**\n"
                    f"• `192.168.1.0/24`\n"
                    f"• `10.0.0.1-10.0.0.254`\n"
                    f"• `8.8.8.8`",
                    parse_mode='Markdown'
                )
                return
                
            # Show processing message
            processing_msg = await update.message.reply_text(
                f"🎯 **מתחיל סריקת טווח מתקדמת**\n\n"
                f"📍 **טווח:** `{ip_range}`\n"
                f"🔍 **פורט:** `{port}`\n"
                f"📊 **מוערך:** ~`{estimated_count:,}` IPs\n"
                f"⏱️ **זמן משוער:** {time_est}\n\n"
                f"⚡ **מתחיל threads...**\n"
                f"⏳ **התחלת סריקה...**",
                parse_mode='Markdown'
            )
            
            # Progress callback function
            async def progress_callback(scanned, total, found):
                progress_percent = (scanned / total) * 100
                bar_length = 15
                filled = int(bar_length * scanned / total)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                try:
                    await processing_msg.edit_text(
                        f"🎯 **סורק טווח IP - {progress_percent:.1f}%**\n\n"
                        f"📍 **טווח:** `{ip_range}`\n"
                        f"🔍 **פורט:** `{port}`\n\n"
                        f"📊 **התקדמות:** `{scanned:,}/{total:,}`\n"
                        f"🟢 **נמצאו:** `{found}` פורטים פתוחים\n\n"
                        f"**[{bar}] {progress_percent:.1f}%**\n\n"
                        f"⚡ ממשיך בסריקה...",
                        parse_mode='Markdown'
                    )
                except:
                    pass  # Ignore edit errors during progress updates
                    
            # Perform the range scan
            result = await range_scanner.scan_range_async(
                ip_range, port, progress_callback
            )
            
            # Format results with advanced formatting
            result_text = format_range_scan_result(result)
            
            # Create enhanced inline keyboard
            keyboard = [
                [InlineKeyboardButton("🔄 סרוק טווח אחר", callback_data='scan_demo')],
                [InlineKeyboardButton("🔍 סריקת פורטים רגילה", callback_data='scan_demo')],
                [InlineKeyboardButton("📍 איתור IP", callback_data='locate_demo')],
                [InlineKeyboardButton("🔙 תפריט ראשי", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Range scan command error: {e}")
            try:
                await update.message.reply_text(
                    f"❌ **שגיאה בסריקת טווח**\n\n"
                    f"השגיאה: `{str(e)}`\n\n"
                    f"🔄 נסה שוב עם פורמט נכון:\n"
                    f"`/rangescan 192.168.1.0/24 22`",
                    parse_mode='Markdown'
                )
            except:
                await update.message.reply_text(f"❌ שגיאה בסריקת טווח: {str(e)}")

    async def exploitscan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /exploitscan command for comprehensive exploit analysis"""
        if not VULN_SCANNER_AVAILABLE:
            await update.message.reply_text("❌ מודול ניתוח exploits לא זמין בפריסה זו")
            return
            
        try:
            user_name = update.effective_user.first_name
            user_id = update.effective_user.id
            username = update.effective_user.username or "ללא שם משתמש"
            
            logger.info(f"💥 /exploitscan - משתמש: {user_name} (@{username}) | ID: {user_id}")
            
            if not context.args:
                await update.message.reply_text(
                    "💥 **ניתוח Exploits מתקדם**\n\n"
                    "**שימוש:** `/exploitscan <יעד>`\n\n"
                    "🎯 **מה הבוט יעשה:**\n"
                    "• זיהוי שירותים וגרסאות מדויק\n"
                    "• חיפוש exploits ספציפיים ב-Exploit-DB\n"
                    "• תוכנית ניצול מפורטת\n"
                    "• הערכת רמת סיכון\n\n"
                    "📖 **דוגמאות:**\n"
                    "`/exploitscan google.com`\n"
                    "`/exploitscan 192.168.1.1`\n\n"
                    "⚠️ **אזהרה:** למטרות חינוך והגנה בלבד!",
                    parse_mode='Markdown'
                )
                return
                
            target = context.args[0]
            
            # Send "analyzing" message
            status_msg = await update.message.reply_text(
                f"💥 **מנתח exploits עבור:** `{target}`\n\n"
                "🔍 זיהוי שירותים...\n"
                "🎯 חיפוש exploits...\n"
                "📋 יצירת תוכנית ניצול...\n\n"
                "⏳ זה יכול לקחת דקה...",
                parse_mode='Markdown'
            )
            
            # Import and run exploit analysis
            from vulnerability_scanner import VulnerabilityScanner
            scanner = VulnerabilityScanner()
            
            # Perform comprehensive exploit analysis
            analysis_result = await scanner.analyze_website_exploits(target)
            
            # Format results
            if 'error' in analysis_result:
                await status_msg.edit_text(
                    f"❌ **שגיאה בניתוח:** {analysis_result['error']}\n\n"
                    "נסה יעד אחר או בדוק את החיבור לאינטרנט",
                    parse_mode='Markdown'
                )
                return
            
            response = await self._format_exploit_analysis(analysis_result)
            
            # Split long messages
            if len(response) > 4000:
                parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                await status_msg.edit_text(parts[0], parse_mode='Markdown')
                for part in parts[1:]:
                    await update.message.reply_text(part, parse_mode='Markdown')
            else:
                await status_msg.edit_text(response, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Exploitscan command error: {e}")
            await update.message.reply_text(f"❌ שגיאה בניתוח exploits: {str(e)}")

    async def _format_exploit_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format exploit analysis results for display"""
        target = analysis.get('target', 'Unknown')
        services = analysis.get('detected_services', [])
        exploits = analysis.get('potential_exploits', [])
        plan = analysis.get('exploitation_plan', [])
        severity_score = analysis.get('severity_score', 100)
        
        # Determine risk level
        if severity_score <= 20:
            risk_level = "🔴 **סיכון קריטי**"
            risk_emoji = "🚨"
        elif severity_score <= 40:
            risk_level = "🟠 **סיכון גבוה**"  
            risk_emoji = "⚠️"
        elif severity_score <= 70:
            risk_level = "🟡 **סיכון בינוני**"
            risk_emoji = "⚡"
        else:
            risk_level = "🟢 **סיכון נמוך**"
            risk_emoji = "✅"
        
        response = f"💥 **דוח ניתוח Exploits - {target}**\n\n"
        response += f"{risk_emoji} {risk_level}\n"
        response += f"🎯 **ציון אבטחה:** {severity_score}/100\n\n"
        
        # Detected services
        if services:
            response += f"🔍 **שירותים שזוהו ({len(services)}):**\n"
            for service in services[:3]:  # Show top 3 services
                if 'server_parsed' in service and 'software' in service['server_parsed']:
                    server_info = service['server_parsed']
                    software = server_info.get('software', 'Unknown')
                    version = server_info.get('version', 'Unknown')
                    response += f"• {software} {version} (Port {service.get('port', 'N/A')})\n"
                elif 'technologies' in service:
                    for tech in service['technologies'][:2]:
                        tech_name = tech.get('name', 'Unknown')
                        tech_version = tech.get('version', '')
                        response += f"• {tech_name} {tech_version}\n"
                else:
                    service_name = service.get('service', 'Unknown')
                    port = service.get('port', 'N/A')
                    response += f"• {service_name} (Port {port})\n"
            response += "\n"
        
        # Found exploits
        if exploits:
            response += f"💀 **EXPLOITS זמינים ({len(exploits)}):**\n\n"
            
            # Show critical exploits first
            critical_exploits = [e for e in exploits if e.get('severity') == 'Critical']
            high_exploits = [e for e in exploits if e.get('severity') == 'High']
            
            for exploit in critical_exploits[:2]:
                response += f"🔴 **CRITICAL: {exploit.get('title', 'Unknown')}**\n"
                if 'cve' in exploit:
                    response += f"🏷️ CVE: `{exploit['cve']}`\n"
                response += f"📝 {exploit.get('description', '')}\n"
                if 'exploitation' in exploit:
                    exp = exploit['exploitation']
                    response += f"⚔️ כלים: {', '.join(exp.get('tools', [])[:3])}\n"
                    response += f"💥 השפעה: {exp.get('impact', 'Unknown')}\n"
                response += "\n"
                
            for exploit in high_exploits[:1]:
                response += f"🟠 **HIGH: {exploit.get('title', 'Unknown')}**\n"
                if 'cve' in exploit:
                    response += f"🏷️ CVE: `{exploit['cve']}`\n"
                response += f"📝 {exploit.get('description', '')}\n\n"
                
            if len(exploits) > 3:
                response += f"⚠️ ועוד {len(exploits)-3} exploits נוספים!\n\n"
        
        # Exploitation plan
        if plan:
            response += f"📋 **תוכנית ניצול מומלצת:**\n\n"
            for step in plan[:2]:  # Show top 2 steps
                response += f"**שלב {step['step']}: {step['target']}**\n"
                response += f"🎯 שיטה: {step['method']}\n"
                response += f"🛠️ כלים: {', '.join(step['tools_needed'][:3])}\n"
                response += f"📊 רמת קושי: {step['difficulty']}\n"
                if step['steps']:
                    response += f"🔹 צעד ראשון: {step['steps'][0]}\n"
                response += "\n"
        
        response += "🛡️ **הערה:** מידע זה למטרות הגנה והדרכה בלבד!\n"
        response += "⚖️ השימוש באופן בלתי חוקי אסור ועלול להוביל לתביעה משפטית."
        
        return response

    async def exploitinfo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /exploitinfo command for detailed exploit information"""
        if not VULN_SCANNER_AVAILABLE:
            await update.message.reply_text("❌ מודול מידע exploits לא זמין בפריסה זו")
            return
            
        try:
            user_name = update.effective_user.first_name
            user_id = update.effective_user.id
            username = update.effective_user.username or "ללא שם משתמש"
            
            logger.info(f"💥 /exploitinfo - משתמש: {user_name} (@{username}) | ID: {user_id}")
            
            if not context.args:
                await update.message.reply_text(
                    "💥 **מאגר מידע Exploits**\n\n"
                    "**שימוש:** `/exploitinfo <שירות>`\n\n"
                    "🎯 **שירותים נתמכים:**\n"
                    "• `apache` - Apache HTTP Server exploits\n"
                    "• `nginx` - Nginx exploits\n" 
                    "• `ssh` - OpenSSH exploits\n"
                    "• `ftp` - FTP service exploits\n"
                    "• `mysql` - MySQL exploits\n"
                    "• `iis` - Microsoft IIS exploits\n\n"
                    "📖 **דוגמה:**\n"
                    "`/exploitinfo apache`\n\n"
                    "⚠️ **אזהרה:** מידע למטרות הגנה בלבד!",
                    parse_mode='Markdown'
                )
                return
                
            service = context.args[0].lower()
            
            # Import vulnerability scanner for exploit info
            from vulnerability_scanner import VulnerabilityScanner
            
            # Create scanner instance
            scanner = VulnerabilityScanner()
            
            # Get exploits for the service
            exploits = await scanner.search_known_exploits(service)
            
            if not exploits:
                await update.message.reply_text(
                    f"❌ **לא נמצאו exploits עבור:** `{service}`\n\n"
                    "השתמש ב-`/exploitinfo` לרשימת השירותים הנתמכים",
                    parse_mode='Markdown'
                )
                return
            
            # Format exploit information
            response = f"💥 **Exploits עבור {service.upper()}**\n\n"
            
            for i, exploit in enumerate(exploits[:3], 1):  # Limit to 3 exploits
                severity_icon = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(exploit.get('severity', '').lower(), '⚪')
                
                response += f"{severity_icon} **{i}. {exploit.get('title', 'Unknown')}**\n"
                
                if 'cve' in exploit:
                    response += f"🏷️ **CVE:** `{exploit['cve']}`\n"
                    
                response += f"📝 **תיאור:** {exploit.get('description', '')}\n"
                
                if 'versions_affected' in exploit:
                    response += f"🎯 **גרסאות מושפעות:** {exploit['versions_affected']}\n"
                
                if 'exploitation' in exploit:
                    exp = exploit['exploitation']
                    response += f"⚔️ **שיטת ניצול:** {exp.get('method', 'Unknown')}\n"
                    
                    if 'tools' in exp:
                        tools_str = ', '.join(exp['tools'][:3])
                        response += f"🛠️ **כלים:** {tools_str}\n"
                    
                    if 'payload' in exp:
                        payload = exp['payload'][:80]
                        response += f"💣 **Payload:** `{payload}...`\n"
                    
                    if 'impact' in exp:
                        response += f"💥 **השפעה:** {exp['impact']}\n"
                
                response += "\n"
            
            if len(exploits) > 3:
                response += f"⚠️ ועוד {len(exploits)-3} exploits נוספים!\n\n"
            
            response += "🛡️ **הערה:** מידע זה מיועד למטרות הגנה ולמידה בלבד!"
            
            await update.message.reply_text(response, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Exploitinfo command error: {e}")
            await update.message.reply_text(f"❌ שגיאה בהצגת מידע exploits: {str(e)}")

    async def vulninfo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /vulninfo command for detailed vulnerability information"""
        if not VULN_SCANNER_AVAILABLE:
            await update.message.reply_text("❌ מודול מידע פגיעויות לא זמין בפריסה זו")
            return
            
        try:
            user_name = update.effective_user.first_name
            user_id = update.effective_user.id
            username = update.effective_user.username or "ללא שם משתמש"
            
            logger.info(f"📚 /vulninfo - משתמש: {user_name} (@{username}) | ID: {user_id}")
            
            if not context.args:
                await update.message.reply_text(
                    "📚 **מאגר מידע פגיעויות**\n\n"
                    "**שימוש:** `/vulninfo <סוג פגיעות>`\n\n"
                    "🔐 **סוגי פגיעויות זמינים:**\n"
                    "• `ssl` - פגיעויות SSL/TLS\n"
                    "• `cert` - תעודות פגות\n" 
                    "• `headers` - כותרות אבטחה חסרות\n"
                    "• `server` - חשיפת מידע שרת\n"
                    "• `ftp` - שירות FTP לא מאובטח\n"
                    "• `telnet` - שירות Telnet לא מאובטח\n\n"
                    "📖 **דוגמה:**\n"
                    "`/vulninfo ssl`\n\n"
                    "🎯 **מטרה:** הבנת שיטות התקפה למטרות הגנה",
                    parse_mode='Markdown'
                )
                return
                
            vuln_type = context.args[0].lower()
            
            # Import vulnerability scanner
            from vulnerability_scanner import VulnerabilityScanner, format_detailed_vulnerability_info
            
            # Create scanner instance to access database
            scanner = VulnerabilityScanner()
            
            # Map user input to vulnerability database keys
            vuln_mapping = {
                'ssl': 'ssl_version',
                'tls': 'ssl_version',
                'cert': 'certificate_expiry', 
                'certificate': 'certificate_expiry',
                'headers': 'security_headers',
                'header': 'security_headers',
                'server': 'server_info',
                'info': 'server_info',
                'ftp': 'insecure_ftp',
                'telnet': 'insecure_telnet'
            }
            
            if vuln_type not in vuln_mapping:
                await update.message.reply_text(
                    f"❌ **סוג פגיעות לא נמצא:** `{vuln_type}`\n\n"
                    "השתמש ב-`/vulninfo` לרשימת הסוגים הזמינים",
                    parse_mode='Markdown'
                )
                return
                
            # Get vulnerability info from database
            db_key = vuln_mapping[vuln_type]
            if db_key in scanner.vuln_database:
                vuln_info = scanner.vuln_database[db_key]
                detailed_info = format_detailed_vulnerability_info(vuln_info)
                
                # Split long messages if needed
                if len(detailed_info) > 4000:
                    # Send in parts
                    parts = [detailed_info[i:i+4000] for i in range(0, len(detailed_info), 4000)]
                    for i, part in enumerate(parts):
                        if i == 0:
                            await update.message.reply_text(part, parse_mode='Markdown')
                        else:
                            await update.message.reply_text(f"**המשך חלק {i+1}:**\n\n{part}", parse_mode='Markdown')
                else:
                    await update.message.reply_text(detailed_info, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    f"❌ מידע לא זמין עבור: `{vuln_type}`",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Vulninfo command error: {e}")
            await update.message.reply_text(f"❌ שגיאה בהצגת מידע: {str(e)}")

    async def vuln_scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /vulnscan command - Advanced vulnerability scanning"""
        if not VULN_SCANNER_AVAILABLE:
            # Fallback to basic scan if vulnerability scanner not available
            if context.args and NETWORK_AVAILABLE:
                target = context.args[0]
                await update.message.reply_text(
                    f"⚠️ **מודול סריקת פגיעויות לא זמין בפריסה זו**\n\n"
                    f"🔄 **חלופה זמינה:**\n"
                    f"📍 `/locate {target}` - מידע על IP ומיקום\n"
                    f"🔍 `/scan {target}` - סריקת פורטים בסיסית\n"
                    f"🏓 `/ping {target}` - בדיקת זמינות\n\n"
                    f"💡 **טיפ:** אלו כלים בסיסיים שעדיין יכולים לעזור!",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ מודול סריקת פגיעויות לא זמין בפריסה זו\n"
                    "נסה /scan או /locate במקום זאת"
                )
            return
            
        try:
            user_name = update.effective_user.first_name
            
            if not context.args:
                await update.message.reply_text(
                    "🔐 **סריקת פגיעויות מתקדמת**\n\n"
                    "שימוש: `/vulnscan <IP או דומיין>`\n\n"
                    "דוגמאות:\n"
                    "• `/vulnscan google.com`\n"
                    "• `/vulnscan github.com`\n\n"
                    "⚠️ לשימוש חוקי בלבד!",
                    parse_mode='Markdown'
                )
                return
                
            target = context.args[0]
            
            # Show processing message
            processing_msg = await update.message.reply_text(
                f"🔐 מתחיל סריקת פגיעויות עבור {target}...\n"
                f"⏳ זמן משוער: 15-30 שניות"
            )
            
            try:
                # Use pre-loaded vulnerability scanner
                scanner = VulnerabilityScanner()
                results = await scanner.scan_vulnerabilities(target)
                
                # Format and send results
                report = format_vulnerability_report(results)
                await processing_msg.edit_text(report, parse_mode='Markdown')
                
            except Exception as scan_error:
                logger.error(f"Vulnerability scan failed: {scan_error}")
                await processing_msg.edit_text(
                    f"❌ **שגיאה בסריקת פגיעויות**\n\n"
                    f"השגיאה: `{str(scan_error)}`\n\n"
                    f"🔄 **חלופות זמינות:**\n"
                    f"📍 `/locate {target}` - מידע על IP ומיקום\n" 
                    f"🔍 `/scan {target}` - סריקת פורטים\n"
                    f"🏓 `/ping {target}` - בדיקת זמינות",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Vulnerability scan error: {e}")
            await update.message.reply_text(f"❌ שגיאה: {str(e)}")

    async def locate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /locate command"""
        if not IP_LOCATION_AVAILABLE:
            await update.message.reply_text("❌ IP location tools not available in this deployment")
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "📍 **IP Location Finder**\n\n"
                    "Usage: `/locate <IP>`\n\n"
                    "Examples:\n"
                    "• `/locate 8.8.8.8`\n"
                    "• `/locate 1.1.1.1`\n"
                    "• `/locate 208.67.222.222`"
                )
                return
                
            ip = context.args[0]
            status_msg = await update.message.reply_text(f"📍 Finding location for {ip}...")
            
            # Get location data (using sync function)
            result = analyze_single_ip(ip)
            
            if result and 'error' not in result:
                response = f"📍 **IP Location - {ip}**\n\n"
                response += f"🌍 **Country:** {result.get('country', 'Unknown')}\n"
                response += f"🏙️ **City:** {result.get('city', 'Unknown')}\n"
                response += f"📍 **Region:** {result.get('region', 'Unknown')}\n"
                response += f"🏢 **ISP:** {result.get('isp', 'Unknown')}\n"
                response += f"🏛️ **Organization:** {result.get('org', 'Unknown')}\n"
                
                if 'lat' in result and 'lon' in result:
                    response += f"🗺️ **Coordinates:** {result['lat']}, {result['lon']}\n"
                    
                if 'timezone' in result:
                    response += f"🕒 **Timezone:** {result['timezone']}"
            else:
                error_msg = result.get('error', 'Location lookup failed') if result else 'Location lookup failed'
                response = f"❌ {error_msg}"
                
            await status_msg.edit_text(response)
            
        except Exception as e:
            logger.error(f"Locate command error: {e}")
            await update.message.reply_text(f"❌ Error locating {ip}: {str(e)}")

    async def ip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ip command - detailed IP information"""
        if not IP_LOCATION_AVAILABLE:
            await update.message.reply_text("❌ IP location tools not available in this deployment")
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "🔍 **IP Information Tool**\n\n"
                    "Usage: `/ip <IP>`\n\n"
                    "Examples:\n"
                    "• `/ip 8.8.8.8` - Google DNS\n"
                    "• `/ip 1.1.1.1` - Cloudflare DNS\n"
                    "• `/ip 208.67.222.222` - OpenDNS"
                )
                return
                
            ip = context.args[0]
            status_msg = await update.message.reply_text(f"🔍 Analyzing IP {ip}...")
            
            # Try multiple sources for comprehensive data (using sync functions)
            ipapi_result = geoip_ipapi(ip)
            ipinfo_result = geoip_ipinfo(ip)
            
            response = f"🔍 **IP Analysis - {ip}**\n\n"
            
            # Combine results from multiple sources
            if ipapi_result and 'error' not in ipapi_result:
                response += f"📊 **Geographic Data:**\n"
                response += f"• Country: {ipapi_result.get('country', 'Unknown')} ({ipapi_result.get('countryCode', 'XX')})\n"
                response += f"• Region: {ipapi_result.get('regionName', 'Unknown')}\n"
                response += f"• City: {ipapi_result.get('city', 'Unknown')}\n"
                response += f"• ZIP: {ipapi_result.get('zip', 'Unknown')}\n"
                response += f"• ISP: {ipapi_result.get('isp', 'Unknown')}\n"
                response += f"• Organization: {ipapi_result.get('org', 'Unknown')}\n"
                response += f"• AS: {ipapi_result.get('as', 'Unknown')}\n"
                
                if 'lat' in ipapi_result and 'lon' in ipapi_result:
                    response += f"• Coordinates: {ipapi_result['lat']}, {ipapi_result['lon']}\n"
                    
            elif ipinfo_result and 'error' not in ipinfo_result:
                response += f"📊 **Geographic Data (IPInfo):**\n"
                response += f"• Location: {ipinfo_result.get('city', 'Unknown')}, {ipinfo_result.get('region', 'Unknown')}, {ipinfo_result.get('country', 'Unknown')}\n"
                response += f"• Organization: {ipinfo_result.get('org', 'Unknown')}\n"
                
                if 'loc' in ipinfo_result:
                    response += f"• Coordinates: {ipinfo_result['loc']}\n"
            else:
                response += "❌ Could not retrieve detailed IP information"
                
            await status_msg.edit_text(response)
            
        except Exception as e:
            logger.error(f"IP command error: {e}")
            await update.message.reply_text(f"❌ Error analyzing {ip}: {str(e)}")

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Echo messages back"""
        try:
            text = update.message.text
            await update.message.reply_text(f"Echo: {text}")
        except Exception as e:
            logger.error(f"Echo error: {e}")
    
    def run(self):
        """Run the bot"""
        try:
            logger.info("Starting minimal bot...")
            self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Bot run error: {e}")
            raise

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_name = update.effective_user.first_name
            user_id = update.effective_user.id
            username = update.effective_user.username or "ללא שם משתמש"
            
            logger.info(f"🔘 כפתור נלחץ: '{query.data}' - משתמש: {user_name} (@{username}) | ID: {user_id}")

            # Main menu options
            if query.data == 'network_tools':
                keyboard = []
                if IP_LOCATION_AVAILABLE:
                    keyboard.extend([
                        [InlineKeyboardButton("📍 איתור IP/דומיין", callback_data='locate_demo')],
                        [InlineKeyboardButton("🗺️ מידע IP מהיר", callback_data='ip_demo')]
                    ])
                if NETWORK_AVAILABLE:
                    keyboard.extend([
                        [InlineKeyboardButton("🔍 סריקת פורטים", callback_data='scan_demo')],
                        [InlineKeyboardButton("� סריקת טווח IP", callback_data='rangescan_demo')],
                        [InlineKeyboardButton("�🏓 בדיקת Ping", callback_data='ping_demo')]
                    ])
                keyboard.append([InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "🔍 **כלי רשת**\n\n"
                    "בחר כלי לשימוש:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            elif query.data == 'stock_tools' and STOCK_AVAILABLE:
                keyboard = [
                    [InlineKeyboardButton("📈 ניתוח מניה", callback_data='stock_demo')],
                    [InlineKeyboardButton("💡 דוגמאות מניות", callback_data='stock_examples')],
                    [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📈 **ניתוח מניות**\n\n"
                    "בחר אפשרות:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            # Back to main menu
            elif query.data == 'main_menu':
                keyboard = []
                
                if NETWORK_AVAILABLE or IP_LOCATION_AVAILABLE:
                    keyboard.append([InlineKeyboardButton("🔍 כלי רשת", callback_data='network_tools')])
                    
                if STOCK_AVAILABLE:
                    keyboard.append([InlineKeyboardButton("📈 ניתוח מניות", callback_data='stock_tools')])
                    
                keyboard.extend([
                    [InlineKeyboardButton("📊 דוגמאות מהירות", callback_data='quick_examples')],
                    [InlineKeyboardButton("❓ עזרה ומידע", callback_data='help_info')],
                    [InlineKeyboardButton("📞 יצירת קשר", callback_data='contact')]
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"🤖 **שלום {user_name}!**\n\n"
                    "בחר אפשרות מהתפריט:\n"
                    "💡 לחץ על הכפתורים למטה לגישה מהירה",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            # Demo buttons - show example commands
            elif query.data == 'locate_demo':
                await query.edit_message_text(
                    "📍 **איתור IP/דומיין**\n\n"
                    "דוגמאות שימוש:\n"
                    "`/locate 8.8.8.8`\n"
                    "`/locate google.com`\n"
                    "`/locate 1.1.1.1`\n\n"
                    "פשוט העתק אחת מהפקודות למעלה! 📋",
                    parse_mode='Markdown'
                )
                
            elif query.data == 'ip_demo':
                await query.edit_message_text(
                    "🗺️ **מידע IP מהיר**\n\n"
                    "דוגמאות שימוש:\n"
                    "`/ip 8.8.8.8`\n"
                    "`/ip 1.1.1.1`\n"
                    "`/ip 208.67.222.222`\n\n"
                    "פשוט העתק אחת מהפקודות למעלה! 📋",
                    parse_mode='Markdown'
                )
                
            elif query.data == 'scan_demo':
                await query.edit_message_text(
                    "🔍 **סריקת פורטים**\n\n"
                    "דוגמאות שימוש:\n"
                    "`/scan google.com`\n"
                    "`/scan 192.168.1.1`\n\n"
                    "פשוט העתק אחת מהפקודות למעלה! 📋",
                    parse_mode='Markdown'
                )
                
            elif query.data == 'ping_demo':
                await query.edit_message_text(
                    "🏓 **בדיקת Ping**\n\n"
                    "דוגמאות שימוש:\n"
                    "`/ping google.com`\n"
                    "`/ping github.com`\n"
                    "`/ping 8.8.8.8`\n\n"
                    "פשוט העתק אחת מהפקודות למעלה! 📋",
                    parse_mode='Markdown'
                )
                
            elif query.data == 'rangescan_demo':
                await query.edit_message_text(
                    "🎯 **סריקת טווח IP מתקדמת**\n\n"
                    "דוגמאות שימוש:\n"
                    "`/rangescan 192.168.1.0/24 22`\n"
                    "`/rangescan 10.0.0.1-10.0.0.50 80`\n"
                    "`/rangescan 172.16.1.0/24 5900`\n\n"
                    "פשוט העתק אחת מהפקודות למעלה! 📋\n\n"
                    "💡 **טיפים:**\n"
                    "• SSH: פורט 22\n"
                    "• Web: פורט 80/443\n"
                    "• VNC: פורט 5900",
                    parse_mode='Markdown'
                )
                
            elif query.data == 'stock_demo' and STOCK_AVAILABLE:
                await query.edit_message_text(
                    "📈 **ניתוח מניה**\n\n"
                    "דוגמאות שימוש:\n"
                    "`/stock AAPL`\n"
                    "`/stock MSFT`\n"
                    "`/stock GOOGL`\n\n"
                    "פשוט העתק אחת מהפקודות למעלה! 📋",
                    parse_mode='Markdown'
                )
                
            elif query.data == 'contact':
                await query.edit_message_text(
                    "📞 **יצירת קשר**\n\n"
                    "🤖 הבוט הזה נוצר עבור בדיקות רשת ואבטחה\n"
                    "🛡️ השתמש באחריות ובהתאם לחוק\n"
                    "⚖️ אין להשתמש לפעילות לא חוקית\n\n"
                    "💬 פשוט שלח הודעה לבוט לשימוש רגיל!"
                )
                
            # Fallback for undefined buttons
            else:
                await query.edit_message_text(
                    f"🔧 הפיצ'ר '{query.data}' עדיין בפיתוח...\n\n"
                    "השתמש ב-/help לרשימת פקודות זמינות!"
                )
                
        except Exception as e:
            logger.error(f"Button callback error: {e}")

def main():
    """Main function"""
    try:
        # Get bot token
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")
        
        logger.info("Initializing bot...")
        bot = MinimalBot(bot_token)
        
        # Start crypto alerts monitoring if available
        if CRYPTO_ALERTS_AVAILABLE and bot.crypto_manager:
            logger.info("Starting crypto alerts monitoring...")
            bot.crypto_manager.start_monitoring()
        
        logger.info("Bot ready - starting polling...")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()