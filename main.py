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
from src.bot.core.bot_config import configure_bot
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

            # Delete the system message "Data from the mini app..." for cleaner UX
            try:
                await update.message.delete()
            except Exception as e:
                logger.warning(f"Could not delete WebApp data message: {e}")

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
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=f"Unknown command: {command}"
                    )
            else:
                await context.bot.send_message(
                    chat_id=user.id,
                    text="Data received from WebApp!"
                )

    except Exception as e:
        logger.error(f"Error handling WebApp data: {e}")
        logger.exception("Full handle_webapp_data error traceback:")
        try:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="Error processing WebApp data"
            )
        except Exception:
            pass

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

async def price_cache_refresh_task():
    """Background task to periodically refresh price cache"""
    from src.utils.crypto_price import warm_up_price_cache

    while True:
        try:
            await asyncio.sleep(300)  # Wait 5 minutes
            cached_count = await warm_up_price_cache()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Error refreshing price cache: {e}")


async def startup(application):
    """Initialize resources"""
    # Check if database reset is requested
    if os.environ.get('RESET_DATABASE') == '1':
        logger.warning("🚨 RESET_DATABASE=1 detected - dropping all tables!")
        await reset_database()
    await init_database()

    # Configure bot commands and settings
    await configure_bot(application)

    # Warm up price cache to reduce API calls at startup
    try:
        from src.utils.crypto_price import warm_up_price_cache
        cached_count = await warm_up_price_cache()
    except Exception as e:
        logger.warning(f"Failed to warm up price cache: {e}")

    # Start background price cache refresh task
    cache_refresh_task = asyncio.create_task(price_cache_refresh_task())
    application.cache_refresh_task = cache_refresh_task

    # Start web server
    port = int(os.environ.get('PORT', 8080))
    web_runner = await start_web_server(port, application)
    application.web_runner = web_runner  # Store runner for cleanup
    logger.info(f"✅ Web server started on port {port}")

async def shutdown(application):
    """Clean up resources"""

    # Cancel price cache refresh task if running
    if hasattr(application, 'cache_refresh_task') and application.cache_refresh_task:
        application.cache_refresh_task.cancel()
        try:
            await application.cache_refresh_task
        except asyncio.CancelledError:
            pass

    # Stop web server if running
    if hasattr(application, 'web_runner') and application.web_runner:
        await application.web_runner.cleanup()
    else:
        logger.debug("No web server to stop")
    await close_pool()

def main():
    """Main entry point"""
    try:
        # Create application
        global application
        application = create_application()
        
        # Add startup and shutdown handlers
        application.post_init = startup
        application.post_shutdown = shutdown
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("👋 Received KeyboardInterrupt")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        logger.exception("Full main error traceback:")
        raise

if __name__ == '__main__':
    main()
