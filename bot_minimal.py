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
            await update.message.reply_text(
                "📚 Available Commands:\n"
                "/start - Start the bot\n" 
                "/help - This help message\n"
                "/status - Bot status\n"
                "\nBot is running in cloud mode ☁️"
            )
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