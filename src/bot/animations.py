"""
Animation and update logic for the fishing bot.
Handles fishing animations, periodic status updates, and retry mechanisms.
"""

import asyncio
import logging
from io import BytesIO
from src.database.db_manager import get_active_position
from src.utils.eth_price import get_eth_price, calculate_pnl, format_time_fishing
from src.bot.message_templates import (
    get_waiting_messages, get_status_description, 
    format_fishing_status_update, format_final_waiting_message
)

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

async def animate_casting_sequence(message, cast_messages):
    """Animate the casting sequence with messages"""
    try:
        # Start with first message
        cast_msg = await message.reply_text(cast_messages[0])
        
        # Animate through remaining casting messages
        for msg in cast_messages[1:]:
            await asyncio.sleep(1)
            await cast_msg.edit_text(msg)
        
        return cast_msg
        
    except Exception as e:
        logger.error(f"Error in casting animation: {e}")
        return None

async def animate_hook_sequence(update, username, tension_msg):
    """Animate the hook sequence"""
    try:
        # Step 1: Tension building
        hook_msg = await update.message.reply_text(f"🎣 {username} SETS THE HOOK!\n\n{tension_msg}")
        await asyncio.sleep(2)
        
        # Step 2: Simple battle
        await hook_msg.edit_text("⚡ Reeling in... almost there!")
        await asyncio.sleep(2)
        
        # Step 3: Coming up from depths
        await hook_msg.edit_text("🌊 Something is coming up from the depths!")
        await asyncio.sleep(2)
        
        return hook_msg
        
    except Exception as e:
        logger.error(f"Error in hook animation: {e}")
        return None

async def start_fishing_updates(message, user_id, username):
    """Start periodic fishing status updates - simplified and reliable"""
    waiting_messages = get_waiting_messages()
    update_count = 0
    
    try:
        # Wait 5 seconds before starting updates to let user read initial message
        await asyncio.sleep(5)
        
        # Update every 10 seconds for 1 minute (6 updates total)
        while update_count < 6:
            await asyncio.sleep(10)
            
            # Check if position still active
            position = get_active_position(user_id)
            if not position:
                break
                
            update_count += 1
            
            # Get current P&L and prices
            current_price = get_eth_price()
            entry_price = position[2]
            current_pnl = calculate_pnl(entry_price, current_price, leverage=2.0)
            time_fishing = format_time_fishing(position[3])
            
            # Get current status message
            status_desc = get_status_description(current_pnl, time_fishing)
            
            # Get waiting message based on update count (fix indexing)
            if update_count <= len(waiting_messages):
                waiting_msg = waiting_messages[update_count - 1]
            else:
                waiting_msg = "🔮 We can only wait and see what happens..."
            
            # Create consolidated update message
            updated_text = format_fishing_status_update(
                username, time_fishing, status_desc, waiting_msg,
                entry_price, current_price, current_pnl
            )
            
            await message.edit_text(updated_text)
        
        # Final waiting message after 1 minute
        if get_active_position(user_id):
            position = get_active_position(user_id)
            current_price = get_eth_price()
            entry_price = position[2]
            current_pnl = calculate_pnl(entry_price, current_price, leverage=2.0)
            time_fishing = format_time_fishing(position[3])
            
            final_text = format_final_waiting_message(
                username, time_fishing, entry_price, current_price, current_pnl
            )
            
            await message.edit_text(final_text)
                
    except Exception as e:
        logger.error(f"Error in fishing updates: {e}")

async def send_fish_card_or_fallback(update, hook_msg, fish_card_image, fish_caught, 
                                   pnl_percent, time_fishing, entry_price, current_price):
    """Send fish card image or fallback to text message"""
    from .message_templates import get_catch_story, format_fishing_complete_caption
    
    try:
        if fish_card_image:
            logger.info(f"Sending fish card for {fish_caught}")
            
            catch_story = get_catch_story(fish_caught, pnl_percent, time_fishing)
            caption = format_fishing_complete_caption(
                catch_story, pnl_percent, entry_price, current_price
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
        catch_story = get_catch_story(fish_caught, pnl_percent, time_fishing)
        final_message = format_fishing_complete_caption(
            catch_story, pnl_percent, entry_price, current_price
        )
        await hook_msg.edit_text(final_message)
        return False
        
    except Exception as text_error:
        logger.error(f"Error sending fallback text: {text_error}")
        return False