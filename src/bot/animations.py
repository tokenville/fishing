"""
Animation and update logic for the fishing bot.
Handles fishing animations, periodic status updates, and retry mechanisms.
"""

import asyncio
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

async def safe_reply(update, text: str, max_retries: int = 3) -> None:
    """Safely send message with retry logic"""
    for attempt in range(max_retries):
        try:
            await update.message.reply_text(text)
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to send message after {max_retries} attempts: {e}")
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

async def animate_casting_sequence(message, username, user_level, entry_price, pond_id=None, rod_id=None):
    """Animate the casting sequence with text-only messages"""
    import random
    from .message_templates import get_cast_header, get_cast_animated_sequence, format_cast_message
    from src.database.db_manager import get_available_ponds, get_user_rods, get_pond_by_id, get_rod_by_id
    
    try:
        user_id = message.from_user.id
        
        # Use provided pond and rod if available, otherwise select randomly
        if pond_id and rod_id:
            selected_pond = get_pond_by_id(pond_id)
            selected_rod = get_rod_by_id(rod_id)
            
            if not selected_pond or not selected_rod:
                logger.error(f"Invalid pond_id {pond_id} or rod_id {rod_id}")
                return None, None, None
                
            # Convert to expected format for compatibility
            selected_pond = (pond_id, selected_pond[1], selected_pond[2])  # (id, name, trading_pair)
            selected_rod = (rod_id, selected_rod[1], selected_rod[2])     # (id, name, leverage)
        else:
            # Original random selection logic
            available_ponds = get_available_ponds(user_level)
            user_rods = get_user_rods(user_id)
            
            # Fallback: ensure user has starter rod and access to starter pond
            if not user_rods:
                logger.warning(f"User {user_id} has no rods, giving starter rod")
                from src.database.db_manager import give_starter_rod
                give_starter_rod(user_id)
                user_rods = get_user_rods(user_id)
                
            if not available_ponds:
                logger.warning(f"User {user_id} has no available ponds for level {user_level}")
                # Force access to starter pond (level 1) regardless of user level
                available_ponds = get_available_ponds(1)
                
            if not available_ponds or not user_rods:
                logger.error(f"Still no available ponds or rods for user {user_id} after fallback")
                return None, None, None
                
            # Select random pond and rod
            selected_pond = random.choice(available_ponds)
            selected_rod = random.choice(user_rods)
        
        # Create fixed header with pond/rod info
        pond_name = selected_pond[1]  # name column
        pond_pair = selected_pond[2]  # trading_pair column (without extra parentheses)
        rod_name = selected_rod[1]  # name column
        leverage = selected_rod[2]  # leverage column
        
        header = get_cast_header(username, rod_name, pond_name, pond_pair, entry_price, leverage)
        
        # Get animated sequence
        animated_sequence = get_cast_animated_sequence()
        
        # Send initial text message
        initial_message = format_cast_message(header, animated_sequence[0])
        cast_msg = await message.reply_text(initial_message)
        
        # Animate through remaining sequence (only the animated part changes)
        for i, animated_text in enumerate(animated_sequence[1:]):
            delay = 3.0 if i in [0, 3, 5] else 2.5  # Slower for readability
            await asyncio.sleep(delay)
            full_message = format_cast_message(header, animated_text)
            try:
                await cast_msg.edit_text(full_message)
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    logger.warning(f"Skipping duplicate message: {animated_text}")
                    continue
                else:
                    raise
        
        # Return cast message and selected gear info for database
        return cast_msg, selected_pond[0], selected_rod[0]  # return IDs for database
        
    except Exception as e:
        import traceback
        logger.error(f"Error in casting animation: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None, None, None

async def animate_hook_sequence(update, username, rod_name, pond_name, pond_pair, 
                                time_fishing, entry_price, current_price, leverage):
    """Animate the hook sequence with structured messages like casting"""
    from .message_templates import get_hook_header, get_hook_animated_sequence, format_hook_message
    
    try:
        # Create fixed header with rod/pond info (similar to casting)
        header = get_hook_header(username, rod_name, pond_name, pond_pair, 
                               time_fishing, entry_price, current_price, leverage)
        
        # Get animated sequence
        animated_sequence = get_hook_animated_sequence()
        
        # Send initial message with header + first animated text
        initial_message = format_hook_message(header, animated_sequence[0])
        hook_msg = await update.message.reply_text(initial_message)
        
        # Animate through remaining sequence (only the animated part changes)
        for animated_text in animated_sequence[1:]:
            delay = 2.5  # Consistent timing for hook sequence
            await asyncio.sleep(delay)
            full_message = format_hook_message(header, animated_text)
            try:
                await hook_msg.edit_text(full_message)
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    logger.warning(f"Skipping duplicate hook message: {animated_text}")
                    continue
                else:
                    raise
        
        return hook_msg
        
    except Exception as e:
        logger.error(f"Error in hook animation: {e}")
        return None


async def send_fish_card_or_fallback(update, hook_msg, fish_card_image, fish_data, fish_name,
                                   pnl_percent, time_fishing, entry_price, current_price, leverage):
    """Send fish card image or fallback to text message"""
    from .message_templates import get_catch_story_from_db, format_fishing_complete_caption
    
    try:
        if fish_card_image:
            logger.info(f"Sending fish card for {fish_name}")
            
            # Use new database-driven story system
            catch_story = get_catch_story_from_db(fish_data, pnl_percent, time_fishing)
            caption = format_fishing_complete_caption(
                catch_story, pnl_percent, entry_price, current_price, leverage
            )
            
            # Send fish card as photo
            await update.message.reply_photo(
                photo=BytesIO(fish_card_image),
                caption=caption
            )
            
            # Delete the hook message since we're sending a new one with photo
            await hook_msg.delete()
            return True
        
    except Exception as img_error:
        logger.error(f"Error sending fish image: {img_error}")
    
    # Fallback to text-only message
    try:
        catch_story = get_catch_story_from_db(fish_data, pnl_percent, time_fishing)
        final_message = format_fishing_complete_caption(
            catch_story, pnl_percent, entry_price, current_price, leverage
        )
        await hook_msg.edit_text(final_message)
        return False
        
    except Exception as text_error:
        logger.error(f"Error sending fallback text: {text_error}")
        return False