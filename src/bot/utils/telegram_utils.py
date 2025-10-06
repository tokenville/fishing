"""
Telegram utility functions for safe message sending and editing.
Contains retry logic and error handling for Telegram API calls.
"""

import asyncio
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


async def safe_reply(update, text: str, max_retries: int = 3, parse_mode: str = None) -> None:
    """Safely send message with retry logic"""
    logger.debug(f"safe_reply called with update type: {type(update)}, has message: {hasattr(update, 'message') if update else False}")

    if not update:
        logger.error("safe_reply called with None update object")
        return

    message = getattr(update, 'message', None)
    if not message and hasattr(update, 'callback_query') and update.callback_query:
        message = update.callback_query.message
    if not message and hasattr(update, 'effective_message'):
        message = update.effective_message

    if not message:
        logger.error(f"Update object has no message context for safe_reply. Update: {update}")
        return

    for attempt in range(max_retries):
        try:
            logger.debug(f"safe_reply attempt {attempt + 1}: sending message to chat {message.chat_id if message else 'unknown'}")
            if parse_mode:
                await message.reply_text(text, parse_mode=parse_mode)
            else:
                await message.reply_text(text)
            logger.debug(f"safe_reply successful on attempt {attempt + 1}")
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to send message after {max_retries} attempts: {e}")
                logger.exception("Full safe_reply error traceback:")
            else:
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(1)


async def safe_send_message(context, chat_id: int, text: str, max_retries: int = 3) -> None:
    """Safely send message to chat with retry logic (for cases without original message)"""
    for attempt in range(max_retries):
        try:
            logger.debug(f"safe_send_message attempt {attempt + 1}: sending message to chat {chat_id}")
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
            logger.debug(f"safe_send_message successful on attempt {attempt + 1}")
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to send message after {max_retries} attempts: {e}")
                logger.exception("Full safe_send_message error traceback:")
            else:
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(1)


async def safe_reply_photo(update, photo_data: bytes, caption: str, max_retries: int = 3) -> None:
    """Safely send photo with retry logic"""
    for attempt in range(max_retries):
        try:
            await update.message.reply_photo(photo=BytesIO(photo_data), caption=caption)
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to send photo after {max_retries} attempts: {e}")
            else:
                logger.warning(f"Photo attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(1)


async def safe_edit_message(message, text: str, max_retries: int = 3) -> None:
    """Safely edit message text or caption depending on message type"""
    for attempt in range(max_retries):
        try:
            # Check if message has video/photo (needs caption edit) or is text message
            if message.video or message.photo:
                await message.edit_caption(caption=text)
            else:
                await message.edit_text(text)
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to edit message after {max_retries} attempts: {e}")
            else:
                logger.warning(f"Edit attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(1)


async def send_telegram_notification(user_id: int, message: str, application=None):
    """Send a notification message to a user via Telegram"""
    try:
        if application is None:
            try:
                from main import application  # Import application instance from main module
            except ImportError:
                logger.warning(f"Could not import application to send notification to user {user_id}")
                return

        if application and application.bot:
            await application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Sent notification to user {user_id}")
        else:
            logger.warning(f"Application or bot not available to send notification to user {user_id}")

    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {e}")
        raise
