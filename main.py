"""
Main entry point for the fishing bot with PostgreSQL support.
Handles bot startup, configuration, and graceful shutdown.
"""

import os
import asyncio
import logging
from telegram.ext import Application, CommandHandler, ChatMemberHandler, CallbackQueryHandler, Defaults

from src.database.db_manager import init_database, close_pool
from src.bot.command_handlers import cast, hook, status, test_card, help_command, start_command, leaderboard, pnl, pond_selection_callback
from src.bot.group_handlers import my_chat_member_handler, chat_member_handler
from src.webapp.web_server import start_web_server

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
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("pnl", pnl))
    
    # Add group management handlers
    application.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(chat_member_handler, ChatMemberHandler.CHAT_MEMBER))
    
    # Add callback handlers
    application.add_handler(CallbackQueryHandler(pond_selection_callback, pattern=r"^select_pond_"))
    
    return application

async def startup(application):
    """Initialize resources"""
    await init_database()
    logger.info("✅ PostgreSQL database initialized")
    
    # Start web server
    port = int(os.environ.get('PORT', 8000))
    web_runner = await start_web_server(port)
    application.web_runner = web_runner  # Store runner for cleanup
    logger.info(f"✅ Web server started on port {port}")

async def shutdown(application):
    """Clean up resources"""
    logger.info("🧹 Cleaning up resources...")
    
    # Stop web server if running
    if hasattr(application, 'web_runner') and application.web_runner:
        await application.web_runner.cleanup()
        logger.info("✅ Web server stopped")
    
    await close_pool()
    logger.info("✅ Database pool closed")
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