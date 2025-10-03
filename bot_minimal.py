"""
Emergency Minimal Bot - Cloud Stable Version
"""
import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

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

try:
    from stock_analyzer import stock_analyzer, format_stock_analysis
    STOCK_AVAILABLE = True
    logger.info("Stock analysis loaded successfully")
except Exception as e:
    logger.warning(f"Stock analysis not available: {e}")

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

class MinimalBot:
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
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
            
        # Network tools (if available)  
        if NETWORK_AVAILABLE:
            self.application.add_handler(CommandHandler("ping", self.ping_command))
            self.application.add_handler(CommandHandler("scan", self.scan_command))
            
        # IP location tools (if available)
        if IP_LOCATION_AVAILABLE:
            self.application.add_handler(CommandHandler("locate", self.locate_command))
            self.application.add_handler(CommandHandler("ip", self.ip_command))
        
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
            help_text = (
                "📚 Available Commands:\n"
                "/start - Start the bot\n" 
                "/help - This help message\n"
                "/status - Bot status\n"
            )
            
            if STOCK_AVAILABLE:
                help_text += "/stock <SYMBOL> - Stock analysis\n"
                
            if NETWORK_AVAILABLE:
                help_text += "/ping <HOST> - Ping a host\n"
                help_text += "/scan <IP> - Scan ports\n"
                
            if IP_LOCATION_AVAILABLE:
                help_text += "/locate <IP> - Find IP location\n"
                help_text += "/ip <IP> - Get IP details\n"
            
            help_text += "\nBot is running in cloud mode ☁️"
            
            await update.message.reply_text(help_text)
        except Exception as e:
            logger.error(f"Help command error: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            await update.message.reply_text(
                "✅ Bot Status: ONLINE\n"
                "🌐 Environment: Cloud\n"
                "🐍 Python: OK\n"
                "📡 Telegram API: Connected"
            )
        except Exception as e:
            logger.error(f"Status command error: {e}")
    
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
        """Handle /scan command"""
        if not NETWORK_AVAILABLE:
            await update.message.reply_text("❌ Network tools not available in this deployment")
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "🔍 **Port Scanner**\n\n"
                    "Usage: `/scan <IP>`\n\n"
                    "Examples:\n"
                    "• `/scan 192.168.1.1`\n"
                    "• `/scan google.com`\n\n"
                    "Scans common ports (21,22,23,25,53,80,110,443,993,995)"
                )
                return
                
            target = context.args[0]
            status_msg = await update.message.reply_text(f"🔍 Scanning {target}...")
            
            # Perform port scan
            network_tools = NetworkTools()
            common_ports = [21, 22, 23, 25, 53, 80, 110, 443, 993, 995]
            results = await network_tools.scan_ports(target, common_ports, timeout=3)
            
            if results:
                response = f"🔍 **Port Scan Results - {target}**\n\n"
                open_ports = [r for r in results if r['status'] == 'Open']
                
                if open_ports:
                    response += f"🟢 **Open Ports:**\n"
                    for port in open_ports[:10]:  # Limit to 10 ports
                        response += f"• {port['port']}/{port['protocol']} - {port['service']}\n"
                else:
                    response += "🔒 No open ports found"
            else:
                response = f"❌ Scan failed for {target}"
                
            await status_msg.edit_text(response)
            
        except Exception as e:
            logger.error(f"Scan command error: {e}")
            await update.message.reply_text(f"❌ Error scanning {target}: {str(e)}")

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

def main():
    """Main function"""
    try:
        # Get bot token
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")
        
        logger.info("Initializing bot...")
        bot = MinimalBot(bot_token)
        
        logger.info("Bot ready - starting polling...")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()