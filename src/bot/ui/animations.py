"""
Animation sequences for fishing bot.
Contains casting and hooking animations.
"""

import asyncio
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


async def animate_casting_sequence(message, username, user_level, entry_price, pond_id=None, rod_id=None):
    """Animate the casting sequence with text-only messages"""
    import random
    from .messages import get_cast_header, get_cast_animated_sequence, format_cast_message
    from src.database.db_manager import get_available_ponds, get_user_rods, get_pond_by_id, get_rod_by_id, give_starter_rod

    try:
        user_id = message.from_user.id

        # Use provided pond and rod if available, otherwise select randomly
        if pond_id and rod_id:
            selected_pond = await get_pond_by_id(pond_id)
            selected_rod = await get_rod_by_id(rod_id)

            if not selected_pond or not selected_rod:
                logger.error(f"Invalid pond_id {pond_id} or rod_id {rod_id}")
                return None, None, None

        else:
            # Original random selection logic
            available_ponds = await get_available_ponds(user_level)
            user_rods = await get_user_rods(user_id)

            # Fallback: ensure user has starter rod and access to starter pond
            if not user_rods:
                logger.warning(f"User {user_id} has no rods, giving starter rod")
                await give_starter_rod(user_id)
                user_rods = await get_user_rods(user_id)

            if not available_ponds:
                logger.warning(f"User {user_id} has no available ponds for level {user_level}")
                # Force access to starter pond (level 1) regardless of user level
                available_ponds = await get_available_ponds(1)

            if not available_ponds or not user_rods:
                logger.error(f"Still no available ponds or rods for user {user_id} after fallback")
                return None, None, None

            # Select random pond and rod
            selected_pond = random.choice(available_ponds)
            selected_rod = random.choice(user_rods)

        # Extract data from asyncpg Records
        pond_name = selected_pond['name']
        pond_pair = selected_pond['trading_pair']
        pond_id = selected_pond['id']

        rod_name = selected_rod['name']
        leverage = selected_rod['leverage']
        rod_id = selected_rod['id']

        header = get_cast_header(username, rod_name, pond_name, pond_pair, entry_price, leverage, user_level)

        # Get animated sequence
        animated_sequence = get_cast_animated_sequence()

        # Send initial text message with HTML parse mode
        initial_message = format_cast_message(header, animated_sequence[0])
        cast_msg = await message.reply_text(initial_message, parse_mode='HTML')

        # Animate through remaining sequence (only the animated part changes)
        for i, animated_text in enumerate(animated_sequence[1:]):
            delay = 3.0 if i in [0, 3, 5] else 2.5  # Slower for readability
            await asyncio.sleep(delay)
            full_message = format_cast_message(header, animated_text)
            try:
                await cast_msg.edit_text(full_message, parse_mode='HTML')
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    logger.warning(f"Skipping duplicate message: {animated_text}")
                    continue
                else:
                    raise

        # Return cast message and selected gear info for database
        return cast_msg, pond_id, rod_id  # return IDs for database

    except Exception as e:
        import traceback
        logger.error(f"Error in casting animation: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None, None, None


async def animate_hook_sequence(message, username):
    """Animate the hook sequence with simple messages"""
    try:
        from .messages import get_hook_animated_sequence

        # Get animated sequence
        animated_sequence = get_hook_animated_sequence()

        # Send initial hook message
        hook_msg = await message.reply_text(animated_sequence[0])

        # Animate through remaining sequence
        for i, animated_text in enumerate(animated_sequence[1:]):
            delay = 2.5  # Consistent timing for hook sequence
            await asyncio.sleep(delay)
            try:
                await hook_msg.edit_text(animated_text)
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    logger.warning(f"Skipping duplicate hook message: {animated_text}")
                    continue
                else:
                    logger.warning(f"Hook edit error: {edit_error}")

        return hook_msg

    except Exception as e:
        import traceback
        logger.error(f"Error in hook animation: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


async def send_fish_card_or_fallback(animation_message, card_image, story):
    """Send fish card image or fallback to text story"""
    try:
        if card_image and animation_message:
            # Try to send photo with story as caption
            await animation_message.reply_photo(
                photo=BytesIO(card_image),
                caption=story
            )
        elif animation_message:
            # Fallback: send story as text
            await animation_message.reply_text(story)
        else:
            logger.error("No animation message available to send fish card")

    except Exception as e:
        logger.error(f"Error sending fish card: {e}")
        # Ultimate fallback - try to send just the story
        if animation_message:
            try:
                await animation_message.reply_text(story)
            except Exception as fallback_error:
                logger.error(f"Even fallback failed: {fallback_error}")
