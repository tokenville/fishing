"""
Main entry point for the fishing bot.
Handles bot startup, configuration, and graceful shutdown with conflict resolution.
"""

import os
import time
import asyncio
import logging
from telegram import Bot
from telegram.ext import Application, CommandHandler
from telegram.error import Conflict

from src.database.db_manager import init_database
from src.bot.command_handlers import cast, hook, status, test_card, help_command

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Please set TELEGRAM_BOT_TOKEN environment variable")

def kill_existing_bot_processes():
    """Find and kill existing bot processes"""
    try:
        import subprocess
        import signal
        
        # Find existing bot processes
        result = subprocess.run(
            ['ps', 'aux'], 
            capture_output=True, 
            text=True
        )
        
        killed_count = 0
        for line in result.stdout.split('\n'):
            # Look for Python processes running bot-related scripts
            if ('python' in line and 
                ('bot.py' in line or 'main.py' in line) and 
                'grep' not in line and
                str(os.getpid()) not in line):  # Don't kill ourselves
                
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        os.kill(pid, signal.SIGTERM)
                        killed_count += 1
                        logger.info(f"🔪 Killed existing bot process (PID {pid})")
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
        
        if killed_count > 0:
            time.sleep(5)  # Wait longer for processes to terminate
            logger.info(f"✅ Stopped {killed_count} existing bot process(es)")
        else:
            logger.info("✅ No existing bot processes found")
        
    except Exception as e:
        logger.warning(f"⚠️ Warning during process cleanup: {e}")

def cleanup_bot_instance_sync():
    """Clean up any existing bot instances by clearing webhooks - synchronous version"""
    try:
        import requests
        
        # Use direct HTTP request instead of asyncio
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        params = {"drop_pending_updates": True}
        
        response = requests.post(url, params=params, timeout=10)
        if response.status_code == 200:
            logger.info("🔄 Cleared existing webhooks and pending updates")
        else:
            logger.warning(f"⚠️ Webhook cleanup returned status: {response.status_code}")
        
        time.sleep(3)  # Longer delay to ensure cleanup
        
    except Exception as e:
        logger.warning(f"⚠️ Warning during bot cleanup: {e}")

def create_application():
    """Create and configure the bot application"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("cast", cast))
    application.add_handler(CommandHandler("hook", hook))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("test_card", test_card))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", help_command))
    
    return application

def run_bot():
    """Run the bot with conflict handling and automatic cleanup"""
    # Initialize database
    init_database()
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Clean up existing instances before each attempt - synchronously
            if attempt == 0:
                logger.info("🛑 Stopping any existing bot instances...")
                kill_existing_bot_processes()  # Kill processes first
                cleanup_bot_instance_sync()    # Then clear webhooks
            else:
                logger.info(f"🔄 Retrying with cleanup (attempt {attempt + 1}/{max_retries})...")
                kill_existing_bot_processes()  # Kill processes first
                cleanup_bot_instance_sync()    # Then clear webhooks
            
            # Create fresh application instance
            application = create_application()
            
            logger.info(f"🎣 Fishing Bot starting... (attempt {attempt + 1}/{max_retries})")
            
            # Start the bot
            application.run_polling()
            logger.info("✅ Bot started successfully!")
            break  # Success, exit retry loop
            
        except Conflict as e:
            logger.error(f"❌ Bot conflict detected: {e}")
            if attempt < max_retries - 1:
                logger.info(f"⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            else:
                logger.error("💥 Failed to start after all retries. Another bot instance may be running.")
                raise
                
        except KeyboardInterrupt:
            logger.info("👋 Bot stopped by user")
            break
            
        except Exception as e:
            logger.error(f"💥 Unexpected error: {e}")
            if attempt < max_retries - 1:
                logger.info(f"⏳ Waiting {retry_delay - 2} seconds before retry...")
                time.sleep(retry_delay - 2)
            else:
                logger.error("💥 Failed to start after all retries due to unexpected errors.")
                raise

def main():
    """Main entry point"""
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("👋 Fishing Bot shut down gracefully")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        raise

if __name__ == '__main__':
    main()