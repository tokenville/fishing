"""
Main entry point for the fishing bot with PostgreSQL support.
Handles bot startup, configuration, and graceful shutdown.
"""

import os
import asyncio
import logging
from telegram.ext import Application, CommandHandler, ChatMemberHandler, CallbackQueryHandler, Defaults

from src.database.db_manager import init_database, close_pool, reset_database
from src.bot.command_handlers import cast, hook, status, test_card, help_command, start_command, leaderboard, pnl, pond_selection_callback, gofishing, join_fishing_callback
from src.bot.group_handlers import my_chat_member_handler, chat_member_handler
from src.webapp.web_server import start_web_server

# Configure logging level from environment
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
log_level_value = getattr(logging, log_level, logging.INFO)

# Enable logging with configurable level
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level_value
)

# Suppress some verbose logs (only if not in DEBUG mode)
if log_level_value > logging.DEBUG:
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
else:
    # In DEBUG mode, show more detailed logs
    logging.getLogger('httpx').setLevel(logging.INFO)
    logging.getLogger('telegram').setLevel(logging.INFO)
    logging.getLogger('aiohttp').setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.info(f"Logging configured with level: {log_level} ({log_level_value})")

# Bot token from environment
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
    raise RuntimeError("Please set TELEGRAM_BOT_TOKEN environment variable")
else:
    logger.debug(f"Bot token loaded: {'*' * (len(BOT_TOKEN) - 8)}{BOT_TOKEN[-8:]}")

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
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("pnl", pnl))
    application.add_handler(CommandHandler("gofishing", gofishing))
    
    # Add group management handlers
    application.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(chat_member_handler, ChatMemberHandler.CHAT_MEMBER))
    
    # Add callback handlers
    application.add_handler(CallbackQueryHandler(pond_selection_callback, pattern=r"^select_pond_"))
    application.add_handler(CallbackQueryHandler(join_fishing_callback, pattern=r"^join_fishing_"))
    
    return application

async def startup(application):
    """Initialize resources"""
    logger.debug("Starting application startup sequence...")
    logger.debug(f"Environment variables: PORT={os.environ.get('PORT', '8080')}, WEBAPP_URL={os.environ.get('WEBAPP_URL')}")
    
    # Check if database reset is requested
    if os.environ.get('RESET_DATABASE') == '1':
        logger.warning("🚨 RESET_DATABASE=1 detected - dropping all tables!")
        await reset_database()
        logger.info("✅ Database reset completed")
    
    logger.debug("Initializing database...")
    await init_database()
    logger.info("✅ PostgreSQL database initialized")
    
    # Start web server
    port = int(os.environ.get('PORT', 8080))
    logger.debug(f"Starting web server on port {port}...")
    web_runner = await start_web_server(port)
    application.web_runner = web_runner  # Store runner for cleanup
    logger.info(f"✅ Web server started on port {port}")
    logger.debug("Application startup sequence completed")

async def shutdown(application):
    """Clean up resources"""
    logger.info("🧹 Cleaning up resources...")
    logger.debug("Starting shutdown sequence...")
    
    # Stop web server if running
    if hasattr(application, 'web_runner') and application.web_runner:
        logger.debug("Stopping web server...")
        await application.web_runner.cleanup()
        logger.info("✅ Web server stopped")
    else:
        logger.debug("No web server to stop")
    
    logger.debug("Closing database pool...")
    await close_pool()
    logger.info("✅ Database pool closed")
    logger.info("✅ Shutdown completed")

def main():
    """Main entry point"""
    try:
        logger.debug("Creating bot application...")
        # Create application
        application = create_application()
        logger.debug("Bot application created")
        
        # Add startup and shutdown handlers
        application.post_init = startup
        application.post_shutdown = shutdown
        
        logger.info("🎣 Starting Fishing Bot with PostgreSQL...")
        
        # Run the bot - this handles all signals and shutdown gracefully
        logger.debug("Starting bot polling...")
        application.run_polling(drop_pending_updates=True)
        
        logger.info("👋 Fishing Bot shut down gracefully")
        
    except KeyboardInterrupt:
        logger.info("👋 Received KeyboardInterrupt")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        logger.exception("Full main error traceback:")
        raise

if __name__ == '__main__':
    main()