"""
Command handlers for the fishing bot.
Contains all Telegram bot command handlers (cast, hook, status, help, test_card).
"""

import asyncio
import logging
from io import BytesIO
from telegram import Update
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, get_active_position,
    create_position, close_position, use_bait
)
from src.utils.eth_price import get_eth_price, calculate_pnl, get_fish_by_pnl, format_time_fishing
from src.bot.message_templates import (
    get_simple_cast_messages, get_hook_tension_message, get_catch_story,
    get_help_text, format_cast_initial_message, format_status_message,
    format_no_fishing_status, format_new_user_status, get_status_description
)
from src.bot.animations import (
    safe_reply, safe_reply_photo, animate_casting_sequence,
    animate_hook_sequence, start_fishing_updates, send_fish_card_or_fallback
)
from src.generators.fish_card_generator import generate_fish_card_image

logger = logging.getLogger(__name__)

async def cast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cast command - start animated fishing"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Get or create user
        user = get_user(user_id)
        if not user:
            create_user(user_id, username)
            user = get_user(user_id)
        
        # Check if user has enough BAIT
        if user[2] <= 0:  # bait_tokens is index 2
            await safe_reply(update, "🎣 No $BAIT left! Need more worms to fish 🪱")
            return
        
        # Check if user is already fishing
        active_position = get_active_position(user_id)
        if active_position:
            await safe_reply(update, f"🎣 {username} already has line in the water! Use /hook to reel it in or /status to check progress.")
            return
        
        # Use bait and get current ETH price
        if not use_bait(user_id):
            await safe_reply(update, "🎣 Failed to use bait. Try again!")
            return
        
        current_price = get_eth_price()
        
        # Create position first
        create_position(user_id, current_price)
        
        # Simple literary casting
        cast_messages = get_simple_cast_messages()
        cast_msg = await animate_casting_sequence(
            update.message, cast_messages
        )
        if not cast_msg:
            await safe_reply(update, "🎣 Something went wrong with casting! Try again.")
            return
        
        # Simple waiting story updates
        asyncio.create_task(start_fishing_updates(cast_msg, user_id, username))
        
    except Exception as e:
        logger.error(f"Error in cast command: {e}")
        await safe_reply(update, "🎣 Something went wrong! Try again in a moment.")

async def hook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /hook command - dramatic fishing finale"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Check if user has active position
        position = get_active_position(user_id)
        if not position:
            await safe_reply(update, f"🎣 {username} has no line cast! Use /cast to start fishing.")
            return
        
        # Get current price and calculate P&L
        current_price = get_eth_price()
        entry_price = position[2]  # entry_price is index 2
        pnl_percent = calculate_pnl(entry_price, current_price, leverage=2.0)
        
        # Format time spent fishing
        time_fishing = format_time_fishing(position[3])  # entry_time is index 3
        
        # Simple literary hook story
        hook_msg = await animate_hook_sequence(update, username, get_hook_tension_message(pnl_percent))
        if not hook_msg:
            await safe_reply(update, "🎣 Something went wrong with hooking! Try again.")
            return
        
        # Determine catch and close position
        fish_caught = get_fish_by_pnl(pnl_percent)
        close_position(position[0], current_price, pnl_percent, fish_caught)
        
        # Generate fish card image and send result
        try:
            logger.info(f"Generating fish card for {fish_caught}")
            fish_card_image = await generate_fish_card_image(fish_caught, pnl_percent, time_fishing)
        except Exception as img_error:
            logger.error(f"Error generating fish image: {img_error}")
            fish_card_image = None
        
        # Send fish card or fallback to text
        await send_fish_card_or_fallback(
            update, hook_msg, fish_card_image, fish_caught,
            pnl_percent, time_fishing, entry_price, current_price
        )
        
    except Exception as e:
        logger.error(f"Error in hook command: {e}")
        await safe_reply(update, "🎣 Something went wrong! Try again in a moment.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show current position"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Check if user has active position
        position = get_active_position(user_id)
        if not position:
            # Show user stats instead
            user = get_user(user_id)
            if user:
                message = format_no_fishing_status(username, user[2])
            else:
                message = format_new_user_status(username)
            await safe_reply(update, message)
            return
        
        # Calculate current P&L
        current_price = get_eth_price()
        entry_price = position[2]
        current_pnl = calculate_pnl(entry_price, current_price, leverage=2.0)
        
        # Format time spent fishing
        time_fishing = format_time_fishing(position[3])
        
        # Create status message
        status_desc = get_status_description(current_pnl, time_fishing)
        message = format_status_message(username, status_desc, entry_price, current_price, current_pnl)
        
        await safe_reply(update, message)
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await safe_reply(update, "🎣 Something went wrong! Try again in a moment.")

async def test_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /test_card command - test fish card generation"""
    try:
        # Generate test cards for different fish types
        test_fish = [
            ("🦐 Soggy Boot", -25.0, "5m 30s"),
            ("🐡 Pufferfish of Regret", -8.5, "2m 15s"),
            ("🐟 Lucky Minnow", 12.3, "3m 45s"),
            ("🐠 Diamond Fin Bass", 28.7, "4m 20s"),
            ("🦈 Profit Shark", 67.2, "6m 10s"),
            ("🐋 Legendary Whale", 156.8, "8m 35s")
        ]
        
        await update.message.reply_text("🎨 Generating test fish cards...")
        
        for fish_name, pnl, time_fishing in test_fish:
            try:
                logger.info(f"Generating test card for {fish_name}")
                fish_card_image = await generate_fish_card_image(fish_name, pnl, time_fishing)
                
                await update.message.reply_photo(
                    photo=BytesIO(fish_card_image),
                    caption=f"Test card: {fish_name} ({pnl:+.1f}% in {time_fishing})"
                )
                
                # Small delay between cards
                await asyncio.sleep(1)
                
            except Exception as card_error:
                logger.error(f"Error generating test card for {fish_name}: {card_error}")
                await update.message.reply_text(f"❌ Failed to generate {fish_name} card: {card_error}")
        
        await update.message.reply_text("✅ Test cards generation complete!")
        
    except Exception as e:
        logger.error(f"Error in test_card command: {e}")
        await safe_reply(update, "🎣 Something went wrong with test cards! Try again in a moment.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    try:
        help_text = get_help_text()
        await safe_reply(update, help_text)
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await safe_reply(update, "🎣 Something went wrong! Try again in a moment.")