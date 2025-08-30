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
    get_user, create_user, get_active_position, close_position, use_bait, create_position_with_gear,
    ensure_user_has_level, give_starter_rod
)
from src.utils.crypto_price import get_crypto_price, calculate_pnl, format_time_fishing
from src.bot.message_templates import (
    get_help_text,
    format_no_fishing_status, format_new_user_status,
    format_enhanced_status_message
)
from src.bot.animations import (
    safe_reply, animate_casting_sequence,
    animate_hook_sequence, send_fish_card_or_fallback
)
from src.generators.fish_card_generator import generate_fish_card_from_db

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
        else:
            # Ensure existing user has level and starter rod
            ensure_user_has_level(user_id)
            give_starter_rod(user_id)
            user = get_user(user_id)  # Refresh user data
        
        # Check if user has enough BAIT
        if user[2] <= 0:  # bait_tokens is index 2
            await safe_reply(update, "🎣 Нет токенов $BAIT! Нужно больше червячков для рыбалки 🪱")
            return
        
        # Check if user is already fishing
        active_position = get_active_position(user_id)
        if active_position:
            await safe_reply(update, f"🎣 У {username} уже есть удочка в воде! Используйте /hook чтобы вытащить улов или /status чтобы проверить прогресс.")
            return
        
        # Use bait and get current price
        if not use_bait(user_id):
            await safe_reply(update, "🎣 Не удалось использовать наживку. Попробуйте еще раз!")
            return
        
        user_level = user[4] if user and len(user) > 4 else 1  # Get level from user data (5th column)
        
        # Get pond and price before animation to show correct starting position
        from src.database.db_manager import get_available_ponds, get_user_rods
        available_ponds = get_available_ponds(user_level)
        user_rods = get_user_rods(user_id)
        
        # Fallback logic for starter equipment
        if not user_rods:
            give_starter_rod(user_id)
            user_rods = get_user_rods(user_id)
            
        if not available_ponds:
            available_ponds = get_available_ponds(1)  # Force starter pond access
            
        if not available_ponds or not user_rods:
            await safe_reply(update, "🎣 Что-то пошло не так с оборудованием! Попробуйте еще раз.")
            return
        
        # Pre-select pond and rod to get actual price
        import random
        selected_pond = random.choice(available_ponds)
        selected_rod = random.choice(user_rods)
        pond_id = selected_pond[0]
        rod_id = selected_rod[0]
        
        # Get actual crypto price before animation
        from src.database.db_manager import get_pond_by_id
        pond = get_pond_by_id(pond_id)
        base_currency = pond[3] if pond else 'ETH'  # base_currency is index 3
        current_price = get_crypto_price(base_currency)
        
        # Enhanced social casting animation with real price
        result = await animate_casting_sequence(
            update.message, username, user_level, current_price, pond_id, rod_id
        )
        
        if not result or not result[0]:
            await safe_reply(update, "🎣 Что-то пошло не так с забросом! Попробуйте еще раз.")
            return
            
        cast_msg, returned_pond_id, returned_rod_id = result
        
        # Use pre-selected gear (ignore returned values since we already chose)
        # Create position with selected gear
        create_position_with_gear(user_id, pond_id, rod_id, current_price)
        
    except Exception as e:
        logger.error(f"Error in cast command: {e}")
        await safe_reply(update, "🎣 Что-то пошло не так! Попробуйте через минуту.")

