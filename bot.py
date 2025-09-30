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

# Import phone checker functions  
from phone_checker import phone_checker, COUNTRY_CODES

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default HTTP logs to avoid spam
        pass

def start_health_server():
    """Start health check server in background"""
    try:
        server = HTTPServer(('0.0.0.0', 8000), HealthCheckHandler)
        logger.info("Health check server started on port 8000")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Failed to start health server: {e}")

class TelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Setup command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("locate", self.locate_ip_command))
        self.application.add_handler(CommandHandler("phone", self.phone_check_command))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_message = f"""
🤖 שלום {user.first_name}! ברוכים הבאים לבוט שלנו!

אני כאן לעזור לך. השתמש ב-/help כדי לראות את כל הפקודות הזמינות.
"""
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📋 פקודות זמינות:

/start - התחלת השיחה עם הבוט
/help - הצגת עזרה
/menu - תפריט אינטראקטיבי
/locate <IP או דומיין> - איתור מיקום IP
/phone <מדינה> <מספר> - בדיקת מספר טלפון

דוגמאות איתור IP:
/locate 8.8.8.8
/locate google.com

דוגמאות בדיקת טלפון:
/phone israel 0524845131
/phone usa 5551234567
/phone uk 07123456789

פשוט שלח לי הודעה ואני אענה לך!
"""
        await update.message.reply_text(help_text)

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command with inline keyboard"""
        keyboard = [
            [InlineKeyboardButton("ℹ️ מידע", callback_data='info')],
            [InlineKeyboardButton("📍 איתור IP", callback_data='locate_demo')],
            [InlineKeyboardButton("📱 בדיקת טלפון", callback_data='phone_demo')],
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

        if query.data == 'info':
            await query.edit_message_text("ℹ️ זהו בוט טלגרם פשוט וחכם שנבנה בפייתון!")
        elif query.data == 'settings':
            await query.edit_message_text("⚙️ כאן תוכל לשנות הגדרות (בפיתוח)")
        elif query.data == 'locate_demo':
            await query.edit_message_text("📍 איתור IP - השתמש בפקודה:\n\n/locate 8.8.8.8\n/locate google.com\n\nהבוט יחפש את המיקום הגאוגרפי של ה-IP!")
        elif query.data == 'phone_demo':
            await query.edit_message_text(
                "📱 **בדיקת מספר טלפון**\n\n"
                "השתמש בפקודה:\n"
                "`/phone <מדינה> <מספר>`\n\n"
                "🔹 **דוגמאות:**\n"
                "• `/phone israel 0524845131`\n"
                "• `/phone usa 5551234567`\n"
                "• `/phone uk 07123456789`\n\n"
                "🌍 **מדינות נתמכות:**\n"
                "ישראל, ארה\"ב, בריטניה, גרמניה, צרפת ועוד...",
                parse_mode='Markdown'
            )
        elif query.data == 'locate_another':
            await query.edit_message_text(
                "🔍 **איתור IP חדש**\n\n"
                "השתמש בפקודה:\n"
                "`/locate <IP או דומיין>`\n\n"
                "דוגמאות:\n"
                "• `/locate 1.1.1.1`\n"
                "• `/locate twitter.com`\n"
                "• `/locate yahoo.com`",
                parse_mode='Markdown'
            )
        elif query.data == 'locate_info':
            await query.edit_message_text(
                "ℹ️ **מידע על איתור IP**\n\n"
                "🔍 **איך זה עובד:**\n"
                "הבוט משתמש במספר מסדי נתונים גאוגרפיים כדי לאתר IP addresses\n\n"
                "📊 **מקורות המידע:**\n"
                "• ip-api.com\n"
                "• ipinfo.io\n"
                "• מסדי נתונים נוספים\n\n"
                "⚠️ **חשוב לזכור:**\n"
                "• המיקום מתייחס לתשתית הרשת\n"
                "• דיוק המיקום משתנה בין ספקים\n"
                "• VPN יכול להשפיע על התוצאות\n\n"
                "🛡️ **פרטיות:**\n"
                "הבוט לא שומר את ה-IP שחיפשת"
            )
        elif query.data == 'phone_another':
            await query.edit_message_text(
                "📱 **בדיקת מספר טלפון חדש**\n\n"
                "השתמש בפקודה:\n"
                "`/phone <מדינה> <מספר>`\n\n"
                "🔹 **דוגמאות:**\n"
                "• `/phone israel 0524845131`\n"
                "• `/phone usa 5551234567`\n"
                "• `/phone germany 01701234567`\n\n"
                "🌍 **מדינות נתמכות:**\n"
                "israel, usa, uk, germany, france, italy ועוד...",
                parse_mode='Markdown'
            )
        elif query.data == 'phone_info':
            await query.edit_message_text(
                "ℹ️ **איך בדיקת הטלפון עובדת?**\n\n"
                "🔍 **תהליך הבדיקה:**\n"
                "1. המספר מומר לפורמט בינלאומי\n"
                "2. בדיקת תקינות טכנית\n"
                "3. זיהוי מדינה וקידומת\n"
                "4. ניתוח ספק וסוג קו\n\n"
                "📊 **מה הבוט בודק:**\n"
                "• תקינות המספר\n"
                "• ספק הסלולר (בישראל)\n"
                "• סוג הקו (נייד/קווי)\n"
                "• מדינה ואזור\n\n"
                "⚠️ **חשוב לדעת:**\n"
                "• המידע מבוסס על מסדי נתונים ציבוריים\n"
                "• לא כל המספרים רשומים\n"
                "• המידע עשוי להיות לא מעודכן\n\n"
                "🛡️ **פרטיות:**\n"
                "הבוט לא שומר את המספרים שבדקת"
            )
        elif query.data == 'contact':
            await query.edit_message_text("📞 יצירת קשר: אתה יכול לכתוב לנו כאן בבוט!")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user_message = update.message.text
        user_name = update.effective_user.first_name
        
        # Simple echo with personalization
        response = f"היי {user_name}! קיבלתי את ההודעה שלך:\n\n💬 \"{user_message}\"\n\nאיך אני יכול לעזור לך?"
        
        await update.message.reply_text(response)

    async def locate_ip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /locate command for IP geolocation"""
        user_name = update.effective_user.first_name
        
        # Check if IP/domain was provided
        if not context.args:
            help_text = """
📍 איתור מיקום IP

שימוש: /locate <IP או דומיין>

דוגמאות:
• /locate 8.8.8.8
• /locate google.com  
• /locate facebook.com
• /locate 1.1.1.1

הבוט יחפש את המיקום הגאוגרפי של כתובת ה-IP!
"""
            await update.message.reply_text(help_text)
            return
        
        target = context.args[0]
        
        # Send "typing" action
        await update.message.chat.send_action("typing")
        
        # Send initial processing message
        processing_msg = await update.message.reply_text(
            f"🔍 מחפש את המיקום של {target}...\n⏳ אנא המתן, זה עלול לקחת כמה שניות"
        )
        
        try:
            # Resolve IP if hostname provided
            try:
                ip = socket.gethostbyname(target)
                if ip != target:
                    await processing_msg.edit_text(
                        f"🔍 מחפש את המיקום של {target}...\n"
                        f"📡 זוהה IP: {ip}\n"
                        f"⏳ מקבל נתונים מכמה מקורות..."
                    )
            except Exception:
                await processing_msg.edit_text(f"❌ שגיאה: לא הצלחתי לפתור את {target}")
                return
            
            # Quick GeoIP lookup using multiple sources
            await processing_msg.edit_text(
                f"🔍 מחפש את המיקום של {target}...\n"
                f"📡 IP: {ip}\n"
                f"🌍 בודק מקורות מידע..."
            )
            
            # Try multiple GeoIP services quickly
            results = []
            
            # Service 1: ip-api.com
            try:
                result1 = geoip_ipapi(ip)
                if result1:
                    results.append({
                        'source': 'ip-api.com',
                        'city': result1.get('city'),
                        'region': result1.get('regionName'),
                        'country': result1.get('country'),
                        'lat': result1.get('lat'),
                        'lon': result1.get('lon'),
                        'org': result1.get('org') or result1.get('isp')
                    })
            except Exception:
                pass
                
            # Service 2: ipinfo.io
            try:
                result2 = geoip_ipinfo(ip)
                if result2:
                    results.append({
                        'source': 'ipinfo.io',
                        'city': result2.get('city'),
                        'region': result2.get('region'),
                        'country': result2.get('country'),
                        'lat': result2.get('lat'),
                        'lon': result2.get('lon'),
                        'org': result2.get('org')
                    })
            except Exception:
                pass
            
            if not results:
                await processing_msg.edit_text(
                    f"❌ מצטער {user_name}, לא הצלחתי למצוא מידע על {target}\n"
                    f"ייתכן שה-IP חסום או לא זמין במסדי הנתונים."
                )
                return
            
            # Calculate average location
            lats = [r['lat'] for r in results if r.get('lat') is not None]
            lons = [r['lon'] for r in results if r.get('lon') is not None]
            
            if not lats or not lons:
                await processing_msg.edit_text(
                    f"❌ מצטער {user_name}, לא הצלחתי לקבל קואורדינטות עבור {target}"
                )
                return
            
            avg_lat = sum(lats) / len(lats)
            avg_lon = sum(lons) / len(lons)
            
            # Create response message
            response = f"📍 **מיקום IP: {target}**\n\n"
            response += f"🌐 **כתובת IP:** `{ip}`\n"
            
            if avg_lat and avg_lon:
                response += f"📍 **קואורדינטות:** `{avg_lat:.4f}, {avg_lon:.4f}`\n\n"
            
            # Add info from each source
            cities = set()
            countries = set()
            orgs = set()
            
            response += f"📊 **מידע ממקורות ({len(results)}):**\n"
            for i, result in enumerate(results, 1):
                city = result.get('city', 'לא ידוע')
                country = result.get('country', 'לא ידוע')
                source = result.get('source', 'מקור לא ידוע')
                
                response += f"{i}. **{source}:** {city}, {country}\n"
                
                if city and city != 'לא ידוע':
                    cities.add(city)
                if country and country != 'לא ידוע':
                    countries.add(country)
                if result.get('org'):
                    orgs.add(result['org'])
            
            # Summary
            if cities:
                response += f"\n🏙️ **עיר:** {', '.join(cities)}\n"
            if countries:
                response += f"🇮🇱 **מדינה:** {', '.join(countries)}\n"
            if orgs:
                response += f"🏢 **ארגון/ספק:** {', '.join(list(orgs)[:2])}\n"
            
            # Add Google Maps link
            if avg_lat and avg_lon:
                maps_link = f"https://www.google.com/maps/place/{avg_lat},{avg_lon}/@{avg_lat},{avg_lon},12z"
                response += f"\n🗺️ [פתח במפות Google]({maps_link})\n"
            
            # Add warning
            response += f"\n⚠️ **הערה חשובה:**\n"
            response += f"המיקום מייצג את תשתית הרשת ולא בהכרח את המיקום הפיזי של המשתמש."
            
            # Create inline keyboard for additional options
            keyboard = [
                [InlineKeyboardButton("🔄 בדוק IP אחר", callback_data='locate_another')],
                [InlineKeyboardButton("ℹ️ מידע נוסף", callback_data='locate_info')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                response,
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

    async def phone_check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /phone command for phone number checking"""
        user_name = update.effective_user.first_name
        
        # Check if country and phone number were provided
        if len(context.args) < 2:
            help_text = """
📱 בדיקת מספר טלפון

שימוש: /phone <מדינה> <מספר>

🌍 **מדינות נתמכות:**
• israel - ישראל 🇮🇱
• usa - ארה"ב 🇺🇸  
• uk - בריטניה 🇬🇧
• germany - גרמניה 🇩🇪
• france - צרפת 🇫🇷
• italy - איטליה 🇮🇹

📞 **דוגמאות:**
• /phone israel 0524845131
• /phone usa 5551234567
• /phone uk 07123456789
• /phone germany 01701234567

הבוט יבדוק את המספר ויחזיר מידע על הספק, סוג הקו ועוד!
"""
            await update.message.reply_text(help_text)
            return
        
        country = context.args[0].lower()
        phone_number = context.args[1]
        
        # Validate country
        if country not in COUNTRY_CODES:
            available_countries = ', '.join(COUNTRY_CODES.keys())
            await update.message.reply_text(
                f"❌ מדינה לא נתמכת: {country}\n\n"
                f"🌍 מדינות זמינות:\n{available_countries}\n\n"
                f"דוגמה: /phone israel 0524845131"
            )
            return
        
        # Send "typing" action
        await update.message.chat.send_action("typing")
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            f"📱 בודק את המספר {phone_number} במדינה {COUNTRY_CODES[country]['name']}...\n"
            f"🔍 פונה לבוט TrueCaller לקבלת מידע...\n"
            f"⏳ אנא המתן..."
        )
        
        try:
            # Normalize phone number
            formatted_number, is_valid = phone_checker.normalize_phone_number(phone_number, country)
            
            if not is_valid:
                await processing_msg.edit_text(
                    f"❌ מספר לא תקין: {phone_number}\n\n"
                    f"🔢 וודא שהמספר נכון ונסה שוב.\n"
                    f"דוגמה למדינה {COUNTRY_CODES[country]['name']}: "
                    f"/phone {country} {COUNTRY_CODES[country].get('example', '1234567890')}"
                )
                return
            
            await processing_msg.edit_text(
                f"📱 בודק את המספר {phone_number}...\n"
                f"🔄 מספר בפורמט בינלאומי: {formatted_number}\n"
                f"🤖 שולח בקשה לבוט TrueCaller...\n"
                f"� מחכה לתשובה..."
            )
            
            # Lookup phone information using real TrueCaller bot
            phone_result = phone_checker.check_phone_via_truecaller_bot(formatted_number, self.token)
            
            if not phone_result or not phone_result.get('success'):
                await processing_msg.edit_text(
                    f"📱 **תוצאות בדיקה למספר:** `{phone_number}`\n\n"
                    f"🔢 **מספר בינלאומי:** `{formatted_number}`\n"
                    f"🏳️ **מדינה:** {COUNTRY_CODES[country]['flag']} {COUNTRY_CODES[country]['name']}\n"
                    f"✅ **תקינות:** המספר תקין מבחינה טכנית\n\n"
                    f"ℹ️ **מידע נוסף לא זמין** - ייתכן שהמספר פרטי או לא רשום במסדי נתונים ציבוריים.\n\n"
                    f"⚠️ **הערה:** תוצאות מבוססות על מסדי נתונים ציבוריים בלבד.",
                    parse_mode='Markdown'
                )
                return
            
            # Format and display results using new format
            result_text = phone_checker.format_phone_result(phone_result, phone_number)
            
            # Create inline keyboard for additional options
            keyboard = [
                [InlineKeyboardButton("🔄 בדוק מספר אחר", callback_data='phone_another')],
                [InlineKeyboardButton("ℹ️ איך זה עובד?", callback_data='phone_info')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in phone_check_command: {e}")
            await processing_msg.edit_text(
                f"❌ מצטער {user_name}, אירעה שגיאה בבדיקת המספר {phone_number}\n\n"
                f"🔄 נסה שוב מאוחר יותר או עם מספר אחר.\n\n"
                f"📝 וודא שהפורמט נכון:\n"
                f"`/phone {country} <מספר>`"
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.warning(f'Update {update} caused error {context.error}')

    def run(self):
        """Start the bot"""
        logger.info("Starting Telegram Bot...")
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        # Start polling
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function to run the bot"""
    try:
        # Start health check server in background thread
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()
        
        # Start the bot
        bot = TelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ שגיאה בהפעלת הבוט: {e}")

if __name__ == "__main__":
    main()