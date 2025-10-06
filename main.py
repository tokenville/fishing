"""
Main entry point for the fishing bot with PostgreSQL support.
Handles bot startup, configuration, and graceful shutdown.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram.ext import Application, Defaults
from telegram import Update
from telegram.ext import ContextTypes

# Load environment variables from .env file
load_dotenv()

from src.database.db_manager import init_database, close_pool, reset_database
from src.bot.core.handlers_registry import register_all_handlers
from src.webapp.web_server import start_web_server

# Configure logging level from environment
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
log_level_value = getattr(logging, log_level, logging.INFO)

# Enable logging with configurable level
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level_value
)

# Suppress verbose logs from external libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

# In DEBUG mode, still suppress the most verbose logs but allow some telegram logs
if log_level_value > logging.DEBUG:
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
else:
    # In DEBUG mode, show telegram logs but still suppress HTTP polling
    logging.getLogger('telegram').setLevel(logging.INFO)
    logging.getLogger('aiohttp').setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.info(f"Logging configured with level: {log_level} ({log_level_value})")

# Global application instance for external access
application = None

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle data from WebApp"""
    try:
        from src.bot.commands.cast import cast
        from src.bot.commands.hook import hook
        from src.bot.commands.status import status

        if update.message and update.message.web_app_data:
            data = update.message.web_app_data.data
            user = update.effective_user
            chat = update.effective_chat

            logger.info(f"WebApp data received from user {user.id}: {data}")

            # Если данные - это команда, выполняем её
            if data.startswith('/'):
                command = data.strip()
                logger.info(f"Executing command from WebApp: {command}")

                # Создаем фейковое сообщение с командой
                if command == '/cast':
                    await cast(update, context)
                elif command == '/hook':
                    await hook(update, context)
                elif command == '/status':
                    await status(update, context)
                else:
                    await update.message.reply_text(f"Unknown command: {command}")
            else:
                await update.message.reply_text("Data received from WebApp!")

    except Exception as e:
        logger.error(f"Error handling WebApp data: {e}")
        if update.message:
            await update.message.reply_text("Error processing WebApp data")

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

    # Register all handlers through centralized registry
    register_all_handlers(application)

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
    web_runner = await start_web_server(port, application)
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
        global application
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
