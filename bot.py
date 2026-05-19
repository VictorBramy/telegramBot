"""
Telegram Bot - Main Entry Point
Simple and extensible Telegram bot built with python-telegram-bot library
"""

import os
import logging
import socket
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from typing import Dict

# Import optional modules
IP_LOCATION_AVAILABLE = False
NETWORK_TOOLS_AVAILABLE = False

try:
    from locate_ip import analyze_single_ip, geoip_ipapi, geoip_ipinfo
    IP_LOCATION_AVAILABLE = True
except ImportError:
    print("IP location module not available")

try:
    from network_tools import (NetworkTools, format_port_scan_result, format_ping_result, 
                              IPRangeScanner, format_range_scan_result,
                              export_scan_results_csv, export_scan_results_json, export_scan_results_txt)
    NETWORK_TOOLS_AVAILABLE = True
except ImportError:
    print("Network tools module not available")

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('bot_activity.log', encoding='utf-8')  # File output
    ]
)

# Silence noisy HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Import stock analysis tools with better error handling
STOCK_ANALYSIS_AVAILABLE = False
try:
    from stock_analyzer import stock_analyzer, format_stock_analysis
    STOCK_ANALYSIS_AVAILABLE = True
    logger.info("Stock analysis module loaded successfully")
except ImportError as e:
    logger.warning(f"Stock analysis not available: {e}")
except Exception as e:
    logger.error(f"Failed to load stock analysis: {e}")

# Import crypto alerts module
CRYPTO_ALERTS_AVAILABLE = False
try:
    from crypto_alerts import (
        CryptoAlertManager, SimpleAlert, TechnicalAlert,
        parse_cooldown, get_indicators_list, SIMPLE_COMPARISONS, BINANCE_TIMEFRAMES
    )
    CRYPTO_ALERTS_AVAILABLE = True
    logger.info("Crypto alerts module loaded successfully")
except ImportError as e:
    logger.warning(f"Crypto alerts not available: {e}")
except Exception as e:
    logger.error(f"Failed to load crypto alerts: {e}")

# Import 10bis handler module
TENBIS_AVAILABLE = False
try:
    from tenbis_handler import TenbisHandler, format_voucher_message, generate_html_report
    TENBIS_AVAILABLE = True
    logger.info("10bis handler module loaded successfully")
except ImportError as e:
    logger.warning(f"10bis handler not available: {e}")
except Exception as e:
    logger.error(f"Failed to load 10bis handler: {e}")

# Import finance handler module
FINANCE_AVAILABLE = False
try:
    from finance_handler import format_index_report, test_symbol, get_stock_info
    FINANCE_AVAILABLE = True
    logger.info("Finance handler module loaded successfully")
except ImportError as e:
    logger.warning(f"Finance handler not available: {e}")
except Exception as e:
    logger.error(f"Failed to load finance handler: {e}")

# Import TA-125 scanner module
TA125_AVAILABLE = False
try:
    from ta125_scanner import scan_ta125_async, format_ta125_report
    TA125_AVAILABLE = True
    logger.info("TA-125 scanner module loaded successfully")
except ImportError as e:
    logger.warning(f"TA-125 scanner not available: {e}")
except Exception as e:
    logger.error(f"Failed to load TA-125 scanner: {e}")