async def hook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /hook command - dramatic fishing finale"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Check if user has active position
        position = get_active_position(user_id)
        if not position:
            await safe_reply(update, f"🎣 У {username} нет заброшенной удочки! Используйте /cast чтобы начать рыбалку.")
            return
        
        # Handle mixed old/new position structure
        if len(position) >= 11 and position[9] is not None:
            # New structure with pond_id and rod_id at the end
            pond_id = position[9]   # pond_id at index 9
            rod_id = position[10]   # rod_id at index 10
            entry_price = float(position[2])  # entry_price at index 2
            entry_time = position[3]  # entry_time at index 3
        else:
            # Old structure fallback
            pond_id = 1   # Default to starter pond
            rod_id = 1    # Default to starter rod
            entry_price = float(position[2])  # entry_price at index 2
            entry_time = position[3]  # entry_time at index 3
            
        # Get pond and rod information
        from src.database.db_manager import get_rod_by_id, get_pond_by_id, get_suitable_fish, get_fish_by_id
        rod = get_rod_by_id(rod_id)
        pond = get_pond_by_id(pond_id)
        leverage = float(rod[2]) if rod else 2.0  # leverage from rod, ensure it's float
        
        # Get current price based on pond currency and calculate P&L
        base_currency = pond[3] if pond else 'ETH'  # base_currency is index 3
        current_price = get_crypto_price(base_currency)
        pnl_percent = calculate_pnl(entry_price, current_price, leverage=leverage)
        
        # Format time spent fishing
        time_fishing = format_time_fishing(entry_time)
        
        # Determine catch using new database system EARLY for parallel image generation
        user = get_user(user_id)
        user_level = user[4] if user and len(user) > 4 else 1
        
        fish_data = get_suitable_fish(pnl_percent, user_level, pond_id, rod_id)
        if fish_data:
            fish_id = fish_data[0]
            fish_name = f"{fish_data[2]} {fish_data[1]}"  # emoji + name
        else:
            # Fallback if no suitable fish found in database
            fish_name = "🐟 Неизвестная Рыба"
            fish_id = None
            fish_data = None
        
        # Start image generation in parallel with animation (non-blocking)
        import asyncio
        from src.generators.fish_card_generator import generate_fish_card_from_db
        
        async def generate_image_task():
            """Generate fish card image in background during animation"""
            try:
                logger.info(f"Starting background image generation for {fish_name}")
                if fish_data:
                    return await generate_fish_card_from_db(fish_data, pnl_percent, time_fishing)
                else:
                    logger.warning(f"No fish data found for {fish_name}, skipping image generation")
                    return None
            except Exception as img_error:
                logger.error(f"Error generating fish image: {img_error}")
                return None
        
        # Start image generation task (runs in background)
        image_task = asyncio.create_task(generate_image_task())
        
        # Get pond and rod names for display
        pond_name = pond[1] if pond else "Неизвестный водоем"
        pond_pair = pond[2] if pond else "ETH/USDT" 
        rod_name = rod[1] if rod else "Стартовая удочка"
        
        # Animate hook sequence with structured message (while image generates)
        hook_msg = await animate_hook_sequence(update, username, rod_name, pond_name, pond_pair,
                                             time_fishing, entry_price, current_price, leverage)
        if not hook_msg:
            await safe_reply(update, "🎣 Что-то пошло не так с подсеканием! Попробуйте еще раз.")
            # Cancel image task if hook animation failed
            image_task.cancel()
            return
        
        # Close position in database
        close_position(position[0], current_price, pnl_percent, fish_id)
        
        # Wait for image generation to complete (should be done by now)
        try:
            fish_card_image = await image_task
            logger.info(f"Image generation completed for {fish_name}")
        except asyncio.CancelledError:
            logger.info("Image generation was cancelled")
            fish_card_image = None
        except Exception as img_error:
            logger.error(f"Error waiting for image generation: {img_error}")
            fish_card_image = None
        
        # Send fish card or fallback to text
        await send_fish_card_or_fallback(
            update, hook_msg, fish_card_image, fish_data, fish_name,
            pnl_percent, time_fishing, entry_price, current_price, leverage
        )
        
    except Exception as e:
        logger.error(f"Error in hook command: {e}")
        await safe_reply(update, "🎣 Что-то пошло не так! Попробуйте через минуту.")

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
        
        
        # Handle mixed old/new position structure
        if len(position) >= 11 and position[9] is not None:
            # New structure with pond_id and rod_id at the end
            pond_id = position[9]   # pond_id at index 9
            rod_id = position[10]   # rod_id at index 10
            entry_price = float(position[2])  # entry_price at index 2
            entry_time = position[3]  # entry_time at index 3
        else:
            # Old structure fallback
            pond_id = 1   # Default to starter pond
            rod_id = 1    # Default to starter rod
            entry_price = float(position[2])  # entry_price at index 2
            entry_time = position[3]  # entry_time at index 3
        
        # Get pond and rod information
        from src.database.db_manager import get_pond_by_id, get_rod_by_id
        pond = get_pond_by_id(pond_id)
        rod = get_rod_by_id(rod_id)
        
        # Calculate current P&L with rod leverage and pond currency
        base_currency = pond[3] if pond else 'ETH'  # base_currency is index 3
        current_price = get_crypto_price(base_currency)
        leverage = float(rod[2]) if rod else 2.0  # leverage from rod, ensure it's float
        current_pnl = calculate_pnl(entry_price, current_price, leverage=leverage)
        
        # Format time spent fishing
        time_fishing = format_time_fishing(entry_time)
        
        # Create status message with pond and rod info
        pond_name = pond[1] if pond else "Unknown Pond"
        pond_pair = pond[2] if pond else "ETH/USDT" 
        rod_name = rod[1] if rod else "Unknown Rod"
        
        message = format_enhanced_status_message(
            username, pond_name, pond_pair, rod_name, 
            leverage, entry_price, current_pnl, time_fishing
        )
        
        await safe_reply(update, message)
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await safe_reply(update, "🎣 Что-то пошло не так! Попробуйте через минуту.")

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
                
                # Get fish data from database
                from src.database.db_manager import get_fish_by_name
                fish_data = get_fish_by_name(fish_name)
                
                if fish_data:
                    fish_card_image = await generate_fish_card_from_db(fish_data, pnl, time_fishing)
                else:
                    logger.warning(f"Fish '{fish_name}' not found in database")
                    continue
                
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
        await safe_reply(update, "🎣 Что-то пошло не так! Попробуйте через минуту.")