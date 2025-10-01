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

# Import IP location functions
from locate_ip import analyze_single_ip, geoip_ipapi, geoip_ipinfo

# Import network tools
from network_tools import (NetworkTools, format_port_scan_result, format_ping_result, 
                          IPRangeScanner, format_range_scan_result,
                          export_scan_results_csv, export_scan_results_json, export_scan_results_txt)

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

🔹 **דוגמאות:**
/locate 8.8.8.8
/scan google.com
/scan 192.168.1.1 quick
/ping github.com
/rangescan 213.0.0.0-213.0.0.255 5900
/rangescan 192.168.1.0/24 22

🔹 **סוגי סריקה:**
• quick - 13 פורטים חשובים (מהיר)
• common - 19 פורטים נפוצים (ברירת מחדל)
• top100 - 100 הפורטים הנפוצים ביותר
• web - פורטי שירותי אינטרנט
• full - כל הפורטים 1-65535 (איטי מאוד!)

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
            [InlineKeyboardButton("� דוגמאות מהירות", callback_data='quick_examples')],
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
                [InlineKeyboardButton("📊 דוגמאות מהירות", callback_data='quick_examples')],
                [InlineKeyboardButton("❓ עזרה ומידע", callback_data='help_info')],
                [InlineKeyboardButton("📞 יצירת קשר", callback_data='contact')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎯 **תפריט ראשי**\n\n"
                "בחר אפשרות:",
                reply_markup=reply_markup
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
        
        else:
            await query.edit_message_text("🤖 אפשרות לא מזוהה")

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
        elif query.data == 'range_scan_demo':
            await query.edit_message_text(
                "🎯 **סריקת טווח IP מתקדמת**\n\n"
                "סרוק אלפי IP במהירות הבזק!\n"
                "`/rangescan <טווח> <פורט>`\n\n"
                "🔹 **פורמטים נתמכים:**\n"
                "• **CIDR:** `/rangescan 192.168.1.0/24 22`\n"
                "• **טווח:** `/rangescan 213.0.0.0-213.0.0.255 5900`\n"
                "• **IP יחיד:** `/rangescan 8.8.8.8 80`\n\n"
                "🚀 **פורטים פופולריים:**\n"
                "• `5900` - VNC Server\n"
                "• `22` - SSH\n"
                "• `3389` - RDP\n"
                "• `23` - Telnet\n\n"
                "⚡ **ביצועים:** עד 1000+ IP/שנייה!\n"
                "⚠️ **זהירות:** טווחים גדולים לוקחים זמן!",
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
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise

if __name__ == "__main__":
    main()