# Create separate logger for user activity only
user_logger = logging.getLogger("user_activity")
user_handler = logging.FileHandler('user_activity.log', encoding='utf-8')
user_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
user_logger.addHandler(user_handler)
user_logger.setLevel(logging.INFO)
user_logger.propagate = False  # Don't send to root logger

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple health check server for Docker/cloud monitoring"""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health_status = {
                'status': 'healthy',
                'service': 'VB_International_BOT',
                'version': '1.1.0'
            }
            
            response = str(health_status).replace("'", '"')
            self.wfile.write(response.encode())
        else:
            self.send_response(404)

class TelegramBot:
    """Main Telegram Bot class"""
    
    def __init__(self, token: str):
        """Initialize the bot with token"""
        self.token = token
        self.application = Application.builder().token(token).build()
        self.network_tools = NetworkTools()
        self.range_scanner = IPRangeScanner(max_workers=1000, timeout=2.0)
        
        # Initialize crypto alerts if available
        self.crypto_manager = None
        if CRYPTO_ALERTS_AVAILABLE:
            taapi_key = os.getenv('TAAPIIO_APIKEY')
            self.crypto_manager = CryptoAlertManager(taapi_key)
            logger.info("Crypto alert manager initialized")
        
        # Initialize 10bis handlers dictionary for users
        self.tenbis_handlers = {}
        self.tenbis_auth_states = {}  # Track authentication state per user
        
        self.setup_handlers()

    def setup_handlers(self):
        """Setup command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("locate", self.locate_command))
        self.application.add_handler(CommandHandler("scan", self.port_scan_command))
        self.application.add_handler(CommandHandler("ping", self.ping_command))
        self.application.add_handler(CommandHandler("rangescan", self.range_scan_command))
        
        # Stock analysis command (if available)
        if STOCK_ANALYSIS_AVAILABLE:
            self.application.add_handler(CommandHandler("stock", self.stock_command))
            self.application.add_handler(CommandHandler("predict", self.predict_command))
        
        # Crypto alerts commands (if available)
        if CRYPTO_ALERTS_AVAILABLE and self.crypto_manager:
            self.application.add_handler(CommandHandler("newalert", self.new_alert_command))
            self.application.add_handler(CommandHandler("viewalerts", self.view_alerts_command))
            self.application.add_handler(CommandHandler("cancelalert", self.cancel_alert_command))
            self.application.add_handler(CommandHandler("getprice", self.get_price_command))
            self.application.add_handler(CommandHandler("priceall", self.price_all_command))
            self.application.add_handler(CommandHandler("getindicator", self.get_indicator_command))
            self.application.add_handler(CommandHandler("indicators", self.indicators_command))
        
        # 10bis commands (if available)
        if TENBIS_AVAILABLE:
            self.application.add_handler(CommandHandler("tenbis_login", self.tenbis_login_command))
            self.application.add_handler(CommandHandler("tenbis_vouchers", self.tenbis_vouchers_command))
            self.application.add_handler(CommandHandler("tenbis_logout", self.tenbis_logout_command))
            self.application.add_handler(CommandHandler("tenbis_html", self.tenbis_html_command))
        
        # Finance commands (if available)
        if FINANCE_AVAILABLE:
            self.application.add_handler(CommandHandler("finance", self.finance_command))
            self.application.add_handler(CommandHandler("financestock", self.finance_stock_command))
        
        # TA-125 scanner command (if available)
        if TA125_AVAILABLE:
            self.application.add_handler(CommandHandler("ta125scan", self.ta125_scan_command))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler for regular text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        logger.info(f"🚀 /start - משתמש: {user_name} (@{username}) | ID: {user_id}")
        user_logger.info(f"🚀 /start - משתמש: {user_name} (@{username}) | ID: {user_id}")
        welcome_message = f"""
🎉 שלום {user_name}! ברוך הבא! 

🚀 **VB Network Tools Bot** - כלי רשת מתקדם

�️ **מה אני יכול לעשות עבורך:**
🔍 איתור מיקום IP ודומיינים
🛡️ סריקת פורטים (מהיר ← מלא)
🏓 בדיקות Ping ומהירות
📊 ניתוח תשתיות רשת

⚡ **התחל מיד:**
/menu - תפריט נוח ואינטראקטיבי
/help - רשימת פקודות מלאה

🎯 **דוגמה מהירה:**
/locate google.com
/scan github.com quick
/ping 8.8.8.8

לחץ /menu להתחלה נוחה! 👆
"""
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        logger.info(f"❓ /help - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        help_text = """
📋 פקודות זמינות:

🔹 **בסיסיות:**
/start - התחלת השיחה עם הבוט
/help - הצגת עזרה
/menu - תפריט אינטראקטיבי

🔹 **כלי רשת:**
/locate <IP או דומיין> - איתור מיקום IP
/scan <IP או דומיין> [סוג] - בדיקת פורטים פתוחים
/ping <IP או דומיין> - בדיקת זמינות שרת
/rangescan <טווח IP> <פורט> - סריקת טווח IP לפורט ספציפי

🔹 **ניתוח מניות:**
/stock <סמל> - ניתוח מניה
/predict <סמל> [ימים] - חיזוי מחירים

� **התראות קריפטו:**
/newalert - יצירת התראה חדשה
/viewalerts - צפייה בהתראות
/cancelalert - ביטול התראה
/getprice - קבלת מחיר נוכחי
/priceall - כל המחירים
/getindicator - קבלת אינדיקטור טכני
/indicators - רשימת אינדיקטורים

� **מדד פיננסי:**
/finance - מדד הפיננסים הישראלי
/financestock <סמל> - בדיקת מניה ישראלית

🔹 **דוגמאות:**
/locate 8.8.8.8
/scan google.com
/stock AAPL
/newalert BTC/USDT PRICE ABOVE 50000
/getprice BTC/USDT
/tenbis_login user@email.com
/finance
/financestock PHOE.TA
/ta125scan

פשוט שלח לי הודעה ואני אענה לך!
"""
        await update.message.reply_text(help_text)

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command with inline keyboard"""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        logger.info(f"📋 /menu - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        keyboard = [
            [InlineKeyboardButton("🔍 כלי רשת", callback_data='network_tools')],
            [InlineKeyboardButton("📈 ניתוח מניות", callback_data='stock_tools')],
            [InlineKeyboardButton("💰 התראות קריפטו", callback_data='crypto_tools')],
            [InlineKeyboardButton("💹 מדד פיננסי ישראלי", callback_data='finance_tools')],
            [InlineKeyboardButton("📊 סריקת תא-125 (3 ימים שליליים)", callback_data='ta125_scan')],
            [InlineKeyboardButton("🍔 שוברי 10Bis", callback_data='tenbis_tools')],
            [InlineKeyboardButton("⚡ דוגמאות מהירות", callback_data='quick_examples')],
            [InlineKeyboardButton("❓ עזרה ומידע", callback_data='help_info')],
            [InlineKeyboardButton("📞 יצירת קשר", callback_data='contact')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "בחר אפשרות מהתפריט:",
            reply_markup=reply_markup
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()
        
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        logger.info(f"🔘 כפתור נלחץ: '{query.data}' - משתמש: {user_name} (@{username}) | ID: {user_id}")
        user_logger.info(f"🔘 כפתור נלחץ: '{query.data}' - משתמש: {user_name} (@{username}) | ID: {user_id}")

        # Main menu options
        if query.data == 'network_tools':
            # Network tools submenu
            keyboard = [
                [InlineKeyboardButton("📍 איתור IP/דומיין", callback_data='locate_demo')],
                [InlineKeyboardButton("🔍 סריקת פורטים", callback_data='scan_menu')],
                [InlineKeyboardButton("� סריקת טווחי IP", callback_data='range_scan_demo')],
                [InlineKeyboardButton("�🏓 בדיקת Ping", callback_data='ping_demo')],
                [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🛠️ **כלי רשת מתקדמים**\n\n"
                "בחר את הכלי שברצונך להשתמש בו:",
                reply_markup=reply_markup
            )
        
        elif query.data == 'stock_tools':
            if STOCK_ANALYSIS_AVAILABLE:
                # Stock analysis submenu
                keyboard = [
                    [InlineKeyboardButton("📊 ניתוח מניה", callback_data='stock_demo')],
                    [InlineKeyboardButton("🔮 חיזוי מחיר", callback_data='predict_demo')],
                    [InlineKeyboardButton("📋 דוגמאות", callback_data='stock_examples')],
                    [InlineKeyboardButton("❓ עזרה", callback_data='stock_help')],
                    [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📈 **כלי ניתוח מניות ובורסה**\n\n"
                    "🔍 ניתוח טכני מתקדם\n"
                    "🤖 חיזוי מחירים בבינה מלאכותית\n"
                    "📊 אינדיקטורים טכניים\n"
                    "📥 ייצוא נתונים לקבצים\n\n"
                    "בחר את הכלי שברצונך להשתמש בו:",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    "❌ **שירות ניתוח מניות לא זמין כרגע**\n\n"
                    "חסרים חבילות נדרשות לניתוח מניות.\n"
                    "אנא פנה למפתח הבוט לעדכון.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')
                    ]])
                )
        
        elif query.data == 'crypto_tools':
            if CRYPTO_ALERTS_AVAILABLE:
                # Crypto alerts submenu
                keyboard = [
                    [InlineKeyboardButton("💰 התראת מחיר", callback_data='crypto_price_demo')],
                    [InlineKeyboardButton("📊 התראה טכנית", callback_data='crypto_tech_demo')],
                    [InlineKeyboardButton("📋 צפייה בהתראות", callback_data='crypto_view')],
                    [InlineKeyboardButton("💵 מחיר נוכחי", callback_data='crypto_price')],
                    [InlineKeyboardButton("📈 אינדיקטורים", callback_data='crypto_indicators')],
                    [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "💰 **התראות קריפטו מתקדמות**\n\n"
                    "📊 התראות מחיר (ABOVE/BELOW/PCTCHG/24HR)\n"
                    "📈 אינדיקטורים טכניים (RSI/MACD/BBANDS/SMA/EMA)\n"
                    "⏰ מערכת Cooldown חכמה\n"
                    "🔔 התראות אוטומטיות\n"
                    "💹 תמיכה בכל זוגות Binance\n\n"
                    "בחר את הכלי שברצונך להשתמש בו:",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    "❌ **שירות התראות קריפטו לא זמין כרגע**\n\n"
                    "חסרים חבילות נדרשות להתראות קריפטו.\n"
                    "אנא פנה למפתח הבוט לעדכון.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')
                    ]])
                )
        
        elif query.data == 'tenbis_tools':
            if TENBIS_AVAILABLE:
                # 10Bis submenu
                keyboard = [
                    [InlineKeyboardButton("🔐 התחבר לחשבון", callback_data='tenbis_login_demo')],
                    [InlineKeyboardButton("🎫 הצג שוברים", callback_data='tenbis_vouchers_demo')],
                    [InlineKeyboardButton("� הורד קובץ HTML", callback_data='tenbis_html_demo')],
                    [InlineKeyboardButton("📋 הוראות שימוש", callback_data='tenbis_help')],
                    [InlineKeyboardButton("👋 התנתק", callback_data='tenbis_logout_demo')],
                    [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "🍔 **שוברי 10Bis**\n\n"
                    "🔐 התחבר לחשבון 10Bis שלך\n"
                    "🎫 צפה בכל השוברים הפעילים\n"
                    "📄 הורד קובץ HTML אינטראקטיבי\n"
                    "📸 קבל ברקודים לסריקה\n"
                    "💰 סיכום סכומים\n"
                    "💾 שמירת session אוטומטית\n\n"
                    "בחר פעולה:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **שירות 10Bis לא זמין כרגע**\n\n"
                    "חסרים חבילות נדרשות לשירות 10Bis.\n"
                    "אנא פנה למפתח הבוט לעדכון.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')
                    ]])
                )
        
        elif query.data == 'finance_tools':
            if FINANCE_AVAILABLE:
                # Finance submenu
                keyboard = [
                    [InlineKeyboardButton("📊 מדד הפיננסים", callback_data='finance_index')],
                    [InlineKeyboardButton("🔍 בדיקת מניה", callback_data='finance_stock_demo')],
                    [InlineKeyboardButton("📋 עזרה", callback_data='finance_help')],
                    [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "💹 **מדד הפיננסים הישראלי**\n\n"
                    "📊 מעקב בזמן אמת אחר מדד הפיננסים\n"
                    "💰 מחירי מניות עדכניים\n"
                    "📈 שינויים אחוזיים\n"
                    "🏦 כל המניות הפיננסיות המובילות\n\n"
                    "בחר פעולה:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **שירות Finance לא זמין כרגע**\n\n"
                    "חסרים חבילות נדרשות לשירות Finance.\n"
                    "אנא פנה למפתח הבוט לעדכון.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')
                    ]])
                )
        
        elif query.data == 'scan_menu':
            # Port scanning submenu with different scan types
            keyboard = [
                [InlineKeyboardButton("⚡ סריקה מהירה", callback_data='scan_quick_help')],
                [InlineKeyboardButton("🔍 סריקה נפוצה", callback_data='scan_common_help')],
                [InlineKeyboardButton("💯 Top 100 פורטים", callback_data='scan_top100_help')],
                [InlineKeyboardButton("🌐 Web Services", callback_data='scan_web_help')],
                [InlineKeyboardButton("🔥 סריקה מלאה (1-65535)", callback_data='scan_full_help')],
                [InlineKeyboardButton("🔙 חזרה", callback_data='network_tools')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🔍 **סוגי סריקת פורטים**\n\n"
                "בחר את סוג הסריקה המתאים לך:\n\n"
                "⚡ **מהירה** - 13 פורטים חשובים\n"
                "🔍 **נפוצה** - 19 פורטים נפוצים\n" 
                "💯 **Top 100** - 100 הפורטים הנפוצים\n"
                "🌐 **Web** - פורטי שירותי אינטרנט\n"
                "🔥 **מלאה** - כל הפורטים (איטית מאוד!)\n\n"
                "💡 **טיפ:** התחל עם סריקה מהירה",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif query.data == 'quick_examples':
            # Quick examples submenu
            keyboard = [
                [InlineKeyboardButton("🔗 דוגמאות איתור IP", callback_data='examples_locate')],
                [InlineKeyboardButton("🔍 דוגמאות סריקה", callback_data='examples_scan')], 
                [InlineKeyboardButton("🏓 דוגמאות Ping", callback_data='examples_ping')],
                [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📚 **דוגמאות שימוש מהיר**\n\n"
                "בחר קטגוריה לצפייה בדוגמאות:",
                reply_markup=reply_markup
            )
        
        elif query.data == 'help_info':
            # Help and info submenu
            keyboard = [
                [InlineKeyboardButton("📋 רשימת פקודות", callback_data='help_commands')],
                [InlineKeyboardButton("ℹ️ אודות הבוט", callback_data='about_bot')],
                [InlineKeyboardButton("🛡️ אבטחה ואתיקה", callback_data='security_info')],
                [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❓ **מידע ועזרה**\n\n"
                "בחר נושא למידע נוסף:",
                reply_markup=reply_markup
            )
        
        # Back to main menu
        elif query.data == 'main_menu':
            keyboard = [
                [InlineKeyboardButton("🔍 כלי רשת", callback_data='network_tools')],
                [InlineKeyboardButton("📈 ניתוח מניות", callback_data='stock_tools')],
                [InlineKeyboardButton("💰 התראות קריפטו", callback_data='crypto_tools')],
                [InlineKeyboardButton("💹 מדד פיננסי ישראלי", callback_data='finance_tools')],
                [InlineKeyboardButton("📊 סריקת תא-125 (3 ימים שליליים)", callback_data='ta125_scan')],
                [InlineKeyboardButton("🍔 שוברי 10Bis", callback_data='tenbis_tools')],
                [InlineKeyboardButton("⚡ דוגמאות מהירות", callback_data='quick_examples')],
                [InlineKeyboardButton("❓ עזרה ומידע", callback_data='help_info')],
                [InlineKeyboardButton("📞 יצירת קשר", callback_data='contact')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎯 **תפריט ראשי**\n\n"
                "בחר אפשרות:",
                reply_markup=reply_markup
            )
        
        # Finance callbacks
        elif query.data == 'finance_index':
            await query.answer("טוען נתוני מדד...")
            report = format_index_report()
            try:
                await query.edit_message_text(
                    report,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 רענן", callback_data='finance_index'),
                        InlineKeyboardButton("🔙 חזרה", callback_data='finance_tools')
                    ]])
                )
            except Exception as e:
                # If message is the same, just answer the callback without error
                if "message is not modified" in str(e).lower():
                    await query.answer("הנתונים עדכניים ✓", show_alert=False)
                else:
                    logger.error(f"Error updating finance index: {e}")
                    await query.answer("שגיאה בעדכון נתונים", show_alert=True)
        
        elif query.data == 'finance_stock_demo':
            await query.edit_message_text(
                "🔍 **בדיקת מניה**\n\n"
                "לבדיקת מחיר מניה ספציפית:\n\n"
                "**שימוש:**\n"
                "`/financestock PHOE.TA`\n"
                "`/financestock LUMI.TA`\n\n"
                "**דוגמאות:**\n"
                "• `/financestock PHOE.TA` - פניקס\n"
                "• `/financestock POLI.TA` - פועלים\n"
                "• `/financestock LUMI.TA` - לאומי\n",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 חזרה", callback_data='finance_tools')
                ]])
            )
        
        elif query.data == 'finance_help':
            await query.edit_message_text(
                "📋 **עזרה - מדד פיננסי**\n\n"
                "**פקודות זמינות:**\n"
                "• `/finance` - הצגת מדד הפיננסים\n"
                "• `/financestock <סמל>` - מידע על מניה\n\n"
                "**מניות במדד:**\n"
                "PHOE.TA, POLI.TA, LUMI.TA, MZTF.TA,\n"
                "DSCT.TA, HARL.TA, MNRA.TA, FIBI.TA,\n"
                "CLIS.TA, MGDL.TA, FIBIH.TA\n",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 חזרה", callback_data='finance_tools')
                ]])
            )
        
            await query.edit_message_text(
                "📋 **עזרה - מדד פיננסי**\n\n"
                "**פקודות זמינות:**\n"
                "• `/finance` - הצגת מדד הפיננסים\n"
                "• `/financestock <סמל>` - מידע על מניה\n\n"
                "**מניות במדד:**\n"
                "PHOE.TA, POLI.TA, LUMI.TA, MZTF.TA,\n"
                "DSCT.TA, HARL.TA, MNRA.TA, FIBI.TA,\n"
                "CLIS.TA, MGDL.TA, FIBIH.TA\n",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 חזרה", callback_data='finance_tools')
                ]])
            )
        
        # TA-125 scanner callback
        elif query.data == 'ta125_scan':
            if TA125_AVAILABLE:
                await query.edit_message_text(
                    "⏳ **סורק מדד תא-125...**\n\n"
                    "מוריד נתונים עבור ~125 מניות ובודק 3 ימי מסחר אחרונים.\n"
                    "הסריקה עשויה לקחת כ-30-60 שניות, אנא המתן...",
                    parse_mode='Markdown'
                )
                try:
                    negative_stocks, total_scanned, failed_count = await scan_ta125_async()
                    report = format_ta125_report(negative_stocks, total_scanned, failed_count)
                    await query.edit_message_text(
                        report,
                        parse_mode='MarkdownV2',
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 סרוק שוב", callback_data='ta125_scan')],
                            [InlineKeyboardButton("🔙 חזרה לתפריט", callback_data='main_menu')]
                        ])
                    )
                except Exception as e:
                    logger.error(f"Error in ta125_scan callback: {e}")
                    await query.edit_message_text(
                        "❌ **שגיאה בסריקת תא-125**\n\nאנא נסה שוב מאוחר יותר.",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 חזרה לתפריט", callback_data='main_menu')
                        ]])
                    )
            else:
                await query.edit_message_text(
                    "❌ **סריקת תא-125 לא זמינה**\n\nחסרות חבילות נדרשות.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 חזרה לתפריט", callback_data='main_menu')
                    ]])
                )
        
        # Detailed scan type help
        elif query.data == 'scan_quick_help':
            await query.edit_message_text(
                "⚡ **סריקה מהירה**\n\n"
                "סורקת 13 פורטים חשובים בלבד\n"
                "⏱️ זמן סריקה: ~3-5 שניות\n\n"
                "**שימוש:**\n"
                "`/scan google.com quick`\n"
                "`/scan 192.168.1.1 quick`\n\n"
                "**פורטים נסרקים:**\n"
                "21 (FTP), 22 (SSH), 23 (Telnet)\n"
                "25 (SMTP), 53 (DNS), 80 (HTTP)\n"
                "110 (POP3), 143 (IMAP), 443 (HTTPS)\n"
                "993 (IMAPS), 995 (POP3S)\n"
                "3389 (RDP), 8080 (HTTP-Alt)",
                parse_mode='Markdown'
            )
        
        elif query.data == 'scan_common_help':
            await query.edit_message_text(
                "🔍 **סריקה נפוצה** (ברירת מחדל)\n\n"
                "סורקת 19 פורטים הכי נפוצים\n"
                "⏱️ זמן סריקה: ~5-8 שניות\n\n"
                "**שימוש:**\n"
                "`/scan google.com`\n"
                "`/scan github.com common`\n\n"
                "**כוללת:** FTP, SSH, HTTP/HTTPS, Email, DNS, Databases ועוד",
                parse_mode='Markdown'
            )
        
        elif query.data == 'scan_top100_help':
            await query.edit_message_text(
                "💯 **Top 100 פורטים**\n\n"
                "סורקת 100 הפורטים הנפוצים ביותר\n"
                "⏱️ זמן סריקה: ~15-30 שניות\n\n"
                "**שימוש:**\n"
                "`/scan target.com top100`\n\n"
                "**מומלצ עבור:** שרתים, אתרים, בדיקות אבטחה מקיפות",
                parse_mode='Markdown'
            )
        
        elif query.data == 'scan_web_help':
            await query.edit_message_text(
                "🌐 **Web Services**\n\n"
                "מתמחה בפורטי שירותי אינטרנט\n"
                "⏱️ זמן סריקה: ~3-5 שניות\n\n"
                "**שימוש:**\n"
                "`/scan example.com web`\n\n"
                "**פורטים:** 80, 443, 8000, 8008, 8080, 8081, 8443, 8888, 3000-5001, 9000-9001\n\n"
                "**מושלם עבור:** אתרים, API servers, Dev servers",
                parse_mode='Markdown'
            )
        
        elif query.data == 'scan_full_help':
            keyboard = [
                [InlineKeyboardButton("⚠️ אני מבין - המשך", callback_data='scan_full_confirm')],
                [InlineKeyboardButton("🔙 חזרה", callback_data='scan_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "� **סריקה מלאה (1-65535)**\n\n"
                "⚠️ **אזהרה חשובה!**\n\n"
                "• סורקת **כל** 65,535 פורטים\n"
                "• יכולה לקחת **5-15 דקות**\n"
                "• עלולה להעמיס על השרת היעד\n"
                "• יכולה להפעיל מערכות אבטחה\n\n"
                "🛡️ **השתמש רק עבור:**\n"
                "• שרתים שלך\n"
                "• רשתות פנימיות\n"
                "• בדיקות מורשות\n\n"
                "**שימוש:** `/scan target.com full`",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif query.data == 'scan_full_confirm':
            await query.edit_message_text(
                "🔥 **מידע על סריקה מלאה**\n\n"
                "**פקודה:** `/scan <target> full`\n\n"
                "**דוגמה:** `/scan 192.168.1.1 full`\n\n"
                "⚠️ **זכור:** השתמש באחריות ורק על מערכות מורשות!\n\n"
                "⏳ **סבלנות:** התהליך יכול לקחת זמן רב...",
                parse_mode='Markdown'
            )
        
        # Examples sections
        elif query.data == 'examples_locate':
            await query.edit_message_text(
                "🔗 **דוגמאות איתור IP/דומיין**\n\n"
                "**פקודה:** `/locate <target>`\n\n"
                "🌍 **אתרים פופולריים:**\n"
                "• `/locate google.com`\n"
                "• `/locate facebook.com`\n"
                "• `/locate github.com`\n\n"
                "🏠 **שרתי DNS:**\n"
                "• `/locate 8.8.8.8` (Google)\n"
                "• `/locate 1.1.1.1` (Cloudflare)\n\n"
                "🏢 **רשתות פנימיות:**\n"
                "• `/locate 192.168.1.1`\n"
                "• `/locate 10.0.0.1`",
                parse_mode='Markdown'
            )
        
        elif query.data == 'examples_scan':
            await query.edit_message_text(
                "� **דוגמאות סריקת פורטים**\n\n"
                "⚡ **מהיר:**\n"
                "• `/scan google.com quick`\n"
                "• `/scan 192.168.1.1 quick`\n\n"
                "🔍 **רגיל:**\n"
                "• `/scan github.com`\n"
                "• `/scan example.com common`\n\n"
                "🌐 **Web:**\n"
                "• `/scan mysite.com web`\n\n"
                "💯 **מקיף:**\n"
                "• `/scan server.local top100`\n\n"
                "� **מלא (זהירות!):**\n"
                "• `/scan 192.168.1.100 full`",
                parse_mode='Markdown'
            )
        
        elif query.data == 'examples_ping':
            await query.edit_message_text(
                "🏓 **דוגמאות בדיקת Ping**\n\n"
                "**פקודה:** `/ping <target>`\n\n"
                "🌐 **אתרים:**\n"
                "• `/ping google.com`\n"
                "• `/ping github.com`\n"
                "• `/ping stackoverflow.com`\n\n"
                "🔧 **שרתי DNS:**\n"
                "• `/ping 8.8.8.8`\n"
                "• `/ping 1.1.1.1`\n\n"
                "🏠 **רשת מקומית:**\n"
                "• `/ping 192.168.1.1`\n"
                "• `/ping router.local`",
                parse_mode='Markdown'
            )
        
        elif query.data == 'help_commands':
            await query.edit_message_text(
                "📋 **רשימת פקודות מלאה**\n\n"
                "🔹 **בסיסיות:**\n"
                "• `/start` - התחלה\n"
                "• `/help` - עזרה\n"
                "• `/menu` - תפריט\n\n"
                "🔹 **כלי רשת:**\n"
                "• `/locate <target>` - איתור IP\n"
                "• `/scan <target> [type]` - סריקת פורטים\n"
                "• `/ping <target>` - בדיקת זמינות\n\n"
                "🔹 **סוגי סריקה:**\n"
                "`quick`, `common`, `top100`, `web`, `full`",
                parse_mode='Markdown'
            )
        
        elif query.data == 'about_bot':
            await query.edit_message_text(
                "🤖 **אודות הבוט**\n\n"
                "**שם:** VB Network Tools Bot\n"
                "**גרסה:** 2.0\n"
                "**מפתח:** @VB_International\n\n"
                "�️ **טכנולוגיות:**\n"
                "• Python 3.13\n"
                "• python-telegram-bot\n"
                "• Railway Cloud\n\n"
                "🎯 **מטרה:**\n"
                "כלי רשת נוח ובטוח לבדיקות אבטחה ואבחון רשתות",
                parse_mode='Markdown'
            )
        
        elif query.data == 'security_info':
            await query.edit_message_text(
                "🛡️ **אבטחה ואתיקה**\n\n"
                "⚖️ **חוקים:**\n"
                "• השתמש רק במערכות מורשות\n"
                "• אל תסרוק רשתות זרות\n"
                "• כבד מדיניות שימוש\n\n"
                "🎯 **שימושים חוקיים:**\n"
                "• בדיקת הרשת שלך\n"
                "• אבחון בעיות\n"
                "• בדיקות אבטחה מורשות\n\n"
                "❌ **אל תשתמש עבור:**\n"
                "• חדירה לא מורשת\n"
                "• סריקת רשתות זרות\n"
                "• פעילות בלתי חוקית\n\n"
                "⚠️ **הבוט לא אחראי לשימוש לא נכון**",
                parse_mode='Markdown'
            )
        elif query.data == 'locate_another':
            await query.edit_message_text(
                "🔍 **איתור IP חדש**\n\n"
                "השתמש בפקודה:\n"
                "`/locate <IP או דומיין>`\n\n"
                "דוגמאות:\n"
                "• `/locate 1.1.1.1`\n"
                "• `/locate facebook.com`\n"
                "• `/locate 192.168.1.1`",
                parse_mode='Markdown'
            )
        elif query.data == 'scan_another':
            await query.edit_message_text(
                "🔍 **סריקת פורטים חדשה**\n\n"
                "השתמש בפקודה:\n"
                "`/scan <IP או דומיין> [סוג]`\n\n"
                "דוגמאות:\n"
                "• `/scan google.com`\n"
                "• `/scan 192.168.1.1 quick`\n"
                "• `/scan github.com top100`",
                parse_mode='Markdown'
            )
        elif query.data == 'ping_another':
            await query.edit_message_text(
                "🏓 **Ping Test חדש**\n\n"
                "השתמש בפקודה:\n"
                "`/ping <IP או דומיין>`\n\n"
                "דוגמאות:\n"
                "• `/ping google.com`\n"
                "• `/ping 8.8.8.8`\n"
                "• `/ping github.com`",
                parse_mode='Markdown'
            )
        elif query.data == 'contact':
            await query.edit_message_text("📞 ליצירת קשר שלח הודעה פרטית למפתח @VB_International")
        
        # Main menu handler
        elif query.data == 'main_menu':
            keyboard = [
                [InlineKeyboardButton("🔍 כלי רשת", callback_data='network_tools')],
                [InlineKeyboardButton("📈 ניתוח מניות", callback_data='stock_tools')],
                [InlineKeyboardButton("💰 התראות קריפטו", callback_data='crypto_tools')],
                [InlineKeyboardButton("🍔 שוברי 10Bis", callback_data='tenbis_tools')],
                [InlineKeyboardButton("⚡ דוגמאות מהירות", callback_data='quick_examples')],
                [InlineKeyboardButton("❓ עזרה ומידע", callback_data='help_info')],
                [InlineKeyboardButton("📞 יצירת קשר", callback_data='contact')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "בחר אפשרות מהתפריט:",
                reply_markup=reply_markup
            )
        
        # 10Bis demo handlers
        elif query.data == 'tenbis_login_demo':
            await query.edit_message_text(
                "🔐 **התחברות ל-10Bis**\n\n"
                "**שלב 1:** שלח את האימייל שלך\n"
                "`/tenbis_login your@email.com`\n\n"
                "**שלב 2:** תקבל קוד ל-SMS/Email\n"
                "פשוט שלח את הקוד כהודעה רגילה\n\n"
                "**דוגמה:**\n"
                "• `/tenbis_login user@example.com`\n"
                "• `123456` (הקוד שקיבלת)\n\n"
                "🔒 **הסשן נשמר** - לא צריך להתחבר כל פעם!",
                parse_mode='Markdown'
            )
        
        elif query.data == 'tenbis_vouchers_demo':
            await query.edit_message_text(
                "🎫 **צפייה בשוברים פעילים**\n\n"
                "**שימוש:** `/tenbis_vouchers [חודשים]`\n\n"
                "🔹 **דוגמאות:**\n"
                "• `/tenbis_vouchers` - 12 חודשים (ברירת מחדל)\n"
                "• `/tenbis_vouchers 6` - 6 חודשים אחורה\n"
                "• `/tenbis_vouchers 24` - שנתיים אחורה\n\n"
                "📊 **מה תקבל:**\n"
                "• מספר שוברים פעילים\n"
                "• סכום כולל\n"
                "• פירוט כל שובר\n"
                "• תמונת ברקוד לסריקה\n\n"
                "� **רוצה קובץ HTML?**\n"
                "השתמש ב-`/tenbis_html` לקובץ אינטראקטיבי!\n\n"
                "�💡 **טיפ:** התחל עם /tenbis_vouchers לראות הכל",
                parse_mode='Markdown'
            )
        
        elif query.data == 'tenbis_help':
            await query.edit_message_text(
                "📖 **מדריך שימוש מהיר - 10Bis**\n\n"
                "**1️⃣ התחברות:**\n"
                "`/tenbis_login your@email.com`\n"
                "שלח את הקוד שתקבל\n\n"
                "**2️⃣ צפייה בשוברים:**\n"
                "`/tenbis_vouchers`\n\n"
                "**3️⃣ התנתקות:**\n"
                "`/tenbis_logout`\n\n"
                "❓ **שאלות נפוצות:**\n"
                "• צריך להתחבר כל פעם? **לא!**\n"
                "• קוד לא עובד? **וודא 6 ספרות בלי רווחים**\n"
                "• אין שוברים? **נסה תקופה ארוכה יותר**\n\n"
                "📚 **מדריך מלא:** [TENBIS_QUICK_START.md](https://github.com/VictorBramy/telegramBot/blob/main/TENBIS_QUICK_START.md)",
                parse_mode='Markdown'
            )
        
        elif query.data == 'tenbis_logout_demo':
            await query.edit_message_text(
                "👋 **התנתקות מ-10Bis**\n\n"
                "**פקודה:** `/tenbis_logout`\n\n"
                "🗑️ **מה קורה:**\n"
                "• מחיקת session שמור\n"
                "• מחיקת tokens\n"
                "• ניקוי מידע מקומי\n\n"
                "⚠️ **לאחר התנתקות:**\n"
                "תצטרך להתחבר שוב עם `/tenbis_login`\n\n"
                "🔒 **אבטחה:** מומלץ להתנתק אם משתמש במכשיר משותף",
                parse_mode='Markdown'
            )
        
        elif query.data == 'tenbis_html_demo':
            await query.edit_message_text(
                "📄 **הורדת קובץ HTML אינטראקטיבי**\n\n"
                "**שימוש:** `/tenbis_html [חודשים]`\n\n"
                "🔹 **דוגמאות:**\n"
                "• `/tenbis_html` - 12 חודשים\n"
                "• `/tenbis_html 6` - 6 חודשים\n"
                "• `/tenbis_html 24` - שנתיים\n\n"
                "✨ **תכונות הקובץ:**\n"
                "• 🖼️ גלריית ברקודים אינטראקטיבית\n"
                "• 📱 ממשק ידידותי לנייד\n"
                "• 🔍 לחיצה על ברקוד לסריקה מהירה\n"
                "• ⌨️ ניווט עם חצי מקלדת\n"
                "• 📊 סיכום מלא של כל השוברים\n"
                "• 💾 עובד גם בלי אינטרנט!\n\n"
                "💡 **טיפ:** הורד את הקובץ ופתח בדפדפן בנייד!\n"
                "📸 תוכל להראות ברקודים בקופה בקליק אחד",
                parse_mode='Markdown'
            )
        
        # Demo handlers for menu navigation
        elif query.data == 'ping_demo':
            await query.edit_message_text(
                "🏓 **בדיקת Ping מתקדמת**\n\n"
                "בדוק זמינות ומהירות תגובה!\n"
                "`/ping <IP או דומיין>`\n\n"
                "🔹 **דוגמאות:**\n"
                "• **שרתי Google:** `/ping 8.8.8.8`\n"
                "• **אתרים:** `/ping google.com`\n"
                "• **CDN:** `/ping cloudflare.com`\n\n"
                "📊 **מה תקבל:**\n"
                "• זמן תגובה במילישניות\n"
                "• סטטוס זמינות\n"
                "• TTL (Time To Live)\n"
                "• אחוז אובדן חבילות",
                parse_mode='Markdown'
            )
        
        elif query.data == 'scan_demo':
            await query.edit_message_text(
                "🔍 **סריקת פורטים מקצועית**\n\n"
                "גלה פורטים פתוחים בשרתים!\n"
                "`/scan <IP או דומיין> [רמה]`\n\n"
                "🔹 **רמות סריקה:**\n"
                "• **מהירה:** `/scan 192.168.1.1 quick`\n"
                "• **נפוצה:** `/scan google.com common`\n"
                "• **מלאה:** `/scan 8.8.8.8 top100`\n\n"
                "🎯 **תוצאות:**\n"
                "• פורטים פתוחים\n"
                "• שירותים מזוהים\n"
                "• זמני תגובה\n"
                "• אפשרות הורדת תוצאות",
                parse_mode='Markdown'
            )
        
        elif query.data == 'locate_demo':
            await query.edit_message_text(
                "📍 **איתור מיקום IP מתקדם**\n\n"
                "מצא מיקום גאוגרפי של כל IP!\n"
                "`/locate <IP או דומיין>`\n\n"
                "🔹 **דוגמאות:**\n"
                "• **שרתי גוגל:** `/locate 8.8.8.8`\n"
                "• **אתרים:** `/locate facebook.com`\n"
                "• **שרתים:** `/locate 1.1.1.1`\n\n"
                "🌍 **מידע מפורט:**\n"
                "• מדינה ועיר\n"
                "• ספק שירות (ISP)\n"
                "• קואורדינטות GPS\n"
                "• ציון אמינות מ-5 מקורות",
                parse_mode='Markdown'
            )
        
        elif query.data == 'range_scan_demo':
            await query.edit_message_text(
                "🎯 **סריקת טווח IP מתקדמת**\n\n"
                "סרוק אלפי IP במהירות הבזק!\n"
                "`/rangescan <טווח> <פורט>`\n\n"
                "🔹 **פורמטים נתמכים:**\n"
                "• **CIDR:** `/rangescan 192.168.1.0/24 22`\n"
                "• **טווח:** `/rangescan 213.0.0.0-213.0.0.255 5900`\n"
                "• **IP יחיד:** `/rangescan 8.8.8.8 80`\n\n"
                "⚡ **ביצועים:**\n"
                "• עד 1000+ IP לשנייה\n"
                "• מחפש שרתי VNC, SSH, HTTP\n"
                "• עדכוני התקדמות בזמן אמת\n"
                "• הורדת תוצאות מלאות",
                parse_mode='Markdown'
            )
        
        elif query.data == 'confirm_large_scan':
            # Handle large range scan confirmation
            if hasattr(self, 'pending_scan'):
                ip_range = self.pending_scan['range']
                port = self.pending_scan['port']
                
                user_name = update.effective_user.first_name
                user_id = update.effective_user.id
                username = update.effective_user.username or "ללא שם משתמש"
                
                logger.info(f"🎯 /rangescan CONFIRMED '{ip_range}' פורט {port} - משתמש: {user_name} (@{username}) | ID: {user_id}")
                user_logger.info(f"🎯 /rangescan CONFIRMED '{ip_range}' פורט {port} - משתמש: {user_name} (@{username}) | ID: {user_id}")
                
                # Show processing message
                await query.edit_message_text(
                    f"🚀 **מתחיל סריקה מאושרת**\n\n"
                    f"📍 **טווח:** `{ip_range}`\n"
                    f"🔍 **פורט:** `{port}`\n\n"
                    f"🧵 **מכין {self.range_scanner.max_workers} threads...**\n"
                    f"⏳ **התחלת סריקה...**",
                    parse_mode='Markdown'
                )
                
                # Progress callback function
                async def progress_callback(scanned, total, found):
                    progress_percent = (scanned / total) * 100
                    bar_length = 20
                    filled = int(bar_length * scanned / total)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    
                    try:
                        await query.edit_message_text(
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
                
                try:
                    # Perform the range scan
                    result = await self.range_scanner.scan_range_async(
                        ip_range, port, progress_callback
                    )
                    
                    # Format results
                    result_text = format_range_scan_result(result)
                    
                    # Store scan result for download
                    self.last_range_scan_result = result
                    
                    # Create inline keyboard for additional options
                    keyboard = [
                        [InlineKeyboardButton("💾 הורד תוצאות CSV", callback_data='download_range_csv'),
                         InlineKeyboardButton("📄 הורד כ-JSON", callback_data='download_range_json')],
                        [InlineKeyboardButton("📝 הורד כ-TXT", callback_data='download_range_txt')],
                        [InlineKeyboardButton("🔄 סרוק טווח אחר", callback_data='range_scan_demo')],
                        [InlineKeyboardButton("🔍 סריקת פורטים רגילה", callback_data='scan_menu')],
                        [InlineKeyboardButton("📍 איתור IP", callback_data='locate_demo')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        result_text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                    
                    # Clean up pending scan
                    delattr(self, 'pending_scan')
                    
                except RuntimeError as e:
                    if "can't start new thread" in str(e):
                        logger.error(f"Thread exhaustion error: {e}")
                        await query.edit_message_text(
                            f"⚠️ **משאבי מערכת מוגבלים**\n\n"
                            f"🔍 **טווח:** `{ip_range}`\n"
                            f"🎯 **פורט:** `{port}`\n\n"
                            f"❗ **הבעיה:** יותר מדי threads פעילים\n\n"
                            f"💡 **פתרונות:**\n"
                            f"• המתן 30 שניות ונסה שוב\n"
                            f"• נסה טווח קטן יותר (עד 10,000 IPs)\n"
                            f"• פנה למפתח לשדרוג שרת\n\n"
                            f"🔄 **נסה שוב בקרוב...**",
                            parse_mode='Markdown'
                        )
                    else:
                        raise e
                except Exception as e:
                    logger.error(f"Error in confirmed range scan: {e}")
                    await query.edit_message_text(
                        f"❌ **שגיאה בסריקת הטווח**\n\n"
                        f"🔍 **טווח:** `{ip_range}`\n"
                        f"🎯 **פורט:** `{port}`\n"
                        f"❗ **שגיאה:** `{str(e)}`\n\n"
                        f"💡 **טיפים:**\n"
                        f"• נסה טווח קטן יותר\n"
                        f"• בדוק חיבור לאינטרנט\n"
                        f"• נסה שוב מאוחר יותר",
                        parse_mode='Markdown'
                    )
            else:
                await query.edit_message_text("❌ נתוני הסריקה לא נמצאו. נסה שוב.")
        
        # Download handlers for port scan results
        elif query.data == 'download_port_csv':
            await self.send_scan_file(query, context, 'port_scan', 'csv')
        elif query.data == 'download_port_json':
            await self.send_scan_file(query, context, 'port_scan', 'json')
        elif query.data == 'download_port_txt':
            await self.send_scan_file(query, context, 'port_scan', 'txt')
        
        # Download handlers for range scan results
        elif query.data == 'download_range_csv':
            await self.send_scan_file(query, context, 'range_scan', 'csv')
        elif query.data == 'download_range_json':
            await self.send_scan_file(query, context, 'range_scan', 'json')
        elif query.data == 'download_range_txt':
            await self.send_scan_file(query, context, 'range_scan', 'txt')
        
        # Download handlers for ping results
        elif query.data == 'download_ping_csv':
            await self.send_scan_file(query, context, 'ping', 'csv')
        elif query.data == 'download_ping_json':
            await self.send_scan_file(query, context, 'ping', 'json')
        elif query.data == 'download_ping_txt':
            await self.send_scan_file(query, context, 'ping', 'txt')
        
        # Stock analysis handlers
        elif query.data == 'download_stock_csv':
            await self.send_stock_file(query, context, 'csv')
        elif query.data == 'download_stock_json':
            await self.send_stock_file(query, context, 'json')
        elif query.data == 'stock_demo':
            await query.edit_message_text(
                "📈 **ניתוח מניות מתקדם**\n\n"
                "גלה הכל על המניות שלך!\n"
                "`/stock <סמל מניה>`\n\n"
                "🔹 **מניות פופולריות:**\n"
                "• **טק:** `/stock AAPL`, `/stock MSFT`, `/stock GOOGL`\n"
                "• **AI:** `/stock NVDA`, `/stock AMD`, `/stock META`\n"
                "• **רכב:** `/stock TSLA`, `/stock F`, `/stock GM`\n"
                "• **כספים:** `/stock JPM`, `/stock BAC`, `/stock WFC`\n\n"
                "🔮 **חיזויים מתקדמים:**\n"
                "`/predict <סמל> [ימים]`\n\n"
                "🤖 **AI Features:**\n"
                "• מודלי Machine Learning\n"
                "• ניתוח מחוונים טכניים\n"
                "• תחזיות בטווח ביטחון\n"
                "• סיגנלים לקנייה/מכירה",
                parse_mode='Markdown'
            )
        
        # Handle stock prediction callbacks
        elif query.data.startswith('stock_predict_'):
            symbol = query.data.replace('stock_predict_', '')
            await query.edit_message_text(
                f"🔮 **חיזוי מפורט עבור {symbol}**\n\n"
                f"השתמש בפקודה:\n"
                f"`/predict {symbol} [ימים]`\n\n"
                f"דוגמאות:\n"
                f"• `/predict {symbol} 5` - חיזוי ל-5 ימים\n"
                f"• `/predict {symbol} 10` - חיזוי ל-10 ימים\n\n"
                f"🤖 החיזוי כולל:\n"
                f"• מחירים חזויים יומיים\n"
                f"• טווחי ביטחון\n"
                f"• רמת דיוק המודל\n"
                f"• ניתוח טרנד כללי",
                parse_mode='Markdown'
            )
        
        elif query.data.startswith('stock_full_'):
            symbol = query.data.replace('stock_full_', '')
            await query.edit_message_text(
                f"📈 **ניתוח מלא עבור {symbol}**\n\n"
                f"השתמש בפקודה:\n"
                f"`/stock {symbol}`\n\n"
                f"קבל ניתוח מקיף הכולל:\n"
                f"• מחוונים טכניים מתקדמים\n"
                f"• סיגנלים לקנייה/מכירה\n"
                f"• תחזיות AI\n"
                f"• רמות תמיכה והתנגדות\n"
                f"• ניתוח נפח וטרנדים",
                parse_mode='Markdown'
            )
        
        elif query.data.startswith('predict_again_'):
            symbol = query.data.replace('predict_again_', '')
            await query.edit_message_text(
                f"🔄 **חזרה על החיזוי עבור {symbol}**\n\n"
                f"השתמש שוב בפקודה:\n"
                f"`/predict {symbol} [ימים]`\n\n"
                f"או נסה תחזיות לטווחים שונים:\n"
                f"• `/predict {symbol} 3` - טווח קצר\n"
                f"• `/predict {symbol} 7` - שבוע\n"
                f"• `/predict {symbol} 15` - טווח בינוני\n"
                f"• `/predict {symbol} 30` - טווח ארוך",
                parse_mode='Markdown'
            )
        
        elif query.data == 'stock_demo':
            await query.edit_message_text(
                "📊 **ניתוח מניה מתקדם**\n\n"
                "קבל ניתוח טכני מקצועי של כל מניה!\n"
                "`/stock <סמל מניה>`\n\n"
                "🔹 **דוגמאות:**\n"
                "• **אפל:** `/stock AAPL`\n"
                "• **מיקרוסופט:** `/stock MSFT`\n"
                "• **גוגל:** `/stock GOOGL`\n"
                "• **טסלה:** `/stock TSLA`\n\n"
                "📊 **הניתוח כולל:**\n"
                "• מחיר נוכחי ושינוי יומי\n"
                "• RSI, MACD, בולינגר באנדס\n"
                "• ממוצעים נעים\n"
                "• אותות קנייה/מכירה\n"
                "• ייצוא נתונים ל-CSV/JSON",
                parse_mode='Markdown'
            )

        elif query.data == 'predict_demo':
            await query.edit_message_text(
                "🔮 **חיזוי מחירי מניות**\n\n"
                "חיזוי מחירים בבינה מלאכותית!\n"
                "`/predict <סמל מניה> [ימים]`\n\n"
                "🔹 **דוגמאות:**\n"
                "• **חיזוי שבוע:** `/predict AAPL 7`\n"
                "• **חיזוי חודש:** `/predict MSFT 30`\n"
                "• **חיזוי ברירת מחדל:** `/predict GOOGL`\n\n"
                "🤖 **הבינה המלאכותית:**\n"
                "• אלגוריתם Random Forest\n"
                "• אנליזה של 60 ימי מסחר\n"
                "• אינדיקטורים טכניים\n"
                "• רמת ודאות לחיזוי\n"
                "• טווח מחירים צפוי",
                parse_mode='Markdown'
            )

        elif query.data == 'stock_examples':
            await query.edit_message_text(
                "📋 **דוגמאות מניות פופולריות**\n\n"
                "🇺🇸 **מניות אמריקאיות:**\n"
                "• AAPL - Apple Inc.\n"
                "• MSFT - Microsoft\n"
                "• GOOGL - Alphabet (Google)\n"
                "• TSLA - Tesla\n"
                "• AMZN - Amazon\n"
                "• META - Meta (Facebook)\n"
                "• NVDA - NVIDIA\n"
                "• NFLX - Netflix\n\n"
                "💡 **טיפים:**\n"
                "• השתמש בסמלי מניות באנגלית\n"
                "• בדוק מניות בבורסת NASDAQ\n"
                "• נתוני היסטוריה מ-Yahoo Finance\n"
                "• עדכונים בזמן אמת",
                parse_mode='Markdown'
            )

        elif query.data == 'stock_help':
            await query.edit_message_text(
                "❓ **עזרה - כלי ניתוח מניות**\n\n"
                "📊 **פקודות זמינות:**\n"
                "• `/stock <סמל>` - ניתוח מלא\n"
                "• `/predict <סמל> [ימים]` - חיזוי AI\n\n"
                "🔹 **פורמט סמלי מניות:**\n"
                "• השתמש באותיות באנגלית בלבד\n"
                "• 1-5 תווים (לדוגמה: AAPL, MSFT)\n"
                "• רגיש לאותיות גדולות/קטנות\n\n"
                "📈 **אינדיקטורים טכניים:**\n"
                "• **RSI** - אינדיקס כוח יחסי (0-100)\n"
                "• **MACD** - קו מגמה מתכנס/מתפרק\n"
                "• **Bollinger Bands** - רצועות תנודתיות\n"
                "• **Moving Averages** - ממוצעים נעים\n\n"
                "🤖 **חיזוי בינה מלאכותית:**\n"
                "• אלגוריתם Random Forest מתקדם\n"
                "• ניתוח 60 ימי מסחר אחרונים\n"
                "• רמת ודאות וטווח חיזוי\n"
                "• ייצוא נתונים מפורטים",
                parse_mode='Markdown'
            )
        
        else:
            await query.edit_message_text("🤖 אפשרות לא מזוהה")

    async def send_stock_file(self, query, context, file_format: str):
        """Send stock analysis as a downloadable file"""
        import io
        import json
        from datetime import datetime
        
        try:
            # Get the stored analysis
            analysis = getattr(self, 'last_stock_analysis', None)
            if not analysis:
                await query.edit_message_text("❌ לא נמצא ניתוח מניה להורדה. בצע ניתוח תחילה.")
                return
            
            # Generate file content
            if file_format == 'csv':
                # Create CSV content for stock analysis
                content = self.format_stock_csv(analysis)
                mime_type = 'text/csv'
                file_ext = 'csv'
            elif file_format == 'json':
                content = json.dumps(analysis, indent=2, ensure_ascii=False, default=str)
                mime_type = 'application/json'
                file_ext = 'json'
            else:
                await query.edit_message_text("❌ פורמט קובץ לא תקין")
                return
            
            # Create filename
            symbol = analysis.get('symbol', 'UNKNOWN')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"TelegramBot_Stock_{symbol}_{timestamp}.{file_ext}"
            
            # Create file buffer
            file_buffer = io.BytesIO(content.encode('utf-8'))
            file_buffer.name = filename
            
            await query.edit_message_text("📤 מכין קובץ להורדה...")
            
            # Send file
            chat_id = query.message.chat_id
            user_name = query.from_user.first_name
            
            await context.bot.send_document(
                chat_id=chat_id,
                document=file_buffer,
                filename=filename,
                caption=f"📈 **ניתוח מניה - {symbol}**\n\n"
                       f"📅 **תאריך:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                       f"📁 **פורמט:** {file_format.upper()}\n"
                       f"👤 **הוכן עבור:** {user_name}\n\n"
                       f"💾 **הקובץ מוכן להורדה!**",
                parse_mode='Markdown'
            )
            
            await query.edit_message_text(
                f"✅ **קובץ ניתוח נשלח בהצלחה!**\n\n"
                f"📁 **שם קובץ:** `{filename}`\n"
                f"📊 **פורמט:** {file_format.upper()}\n"
                f"📈 **מניה:** {symbol}\n\n"
                f"💡 **הקובץ כולל:** ניתוח מלא עם תחזיות"
            )
            
        except Exception as e:
            logger.error(f"Error sending stock file: {e}")
            await query.edit_message_text(
                f"❌ **שגיאה ביצירת קובץ המניה**\n\n"
                f"❗ **שגיאה:** `{str(e)}`\n\n"
                f"🔄 נסה שוב מאוחר יותר"
            )
    
    def format_stock_csv(self, analysis: Dict) -> str:
        """Format stock analysis as CSV"""
        import csv
        import io
        from datetime import datetime
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['# Stock Analysis Export'])
        writer.writerow(['# Symbol:', analysis.get('symbol', 'N/A')])
        writer.writerow(['# Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['# Generated by TelegramBot'])
        writer.writerow([])
        
        # Basic info
        info = analysis.get('basic_info', {})
        writer.writerow(['Basic Information'])
        writer.writerow(['Field', 'Value'])
        writer.writerow(['Company Name', info.get('name', 'N/A')])
        writer.writerow(['Sector', info.get('sector', 'N/A')])
        writer.writerow(['Industry', info.get('industry', 'N/A')])
        writer.writerow(['Market Cap', info.get('market_cap', 'N/A')])
        writer.writerow(['P/E Ratio', info.get('pe_ratio', 'N/A')])
        writer.writerow([])
        
        # Technical indicators
        indicators = analysis.get('technical_indicators', {})
        writer.writerow(['Technical Indicators'])
        writer.writerow(['Indicator', 'Value'])
        writer.writerow(['Current Price', indicators.get('current_price', 'N/A')])
        writer.writerow(['Price Change', indicators.get('price_change', 'N/A')])
        writer.writerow(['Price Change %', indicators.get('price_change_pct', 'N/A')])
        writer.writerow(['RSI', indicators.get('rsi', 'N/A')])
        writer.writerow(['SMA 20', indicators.get('sma_20', 'N/A')])
        writer.writerow(['SMA 50', indicators.get('sma_50', 'N/A')])
        writer.writerow(['MACD', indicators.get('macd', 'N/A')])
        writer.writerow(['Volume Ratio', indicators.get('volume_ratio', 'N/A')])
        writer.writerow(['Support', indicators.get('support', 'N/A')])
        writer.writerow(['Resistance', indicators.get('resistance', 'N/A')])
        writer.writerow([])
        
        # Predictions
        predictions = analysis.get('predictions', {})
        if 'predictions' in predictions:
            writer.writerow(['Price Predictions'])
            writer.writerow(['Day', 'Predicted Price', 'Lower Bound', 'Upper Bound', 'Confidence %'])
            for pred in predictions['predictions']:
                writer.writerow([
                    pred.get('day', ''),
                    pred.get('predicted_price', ''),
                    pred.get('lower_bound', ''),
                    pred.get('upper_bound', ''),
                    pred.get('confidence', '')
                ])
        
        content = output.getvalue()
        output.close()
        return content

    async def send_scan_file(self, query, context, scan_type: str, file_format: str):
        """Send scan results as a downloadable file"""
        import io
        from datetime import datetime
        
        try:
            # Get the stored result based on scan type
            if scan_type == 'port_scan':
                result = getattr(self, 'last_port_scan_result', None)
                scan_name = "Port_Scan"
            elif scan_type == 'range_scan':
                result = getattr(self, 'last_range_scan_result', None)
                scan_name = "Range_Scan"
            elif scan_type == 'ping':
                result = getattr(self, 'last_ping_result', None)
                scan_name = "Ping_Test"
            else:
                await query.edit_message_text("❌ סוג סריקה לא תקין")
                return
            
            if not result:
                await query.edit_message_text("❌ לא נמצאו תוצאות סריקה להורדה. בצע סריקה תחילה.")
                return
            
            # Generate file content based on format
            if file_format == 'csv':
                content = export_scan_results_csv(result, scan_type)
                mime_type = 'text/csv'
                file_ext = 'csv'
            elif file_format == 'json':
                content = export_scan_results_json(result, scan_type)
                mime_type = 'application/json'
                file_ext = 'json'
            elif file_format == 'txt':
                content = export_scan_results_txt(result, scan_type)
                mime_type = 'text/plain'
                file_ext = 'txt'
            else:
                await query.edit_message_text("❌ פורמט קובץ לא תקין")
                return
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"TelegramBot_{scan_name}_{timestamp}.{file_ext}"
            
            # Create BytesIO object for file upload
            file_buffer = io.BytesIO(content.encode('utf-8'))
            file_buffer.name = filename
            
            # Send the file
            await query.edit_message_text("📤 מכין קובץ להורדה...")
            
            # Get chat and user info
            chat_id = query.message.chat_id
            user_name = query.from_user.first_name
            
            # Send file with proper caption
            await context.bot.send_document(
                chat_id=chat_id,
                document=file_buffer,
                filename=filename,
                caption=f"📊 **תוצאות סריקה - {scan_name.replace('_', ' ')}**\n\n"
                       f"📅 **תאריך:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                       f"📁 **פורמט:** {file_format.upper()}\n"
                       f"👤 **הוכן עבור:** {user_name}\n\n"
                       f"💾 **הקובץ מוכן להורדה!**",
                parse_mode='Markdown'
            )
            
            # Update the message to show completion
            await query.edit_message_text(
                f"✅ **קובץ נשלח בהצלחה!**\n\n"
                f"📁 **שם קובץ:** `{filename}`\n"
                f"📊 **פורמט:** {file_format.upper()}\n\n"
                f"💡 **טיפ:** הקובץ זמין להורדה מהשיחה"
            )
            
        except Exception as e:
            logger.error(f"Error sending scan file: {e}")
            await query.edit_message_text(
                f"❌ **שגיאה ביצירת הקובץ**\n\n"
                f"❗ **שגיאה:** `{str(e)}`\n\n"
                f"🔄 נסה שוב מאוחר יותר"
            )

    async def locate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /locate command for IP geolocation"""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        # Check if IP/domain was provided
        if not context.args:
            logger.info(f"📍 /locate (ללא פרמטר) - משתמש: {user_name} (@{username}) | ID: {user_id}")
        else:
            target = ' '.join(context.args)
            logger.info(f"📍 /locate '{target}' - משתמש: {user_name} (@{username}) | ID: {user_id}")
        user_logger.info(f"📍 /locate '{target}' - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        if not context.args:
            await update.message.reply_text(
                "📍 איתור מיקום IP/דומיין\n\n"
                "שימוש: /locate <IP או דומיין>\n\n"
                "דוגמאות:\n"
                "• /locate 8.8.8.8\n"
                "• /locate google.com\n"
                "• /locate 1.1.1.1"
            )
            return
        
        target = ' '.join(context.args)
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            f"🔍 מחפש מיקום עבור: {target}\n"
            f"📡 שולח שאילתות ל-5 מקורות גאוגרפיים...\n"
            f"⏳ זה עלול לקחת 10-15 שניות..."
        )
        
        try:
            # Update progress
            await processing_msg.edit_text(
                f"🔍 מחפש מיקום עבור: {target}\n"
                f"🌐 מבצע חיפוש מקיף ב-API מרובים...\n"
                f"📊 אוסף נתונים מ: ip-api, ipinfo, ipwhois ועוד...\n"
                f"⏳ ממש עוד רגע..."
            )
            
            # Use the comprehensive IP analysis from locate_ip module (disable verbose to avoid Unicode issues)
            result = analyze_single_ip(target, target, verbose=False, fast_mode=True)
            
            if not result or not result.get('geo_results'):
                await processing_msg.edit_text(
                    f"❌ **החיפוש הושלם - לא נמצאו נתונים**\n\n"
                    f"🎯 **יעד:** `{target}`\n"
                    f"🔍 **נבדקו:** 5+ מקורות גאוגרפיים\n"
                    f"📊 **תוצאות:** לא נמצא מידע זמין\n\n"
                    f"💡 **אפשר לנסות:**\n"
                    f"• בדוק שהכתובת IP תקינה\n"
                    f"• נסה עם דומיין במקום IP\n"
                    f"• נסה עם IP ציבורי אחר",
                    parse_mode='Markdown'
                )
                return
            
            # Get the best geo result (usually first one)
            geo_results = result.get('geo_results', [])
            if not geo_results:
                await processing_msg.edit_text(
                    f"❌ לא נמצאו נתונים גאוגרפיים עבור: {target}"
                )
                return
            
            # Find the geo result with most information (prioritize ones with ISP data)
            location_info = geo_results[0]  # Default to first
            for geo in geo_results:
                if geo.get('isp') or geo.get('org'):
                    location_info = geo
                    break
            
            # Build comprehensive response
            response_text = f"📍 **תוצאות איתור עבור:** `{target}`\n\n"
            
            # IP address
            ip_addr = result.get('ip', target)
            response_text += f"🌐 **IP:** `{ip_addr}`\n"
            
            # Country
            if location_info.get('country'):
                country = location_info['country']
                # Try to get country flag (basic mapping)
                flag_map = {
                    'US': '🇺🇸', 'United States': '🇺🇸',
                    'Canada': '🇨🇦', 'CA': '🇨🇦',
                    'UK': '🇬🇧', 'United Kingdom': '🇬🇧',
                    'Germany': '🇩🇪', 'DE': '🇩🇪',
                    'France': '🇫🇷', 'FR': '🇫🇷',
                    'Israel': '🇮🇱', 'IL': '🇮🇱'
                }
                flag = flag_map.get(country, '🏳️')
                response_text += f"🏳️ **מדינה:** {flag} {country}\n"
            
            # Region/State
            region = location_info.get('regionName') or location_info.get('region')
            if region:
                response_text += f"📍 **איזור:** {region}\n"
            
            # City
            if location_info.get('city'):
                response_text += f"🏙️ **עיר:** {location_info['city']}\n"
            
            # Coordinates
            if location_info.get('lat') and location_info.get('lon'):
                lat = location_info['lat']
                lon = location_info['lon']
                response_text += f"🗺️ **קואורדינטות:** {lat}, {lon}\n"
            
            # ISP
            if location_info.get('isp'):
                response_text += f"🏢 **ספק שירות:** {location_info['isp']}\n"
            
            # Organization
            if location_info.get('org'):
                response_text += f"�️ **ארגון:** {location_info['org']}\n"
            
            # Source
            if location_info.get('source'):
                response_text += f"🔍 **מקור:** {location_info['source']}\n"
            
            # Confidence score if available
            confidence = result.get('confidence', {})
            if confidence.get('score'):
                score = confidence['score']
                grade = confidence.get('grade', 'N/A')
                response_text += f"\n📊 **אמינות:** {score}/100 (דרג {grade})\n"
            
            # Add info about sources
            num_sources = len(result.get('geo_results', []))
            response_text += f"🔍 **מקורות:** נבדקו {num_sources} מסדי נתונים\n"
            response_text += f"⚡ **זמן חיפוש:** ~{13 if not result.get('fast_mode') else 8} שניות"
            
            # Add interactive buttons
            keyboard = [
                [InlineKeyboardButton("🔄 איתור IP אחר", callback_data='locate_another')],
                [InlineKeyboardButton("📋 תפריט ראשי", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                response_text,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in locate_ip_command: {e}")
            await processing_msg.edit_text(
                f"❌ **שגיאה בביצוע החיפוש**\n\n"
                f"👤 **משתמש:** {user_name}\n"
                f"🎯 **יעד:** `{target}`\n"
                f"❗ **שגיאה:** `{str(e)}`\n\n"
                f"🔄 **פתרונות אפשריים:**\n"
                f"• נסה שוב עוד כמה שניות\n"
                f"• בדוק חיבור לאינטרנט\n"
                f"• נסה עם IP או דומיין אחר\n"
                f"• פנה למפתח אם הבעיה נמשכת",
                parse_mode='Markdown'
            )

    async def port_scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scan command for port scanning"""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        # Check if target was provided
        if not context.args:
            logger.info(f"🔍 /scan (ללא פרמטר) - משתמש: {user_name} (@{username}) | ID: {user_id}")
            await update.message.reply_text(
                "🔍 **סריקת פורטים**\n\n"
                "שימוש: `/scan <IP או דומיין> [סוג]`\n\n"
                "🔹 **דוגמאות:**\n"
                "• `/scan google.com`\n"
                "• `/scan 192.168.1.1 quick`\n"
                "• `/scan github.com top100`\n\n"
                "🔹 **סוגי סריקה:**\n"
                "• `common` - פורטים נפוצים (ברירת מחדל)\n"
                "• `quick` - פורטים חשובים בלבד\n"
                "• `top100` - 100 הפורטים הנפוצים\n\n"
                "⚠️ **לשימוש חוקי בלבד!**",
                parse_mode='Markdown'
            )
            return
        
        target = context.args[0]
        scan_type = context.args[1] if len(context.args) > 1 else "common"
        
        logger.info(f"🔍 /scan '{target}' ({scan_type}) - משתמש: {user_name} (@{username}) | ID: {user_id}")
        user_logger.info(f"🔍 /scan '{target}' ({scan_type}) - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        # Get ports count for progress indication
        ports = self.network_tools.get_port_ranges(scan_type)
        ports_count = len(ports)
        
        # Estimate time based on scan type
        time_estimates = {
            "quick": "3-5 שניות",
            "common": "5-8 שניות", 
            "top100": "15-30 שניות",
            "web": "3-5 שניות",
            "full": "5-15 דקות ⚠️"
        }
        estimated_time = time_estimates.get(scan_type, "מספר שניות")
        
        # Show processing message with better UX
        processing_msg = await update.message.reply_text(
            f"🔍 **סורק פורטים עבור:** `{target}`\n\n"
            f"📊 **סוג סריקה:** {scan_type.upper()}\n"
            f"🎯 **פורטים לסריקה:** {ports_count:,}\n"
            f"⏱️ **זמן משוער:** {estimated_time}\n\n"
            f"⏳ מתחיל סריקה... אנא המתן",
            parse_mode='Markdown'
        )
        
        try:
            
            # Perform the scan
            result = await self.network_tools.scan_ports_async(target, ports)
            
            # Format results
            result_text = format_port_scan_result(result)
            
            # Store scan result for download
            self.last_port_scan_result = result
            
            # Create inline keyboard for additional options
            keyboard = [
                [InlineKeyboardButton("💾 הורד תוצאות CSV", callback_data='download_port_csv'),
                 InlineKeyboardButton("📄 הורד כ-JSON", callback_data='download_port_json')],
                [InlineKeyboardButton("📝 הורד כ-TXT", callback_data='download_port_txt')],
                [InlineKeyboardButton("🔄 סרוק מחדש", callback_data='scan_another')],
                [InlineKeyboardButton("🏓 Ping Test", callback_data='ping_demo')],
                [InlineKeyboardButton("📍 איתור IP", callback_data='locate_demo')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in port_scan_command: {e}")
            await processing_msg.edit_text(
                f"❌ מצטער {user_name}, אירעה שגיאה בסריקת {target}\n\n"
                f"🔄 נסה שוב מאוחר יותר או עם target אחר.\n\n"
                f"📝 וודא שהפורמט נכון:\n"
                f"`/scan {target} [common/quick/top100]`",
                parse_mode='Markdown'
            )

    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ping command for ping tests"""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        # Check if target was provided
        if not context.args:
            logger.info(f"🏓 /ping (ללא פרמטר) - משתמש: {user_name} (@{username}) | ID: {user_id}")
            await update.message.reply_text(
                "🏓 **Ping Test**\n\n"
                "בדיקת זמינות שרת:\n"
                "`/ping <IP או דומיין>`\n\n"
                "🔹 **דוגמאות:**\n"
                "• `/ping google.com`\n"
                "• `/ping 8.8.8.8`\n"
                "• `/ping github.com`\n\n"
                "הבוט יבדוק אם השרת זמין ויציג זמן תגובה.",
                parse_mode='Markdown'
            )
            return
        
        target = context.args[0]
        
        logger.info(f"🏓 /ping '{target}' - משתמש: {user_name} (@{username}) | ID: {user_id}")
        user_logger.info(f"🏓 /ping '{target}' - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            f"🏓 בודק זמינות עבור: {target}\n"
            f"⏳ אנא המתן..."
        )
        
        try:
            # Perform ping test
            result = await self.network_tools.ping_host(target)
            
            # Format results
            result_text = format_ping_result(result)
            
            # Store ping result for download
            self.last_ping_result = result
            
            # Create inline keyboard for additional options
            keyboard = [
                [InlineKeyboardButton("💾 הורד תוצאות CSV", callback_data='download_ping_csv'),
                 InlineKeyboardButton("📄 הורד כ-JSON", callback_data='download_ping_json')],
                [InlineKeyboardButton("📝 הורד כ-TXT", callback_data='download_ping_txt')],
                [InlineKeyboardButton("🔄 Ping מחדש", callback_data='ping_another')],
                [InlineKeyboardButton("🔍 סריקת פורטים", callback_data='scan_demo')],
                [InlineKeyboardButton("📍 איתור IP", callback_data='locate_demo')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in ping_command: {e}")
            await processing_msg.edit_text(
                f"❌ מצטער {user_name}, אירעה שגיאה ב-ping ל-{target}\n\n"
                f"🔄 נסה שוב מאוחר יותר או עם target אחר.\n\n"
                f"📝 וודא שהפורמט נכון:\n"
                f"`/ping {target}`",
                parse_mode='Markdown'
            )

    async def range_scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rangescan command for IP range scanning"""
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
                "🚀 **דוגמה לVNC:**\n"
                "`/rangescan 213.0.0.0-213.255.255.255 5900`\n\n"
                "⚠️ **הערה:** טווחים גדולים יכולים לקחת זמן רב!\n"
                "💡 **טיפ:** התחל עם טווח קטן כמו /24",
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
        user_logger.info(f"🎯 /rangescan '{ip_range}' פורט {port} - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        # Parse range to estimate size
        try:
            test_ips = self.range_scanner.parse_ip_range(ip_range)
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
            
            # Show warning for large scans
            if estimated_count > 10000:
                # Store scan parameters temporarily (simple approach)
                self.pending_scan = {'range': ip_range, 'port': port}
                
                keyboard = [
                    [InlineKeyboardButton("⚠️ המשך בכל זאת", callback_data='confirm_large_scan')],
                    [InlineKeyboardButton("🔙 ביטול", callback_data='range_scan_demo')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"⚠️ **אזהרה: סריקה גדולה**\n\n"
                    f"📊 **טווח:** `{ip_range}`\n"
                    f"🎯 **פורט:** `{port}`\n"
                    f"📈 **מוערך:** ~`{estimated_count:,}` IPs\n"
                    f"⏱️ **זמן משוער:** {time_est}\n\n"
                    f"🚨 **זה יכול להעמיס על הרשת!**\n"
                    f"🛡️ **השתמש רק ברשתות מורשות**\n\n"
                    f"האם להמשיך?",
                    reply_markup=reply_markup,
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
            f"🚀 **מכין {self.range_scanner.max_workers} threads...**\n"
            f"⏳ **התחלת סריקה...**",
            parse_mode='Markdown'
        )
        
        # Progress callback function
        async def progress_callback(scanned, total, found):
            progress_percent = (scanned / total) * 100
            bar_length = 20
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
        
        try:
            # Perform the range scan
            result = await self.range_scanner.scan_range_async(
                ip_range, port, progress_callback
            )
            
            # Format results
            result_text = format_range_scan_result(result)
            
            # Store scan result for download
            self.last_range_scan_result = result
            
            # Create inline keyboard for additional options
            keyboard = [
                [InlineKeyboardButton("💾 הורד תוצאות CSV", callback_data='download_range_csv'),
                 InlineKeyboardButton("📄 הורד כ-JSON", callback_data='download_range_json')],
                [InlineKeyboardButton("📝 הורד כ-TXT", callback_data='download_range_txt')],
                [InlineKeyboardButton("🔄 סרוק טווח אחר", callback_data='range_scan_demo')],
                [InlineKeyboardButton("🔍 סריקת פורטים רגילה", callback_data='scan_demo')],
                [InlineKeyboardButton("📍 איתור IP", callback_data='locate_demo')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in range_scan_command: {e}")
            await processing_msg.edit_text(
                f"❌ מצטער {user_name}, אירעה שגיאה בסריקת הטווח\n\n"
                f"🔍 **טווח:** `{ip_range}`\n"
                f"🎯 **פורט:** `{port}`\n"
                f"❗ **שגיאה:** `{str(e)}`\n\n"
                f"💡 **טיפים:**\n"
                f"• בדוק שהטווח תקין\n"
                f"• נסה טווח קטן יותר\n"
                f"• ודא שהפורט בין 1-65535",
                parse_mode='Markdown'
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user_message = update.message.text
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        logger.info(f"💬 הודעה: '{user_message}' - משתמש: {user_name} (@{username}) | ID: {user_id}")
        user_logger.info(f"💬 הודעה: '{user_message}' - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        # Simple auto-responses
        if "שלום" in user_message or "היי" in user_message:
            await update.message.reply_text(f"שלום {user_name}! איך אני יכול לעזור לך היום? 😊")
        elif "תודה" in user_message:
            await update.message.reply_text("בשמחה! אני כאן כדי לעזור 🤗")
        elif "מה שלומך" in user_message:
            await update.message.reply_text("אני בוט אז אני תמיד בסדר! 🤖 איך אתה?")
        else:
            await update.message.reply_text(
                f"היי {user_name}! 👋\n\n"
                f"אני מבין שאתה רוצה לשאול משהו.\n"
                f"נסה להשתמש בפקודות שלי:\n\n"
                f"📍 /locate <IP או דומיין> - לאיתור מיקום\n"
                f"📋 /help - לרשימת פקודות מלאה\n"
                f"🎯 /menu - לתפריט אינטראקטיבי"
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.warning(f'Update {update} caused error {context.error}')

    def run(self):
        """Start the bot"""
        logger.info("🤖 Starting Telegram Bot...")
        logger.info("📊 Bot is ready to receive messages!")
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        # Start polling
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stock command for stock analysis"""
        if not STOCK_ANALYSIS_AVAILABLE:
            await update.message.reply_text(
                "❌ Stock analysis is not available. Missing required packages:\n"
                "• yfinance\n• pandas\n• numpy\n• scikit-learn"
            )
            return
        
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        if not context.args:
            logger.info(f"📈 /stock (ללא פרמטר) - משתמש: {user_name} (@{username}) | ID: {user_id}")
            await update.message.reply_text(
                "📈 **ניתוח מניות מתקדם**\n\n"
                "שימוש: `/stock <סמל מניה>`\n\n"
                "🔹 **דוגמאות:**\n"
                "• `/stock AAPL` - אפל\n"
                "• `/stock MSFT` - מיקרוסופט\n"
                "• `/stock GOOGL` - גוגל\n"
                "• `/stock TSLA` - טסלה\n"
                "• `/stock NVDA` - נבידיה\n\n"
                "📊 **מה תקבל:**\n"
                "• מחוונים טכניים מתקדמים\n"
                "• סיגנלים לקנייה/מכירה\n"
                "• תחזיות מחיר באמצעות AI\n"
                "• רמות תמיכה והתנגדות\n"
                "• ניתוח נפח וטרנדים",
                parse_mode='Markdown'
            )
            return
        
        symbol = context.args[0].upper()
        logger.info(f"📈 /stock '{symbol}' - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            f"📈 מנתח מניה: {symbol}\n"
            f"📊 אוסף נתונים מ-Yahoo Finance...\n"
            f"🤖 מבצע ניתוח טכני ו-AI...\n"
            f"⏳ זה עלול לקחת 10-15 שניות..."
        )
        
        try:
            # Perform stock analysis
            analysis = await stock_analyzer.analyze_stock(symbol)
            
            # Format results
            result_text = format_stock_analysis(analysis)
            
            # Store analysis for download
            self.last_stock_analysis = analysis
            
            # Create interactive keyboard
            keyboard = [
                [InlineKeyboardButton("💾 הורד ניתוח CSV", callback_data='download_stock_csv'),
                 InlineKeyboardButton("📄 הורד כ-JSON", callback_data='download_stock_json')],
                [InlineKeyboardButton("🔮 תחזיות מפורטות", callback_data=f'stock_predict_{symbol}')],
                [InlineKeyboardButton("📊 ניתוח מניה אחרת", callback_data='stock_demo')],
                [InlineKeyboardButton("📋 תפריט ראשי", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in stock_command: {e}")
            await processing_msg.edit_text(
                f"❌ **שגיאה בניתוח המניה**\n\n"
                f"📈 **סמל:** {symbol}\n"
                f"❗ **שגיאה:** `{str(e)}`\n\n"
                f"💡 **טיפים:**\n"
                f"• בדוק שהסמל תקין (AAPL, MSFT וכו')\n"
                f"• נסה עם סמל אחר\n"
                f"• נסה שוב מאוחר יותר\n"
                f"• וודא שיש חיבור לאינטרנט",
                parse_mode='Markdown'
            )

    async def predict_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /predict command for detailed stock predictions"""
        if not STOCK_ANALYSIS_AVAILABLE:
            await update.message.reply_text(
                "❌ Stock prediction is not available. Missing required packages."
            )
            return
        
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        if not context.args:
            await update.message.reply_text(
                "🔮 **חיזוי מחירי מניות**\n\n"
                "שימוש: `/predict <סמל> [ימים]`\n\n"
                "🔹 **דוגמאות:**\n"
                "• `/predict AAPL` - חיזוי ל-5 ימים\n"
                "• `/predict TSLA 10` - חיזוי ל-10 ימים\n"
                "• `/predict NVDA 3` - חיזוי ל-3 ימים\n\n"
                "🤖 **שימושים AI מתקדם:**\n"
                "• Random Forest Machine Learning\n"
                "• ניתוח מחוונים טכניים\n"
                "• חיזוי בטווח ביטחון\n"
                "• הערכת דיוק המודל",
                parse_mode='Markdown'
            )
            return
        
        symbol = context.args[0].upper()
        days = int(context.args[1]) if len(context.args) > 1 else 5
        days = min(max(days, 1), 30)  # Limit to 1-30 days
        
        logger.info(f"🔮 /predict '{symbol}' {days} days - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        processing_msg = await update.message.reply_text(
            f"🔮 מחשב חיזוי עבור {symbol}\n"
            f"📅 תחזית ל-{days} ימים\n"
            f"🤖 מפעיל מודלי AI...\n"
            f"⏳ אנא המתן..."
        )
        
        try:
            # Get detailed analysis with predictions
            analysis = await stock_analyzer.analyze_stock(symbol, days)
            
            if 'error' in analysis:
                await processing_msg.edit_text(
                    f"❌ שגיאה בחיזוי: {analysis['error']}"
                )
                return
            
            predictions = analysis.get('predictions', {})
            if 'error' in predictions:
                await processing_msg.edit_text(
                    f"❌ שגיאה בחיזוי: {predictions['error']}"
                )
                return
            
            # Format detailed predictions
            response = f"🔮 **חיזוי מחירים - {symbol}**\n\n"
            
            # Model info
            method = predictions.get('method', 'Unknown')
            accuracy = predictions.get('model_accuracy')
            response += f"🤖 **Method:** {method}\n"
            if accuracy:
                response += f"📊 **Model Accuracy:** {accuracy}%\n"
            
            # Current price from indicators
            indicators = analysis.get('technical_indicators', {})
            if 'current_price' in indicators:
                response += f"💰 **Current Price:** ${indicators['current_price']}\n"
            
            response += f"\n📅 **תחזיות ל-{days} ימים:**\n\n"
            
            # Detailed predictions
            if 'predictions' in predictions:
                for pred in predictions['predictions']:
                    day = pred['day']
                    price = pred['predicted_price']
                    conf = pred['confidence']
                    lower = pred.get('lower_bound', price)
                    upper = pred.get('upper_bound', price)
                    
                    trend = "📈" if price > indicators.get('current_price', price) else "📉"
                    
                    response += f"**Day {day}:** {trend} ${price}\n"
                    response += f"   Range: ${lower} - ${upper}\n"
                    response += f"   Confidence: {conf}%\n\n"
            
            # Add trend info
            if 'trend' in predictions:
                trend = predictions['trend']
                trend_emoji = "📈" if trend == 'UP' else "📉" if trend == 'DOWN' else "➡️"
                response += f"{trend_emoji} **Overall Trend:** {trend}\n"
            
            if 'volatility' in predictions:
                response += f"📊 **Volatility:** ${predictions['volatility']}\n"
            
            response += f"\n⚠️ **Disclaimer:** חיזויים למטרות חינוכיות בלבד"
            
            # Interactive keyboard
            keyboard = [
                [InlineKeyboardButton("📈 ניתוח מלא", callback_data=f'stock_full_{symbol}')],
                [InlineKeyboardButton("🔄 חזור על החיזוי", callback_data=f'predict_again_{symbol}')],
                [InlineKeyboardButton("📊 מניה אחרת", callback_data='stock_demo')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                response,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in predict_command: {e}")
            await processing_msg.edit_text(
                f"❌ **שגיאה בחיזוי**\n\n"
                f"📈 **סמל:** {symbol}\n"
                f"📅 **ימים:** {days}\n"
                f"❗ **שגיאה:** `{str(e)}`",
                parse_mode='Markdown'
            )
    
    # ============== Crypto Alerts Commands ==============
    
    async def _send_crypto_alert(self, user_id: str, message: str):
        """Callback function to send crypto alerts"""
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending crypto alert to {user_id}: {e}")
    
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
            
            data = self.crypto_manager.taapi.get_indicator(pair, indicator, timeframe, params)
            
            message = f"📊 **{indicator} - {pair}**\n"
            message += f"⏰ Timeframe: {timeframe}\n\n"
            
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    message += f"**{key}:** {value:.4f}\n"
                else:
                    message += f"**{key}:** {value}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        
        except Exception as e:
            await update.message.reply_text(f"❌ שגיאה: {str(e)}")
    
    async def indicators_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all available indicators"""
        if not CRYPTO_ALERTS_AVAILABLE:
            await update.message.reply_text("❌ Crypto alerts not available")
            return
        
        indicators_list = get_indicators_list()
        await update.message.reply_text(indicators_list, parse_mode='Markdown')
    
    # ========================
    # 10bis Commands
    # ========================
    
    async def tenbis_login_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tenbis_login command"""
        if not TENBIS_AVAILABLE:
            await update.message.reply_text("❌ 10bis module not available")
            return
        
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        logger.info(f"🍔 /tenbis_login - משתמש: {user_name} | ID: {user_id}")
        
        # Initialize handler for user if not exists
        if user_id not in self.tenbis_handlers:
            self.tenbis_handlers[user_id] = TenbisHandler(user_id)
        
        handler = self.tenbis_handlers[user_id]
        
        # Check if already authenticated
        if handler.load_session():
            await update.message.reply_text(
                "✅ כבר מחובר!\n\n"
                "השתמש ב-/tenbis_vouchers כדי לראות את השוברים שלך.\n"
                "או /tenbis_logout כדי להתנתק."
            )
            return
        
        # Check if we have email from args
        if not context.args:
            await update.message.reply_text(
                "📧 **התחברות ל-10Bis**\n\n"
                "שלח את האימייל שלך:\n"
                "/tenbis_login your@email.com"
            )
            return
        
        email = context.args[0]
        
        # Send OTP
        success, message = await handler.authenticate(email)
        
        if success:
            # Save state - waiting for OTP
            self.tenbis_auth_states[user_id] = {
                'handler': handler,
                'waiting_for_otp': True
            }
        
        await update.message.reply_text(message)
    
    async def tenbis_vouchers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tenbis_vouchers command"""
        if not TENBIS_AVAILABLE:
            await update.message.reply_text("❌ 10bis module not available")
            return
        
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        logger.info(f"🎫 /tenbis_vouchers - משתמש: {user_name} | ID: {user_id}")
        
        # Check if handler exists
        if user_id not in self.tenbis_handlers:
            self.tenbis_handlers[user_id] = TenbisHandler(user_id)
        
        handler = self.tenbis_handlers[user_id]
        
        # Check if user is logged in
        if not handler.load_session():
            await update.message.reply_text(
                "❌ אין אימות פעיל\n\n"
                "תחילה השתמש ב-/tenbis_login כדי להתחבר."
            )
            return
        
        # Get months back (default 12)
        months_back = 12
        if context.args:
            try:
                months_back = int(context.args[0])
            except ValueError:
                pass
        
        await update.message.reply_text("🔍 מחפש שוברים פעילים... אנא המתן...")
        
        try:
            success, message, vouchers = handler.get_vouchers(months_back)
        except Exception as e:
            await update.message.reply_text(f"❌ שגיאה בחיבור: {str(e)}")
            return
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
        if vouchers:
            # Send vouchers in batches (5 per message to avoid flooding)
            batch_size = 5
            for i in range(0, len(vouchers), batch_size):
                batch = vouchers[i:i + batch_size]
                batch_message = ""
                for idx, voucher in enumerate(batch, start=i+1):
                    batch_message += format_voucher_message(voucher, idx)
                
                await update.message.reply_text(batch_message, parse_mode='Markdown')
                
                # Send barcode images
                for voucher in batch:
                    try:
                        await update.message.reply_photo(
                            photo=voucher['barcode_img_url'],
                            caption=f"🎫 ברקוד #{i+batch.index(voucher)+1}: {voucher['barcode_number']}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send barcode image: {e}")
    
    async def tenbis_logout_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tenbis_logout command"""
        if not TENBIS_AVAILABLE:
            await update.message.reply_text("❌ 10bis module not available")
            return
        
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        logger.info(f"👋 /tenbis_logout - משתמש: {user_name} | ID: {user_id}")
        
        if user_id in self.tenbis_handlers:
            self.tenbis_handlers[user_id].clear_session()
            del self.tenbis_handlers[user_id]
        
        if user_id in self.tenbis_auth_states:
            del self.tenbis_auth_states[user_id]
        
        await update.message.reply_text("✅ התנתקת בהצלחה מ-10Bis!")
    
    async def tenbis_html_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tenbis_html command - Generate and send HTML report"""
        from datetime import date
        
        if not TENBIS_AVAILABLE:
            await update.message.reply_text("❌ 10bis module not available")
            return
        
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        logger.info(f"📄 /tenbis_html - משתמש: {user_name} | ID: {user_id}")
        
        # Check if handler exists
        if user_id not in self.tenbis_handlers:
            self.tenbis_handlers[user_id] = TenbisHandler(user_id)
        
        handler = self.tenbis_handlers[user_id]
        
        # Check if user is logged in
        if not handler.load_session():
            await update.message.reply_text(
                "❌ אין אימות פעיל\n\n"
                "תחילה השתמש ב-/tenbis_login כדי להתחבר."
            )
            return
        
        # Get months back (default 12)
        months_back = 12
        if context.args:
            try:
                months_back = int(context.args[0])
            except ValueError:
                pass
        
        # Show status: Connecting (0%)
        status_msg = await update.message.reply_text("🔄 [0%] מתחבר ל-10Bis...")
        
        try:
            success, message, vouchers = handler.get_vouchers(months_back)
        except Exception as e:
            await status_msg.edit_text(f"❌ שגיאה בחיבור: {str(e)}")
            return
        
        if not success or not vouchers:
            await status_msg.edit_text(f"❌ {message}")
            return
        
        # Show status: Found vouchers (25%)
        await status_msg.edit_text(
            f"✅ [25%] נמצאו {len(vouchers)} שוברים!\n\n"
            f"📝 יוצר קובץ HTML..."
        )
        
        try:
            # Generate HTML content (50%)
            await status_msg.edit_text(
                f"✅ נמצאו {len(vouchers)} שוברים!\n\n"
                f"📝 [50%] בונה גלריית ברקודים..."
            )
            html_content = generate_html_report(vouchers, user_name)
            
            # Show status: HTML created (70%)
            await status_msg.edit_text(
                f"✅ נמצאו {len(vouchers)} שוברים!\n"
                f"✅ קובץ HTML נוצר!\n\n"
                f"📦 [70%] מכין להורדה..."
            )
            
            # Create file in memory (85%)
            from io import BytesIO
            html_bytes = BytesIO(html_content.encode('utf-8'))
            html_bytes.name = f"10bis_vouchers_{date.today().strftime('%d-%b-%Y')}.html"
            
            # Show status: Uploading (90%)
            await status_msg.edit_text(
                f"✅ נמצאו {len(vouchers)} שוברים!\n"
                f"✅ קובץ HTML נוצר!\n\n"
                f"⬆️ [90%] מעלה קובץ..."
            )
            
            # Send file
            total_amount = sum(float(v['amount']) for v in vouchers)
            today_str = date.today().strftime('%d/%m/%Y')
            await update.message.reply_document(
                document=html_bytes,
                filename=html_bytes.name,
                caption=f"🎫 דוח שוברי 10Bis\n\n"
                       f"📊 סה\"כ שוברים: {len(vouchers)}\n"
                       f"💰 סה\"כ סכום: {total_amount} ₪\n"
                       f"📅 תאריך: {today_str}\n"
                       f"👤 עבור: {user_name}\n\n"
                       f"📱 פתח בדפדפן לצפייה אינטראקטיבית!\n"
                       f"🖼️ גלריית ברקודים\n"
                       f"📸 לחיצה על ברקוד לסריקה מהירה\n"
                       f"⌨️ ניווט עם חצים במקלדת"
            )
            
            # Update final status (100%)
            await status_msg.edit_text(
                f"✅ [100%] הקובץ נשלח בהצלחה!\n\n"
                f"📄 שם קובץ: {html_bytes.name}\n"
                f"📊 {len(vouchers)} שוברים פעילים\n"
                f"💰 סה\"כ: {total_amount} ₪\n\n"
                f"💡 טיפ: הורד את הקובץ ופתח בדפדפן!"
            )
            
        except Exception as e:
            logger.error(f"Error generating HTML: {e}")
            await status_msg.edit_text(
                f"❌ שגיאה ביצירת קובץ HTML\n\n"
                f"❗ שגיאה: {str(e)}\n\n"
                f"🔄 נסה שוב מאוחר יותר"
            )
    
    async def finance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /finance command - show Israeli finance index"""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        logger.info(f"💹 /finance - משתמש: {user_name} (@{username}) | ID: {user_id}")
        user_logger.info(f"💹 /finance - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        # Show loading message
        status_msg = await update.message.reply_text("⏳ טוען נתוני מדד...")
        
        try:
            # Get index report
            report = format_index_report()
            
            # Send report
            await status_msg.edit_text(report, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in finance_command: {e}")
            await status_msg.edit_text(
                f"❌ **שגיאה בטעינת נתונים**\n\n"
                f"לא ניתן לטעון את נתוני המדד כרגע.\n"
                f"אנא נסה שוב מאוחר יותר."
            )
    
    async def finance_stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /financestock command - show specific stock info"""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"
        
        # Check if symbol provided
        if not context.args:
            await update.message.reply_text(
                "❌ **חסר סמל מניה**\n\n"
                "**שימוש:**\n"
                "`/financestock <סמל מניה>`\n\n"
                "**דוגמאות:**\n"
                "• `/financestock PHOE.TA`\n"
                "• `/financestock LUMI.TA`\n"
                "• `/financestock POLI.TA`",
                parse_mode='Markdown'
            )
            return
        
        symbol = context.args[0].upper()
        
        logger.info(f"🔍 /financestock {symbol} - משתמש: {user_name} (@{username}) | ID: {user_id}")
        user_logger.info(f"🔍 /financestock {symbol} - משתמש: {user_name} (@{username}) | ID: {user_id}")
        
        # Show loading message
        status_msg = await update.message.reply_text(f"⏳ בודק מניה {symbol}...")
        
        try:
            # Get stock info
            report = get_stock_info(symbol)
            
            # Send report
            await status_msg.edit_text(report, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in finance_stock_command: {e}")
            await status_msg.edit_text(
                f"❌ **שגיאה בטעינת נתונים**\n\n"
                f"לא ניתן לטעון מידע עבור {symbol}.\n"
                f"וודא שהסמל נכון ונסה שוב."
            )
    
    async def ta125_scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ta125scan command - scan TA-125 for stocks negative 3 days in a row"""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        username = update.effective_user.username or "ללא שם משתמש"

        logger.info(f"📊 /ta125scan - משתמש: {user_name} (@{username}) | ID: {user_id}")
        user_logger.info(f"📊 /ta125scan - משתמש: {user_name} (@{username}) | ID: {user_id}")

        status_msg = await update.message.reply_text(
            "⏳ **סורק מדד תא-125...**\n\n"
            "מוריד נתונים עבור ~125 מניות ובודק 3 ימי מסחר אחרונים.\n"
            "הסריקה עשויה לקחת כ-30-60 שניות, אנא המתן...",
            parse_mode='Markdown'
        )

        try:
            negative_stocks, total_scanned, failed_count = await scan_ta125_async()
            report = format_ta125_report(negative_stocks, total_scanned, failed_count)
            await status_msg.edit_text(report, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f"Error in ta125_scan_command: {e}")
            await status_msg.edit_text(
                "❌ **שגיאה בסריקת תא-125**\n\n"
                f"פרטים: `{str(e)}`\n\n"
                "אנא נסה שוב מאוחר יותר.",
                parse_mode='Markdown'
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Check if waiting for 10bis OTP
        if user_id in self.tenbis_auth_states and self.tenbis_auth_states[user_id].get('waiting_for_otp'):
            handler = self.tenbis_auth_states[user_id]['handler']
            
            # Verify OTP
            success, message = await handler.authenticate(email=None, otp=message_text.strip())
            
            if success:
                # Clear auth state
                self.tenbis_auth_states[user_id]['waiting_for_otp'] = False
            
            await update.message.reply_text(message)
            return
        
        # Original message handling
        await update.message.reply_text(
            "אני לא בטוח איך לענות על זה 🤔\n"
            "נסה להשתמש ב-/help או /menu לראות מה אני יכול לעשות!"
        )


def main():
    """Main function to run the bot"""
    try:
        # Start health check server in background thread
        health_server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
        health_thread = threading.Thread(target=health_server.serve_forever)
        health_thread.daemon = True
        health_thread.start()
        logger.info("Health check server started on port 8080")
        
        # Get bot token from environment
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not found")
        
        # Create and run bot
        bot = TelegramBot(bot_token)
        logger.info("Bot initialized successfully")
        
        # Start crypto alerts monitoring if available
        if CRYPTO_ALERTS_AVAILABLE and bot.crypto_manager:
            bot.crypto_manager.start_monitoring(bot._send_crypto_alert)
            logger.info("Crypto alerts monitoring started")
        
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"ERROR: {e}")
        print("Please check your environment variables")
    except Exception as e:
        logger.error(f"Unexpected bot error: {e}")
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()