"""
Main entry point for the fishing bot with PostgreSQL support.
Handles bot startup, configuration, and graceful shutdown.
"""

import os
import logging
from telegram.ext import Application, CommandHandler, Defaults

from src.database.db_manager import init_database
from src.bot.command_handlers import cast, hook, status, test_card, help_command

# Enable logging with less verbose output
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Suppress some verbose logs
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Bot token from environment
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Please set TELEGRAM_BOT_TOKEN environment variable")

def create_application():
    """Create and configure the bot application"""
    defaults = Defaults(parse_mode='HTML')
    application = Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("cast", cast))
    application.add_handler(CommandHandler("hook", hook))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("test_card", test_card))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", help_command))
    
    return application

async def startup(application):
    """Initialize resources"""
    await init_database()
    logger.info("✅ PostgreSQL database initialized")

async def shutdown(application):
    """Clean up resources"""
    logger.info("🧹 Cleaning up resources...")
    logger.info("✅ Shutdown completed")

def main():
    """Main entry point"""
    try:
        # Create application
        application = create_application()
        
        # Add startup and shutdown handlers
        application.post_init = startup
        application.post_shutdown = shutdown
        
        logger.info("🎣 Starting Fishing Bot with PostgreSQL...")
        
        # Run the bot - this handles all signals and shutdown gracefully
        application.run_polling(drop_pending_updates=True)
        
        logger.info("👋 Fishing Bot shut down gracefully")
        
    except KeyboardInterrupt:
        logger.info("👋 Received KeyboardInterrupt")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        raise

if __name__ == '__main__':
    main()