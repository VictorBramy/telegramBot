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
from network_tools import NetworkTools, format_port_scan_result, format_ping_result

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
שלום {user_name}! 👋

ברוכים הבאים לבוט הטלגרם החכם! 🤖

🔍 אני יכול לעזור לך עם:
• איתור מיקום IP (טווחי רשת, חברות, מדינות)
• ניתוח כתובות דומיין ומיפוי תשתיות

📋 פקודות מהירות:
/help - רשימת פקודות מלאה
/menu - תפריט אינטראקטיבי נוח
/locate <IP/דומיין> - חיפוש מיקום גאוגרפי

✨ נסה עכשיו: /locate 8.8.8.8
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

🔹 **דוגמאות:**
/locate 8.8.8.8
/scan google.com
/scan 192.168.1.1 quick
/ping github.com

🔹 **סוגי סריקה:**
• common - פורטים נפוצים (ברירת מחדל)
• quick - פורטים חשובים בלבד
• top100 - 100 הפורטים הנפוצים ביותר

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
            [InlineKeyboardButton("ℹ️ מידע", callback_data='info')],
            [InlineKeyboardButton("📍 איתור IP", callback_data='locate_demo')],
            [InlineKeyboardButton("🔍 סריקת פורטים", callback_data='scan_demo')],
            [InlineKeyboardButton("🏓 Ping Test", callback_data='ping_demo')],
            [InlineKeyboardButton("⚙️ הגדרות", callback_data='settings')],
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

        if query.data == 'info':
            await query.edit_message_text("ℹ️ זהו בוט טלגרם פשוט וחכם שנבנה בפייתון!")
        elif query.data == 'settings':
            await query.edit_message_text("⚙️ כאן תוכל לשנות הגדרות (בפיתוח)")
        elif query.data == 'locate_demo':
            await query.edit_message_text("📍 איתור IP - השתמש בפקודה:\n\n/locate 8.8.8.8\n/locate google.com\n\nהבוט יחפש את המיקום הגאוגרפי של ה-IP!")
        elif query.data == 'scan_demo':
            await query.edit_message_text(
                "🔍 **סריקת פורטים**\n\n"
                "השתמש בפקודה:\n"
                "`/scan <IP או דומיין> [סוג]`\n\n"
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
        elif query.data == 'ping_demo':
            await query.edit_message_text(
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
        else:
            await query.edit_message_text("🤖 אפשרות לא מזוהה")

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
            f"📡 טוען מידע גאוגרפי...\n"
            f"⏳ אנא המתן..."
        )
        
        try:
            # Use the comprehensive IP analysis from locate_ip module
            result = analyze_single_ip(target)
            
            if not result or not result.get('success', False):
                await processing_msg.edit_text(
                    f"❌ לא הצלחתי למצוא מידע עבור: {target}\n"
                    f"נסה עם IP או דומיין אחר."
                )
                return
            
            # Format the detailed results
            location_info = result.get('data', {})
            
            # Build comprehensive response
            response_text = f"📍 **תוצאות איתור עבור:** `{target}`\n\n"
            
            if location_info.get('ip'):
                response_text += f"🌐 **IP:** `{location_info['ip']}`\n"
            
            if location_info.get('country'):
                flag = location_info.get('country_flag', '🏳️')
                response_text += f"🏳️ **מדינה:** {flag} {location_info['country']}\n"
            
            if location_info.get('region'):
                response_text += f"📍 **איזור:** {location_info['region']}\n"
            
            if location_info.get('city'):
                response_text += f"🏙️ **עיר:** {location_info['city']}\n"
            
            if location_info.get('latitude') and location_info.get('longitude'):
                lat = location_info['latitude']
                lon = location_info['longitude']
                response_text += f"🗺️ **קואורדינטות:** {lat}, {lon}\n"
            
            if location_info.get('timezone'):
                response_text += f"⏰ **איזור זמן:** {location_info['timezone']}\n"
            
            if location_info.get('isp'):
                response_text += f"🏢 **ספק שירות:** {location_info['isp']}\n"
            
            if location_info.get('org'):
                response_text += f"🏛️ **ארגון:** {location_info['org']}\n"
            
            # Add interactive buttons
            keyboard = [
                [InlineKeyboardButton("🔄 איתור IP אחר", callback_data='locate_another')],
                [InlineKeyboardButton("📋 תפריט ראשי", callback_data='info')]
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
                f"❌ מצטער {user_name}, אירעה שגיאה בחיפוש המיקום של {target}\n"
                f"נסה שוב מאוחר יותר או עם IP/דומיין אחר."
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
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            f"🔍 סורק פורטים עבור: {target}\n"
            f"📊 סוג סריקה: {scan_type}\n"
            f"⏳ אנא המתן... זה יכול לקחת מספר שניות"
        )
        
        try:
            # Get ports to scan based on type
            ports = self.network_tools.get_port_ranges(scan_type)
            
            # Perform the scan
            result = await self.network_tools.scan_ports_async(target, ports)
            
            # Format results
            result_text = format_port_scan_result(result)
            
            # Create inline keyboard for additional options
            keyboard = [
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
            
            # Create inline keyboard for additional options
            keyboard = [
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