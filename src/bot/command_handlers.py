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
    ensure_user_has_level, give_starter_rod, get_available_ponds, get_user_rods, get_pond_by_id,
    get_rod_by_id, get_suitable_fish, get_fish_by_id
)
from src.utils.crypto_price import get_crypto_price, calculate_pnl, get_pnl_color, format_time_fishing
from src.bot.message_templates import (
    get_help_text,
    format_no_fishing_status, format_new_user_status,
    format_enhanced_status_message, get_catch_story_from_db
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
        user = await get_user(user_id)
        if not user:
            await create_user(user_id, username)
            user = await get_user(user_id)
        else:
            # Ensure existing user has level and starter rod
            await ensure_user_has_level(user_id)
            await give_starter_rod(user_id)
            user = await get_user(user_id)  # Refresh user data
        
        # Check if user has enough BAIT
        if user['bait_tokens'] <= 0:
            await safe_reply(update, "🎣 Нет токенов $BAIT! Нужно больше червячков для рыбалки 🪱")
            return
        
        # Check if user is already fishing
        active_position = await get_active_position(user_id)
        if active_position:
            await safe_reply(update, f"🎣 У {username} уже есть удочка в воде! Используйте /hook чтобы вытащить улов или /status чтобы проверить прогресс.")
            return
        
        # Use bait and get current price
        if not await use_bait(user_id):
            await safe_reply(update, "🎣 Не удалось использовать наживку. Попробуйте еще раз!")
            return
        
        user_level = user['level'] if user else 1
        
        # Get pond and price before animation to show correct starting position
        available_ponds = await get_available_ponds(user_level)
        user_rods = await get_user_rods(user_id)
        
        # Fallback logic for starter equipment
        if not user_rods:
            await give_starter_rod(user_id)
            user_rods = await get_user_rods(user_id)
            
        if not available_ponds:
            available_ponds = await get_available_ponds(1)  # Force starter pond access
            
        if not available_ponds or not user_rods:
            await safe_reply(update, "🎣 Что-то пошло не так с оборудованием! Попробуйте еще раз.")
            return
        
        # Pre-select pond and rod to get actual price
        import random
        selected_pond = random.choice(available_ponds)
        selected_rod = random.choice(user_rods)
        pond_id = selected_pond['id']
        rod_id = selected_rod['id']
        
        # Get actual crypto price before animation
        pond = await get_pond_by_id(pond_id)
        base_currency = pond['base_currency'] if pond else 'ETH'
        current_price = get_crypto_price(base_currency)
        
        # Create position IMMEDIATELY at market price (before animation)
        await create_position_with_gear(user_id, pond_id, rod_id, current_price)
        
        # Enhanced social casting animation with real price (for UX only)
        result = await animate_casting_sequence(
            update.message, username, user_level, current_price, pond_id, rod_id
        )
        
        # Log the cast action
        logger.info(f"User {username} cast with pond {pond_id}, rod {rod_id}, entry price {current_price}")
        
    except Exception as e:
        logger.error(f"Error in cast command: {e}")
        await safe_reply(update, "🎣 Что-то пошло не так! Попробуйте еще раз.")

async def hook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /hook command - pull out fish with animated sequence"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Check if user is fishing
        position = await get_active_position(user_id)
        
        if not position:
            await safe_reply(update, f"🎣 {username} не рыбачит! Используйте /cast чтобы забросить удочку.")
            return
        
        # Get pond and rod data for the position
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None
        
        # Get base currency and calculate P&L with leverage
        base_currency = pond['base_currency'] if pond else 'ETH'
        leverage = rod['leverage'] if rod else 1.5
        
        current_price = get_crypto_price(base_currency)
        entry_price = position['entry_price']
        
        # Calculate P&L with leverage
        time_fishing = format_time_fishing(position['entry_time'])
        pnl_percent = calculate_pnl(entry_price, current_price, leverage)
        
        # Get user level
        user = await get_user(user_id)
        user_level = user['level'] if user else 1
        
        # Start the hook animation IMMEDIATELY (this runs for 12.5 seconds)
        hook_task = asyncio.create_task(
            animate_hook_sequence(update.message, username)
        )
        
        # Start generating the fish card IN PARALLEL (this takes ~12 seconds)
        # The database-driven fish selection with weighted rarity system
        fish_data = await get_suitable_fish(
            pnl_percent, 
            user_level,
            position['pond_id'] if position['pond_id'] else 1,
            position['rod_id'] if position['rod_id'] else 1
        )
        
        if not fish_data:
            # Fallback to any fish within range
            logger.warning(f"No suitable fish found for PnL {pnl_percent}%, using fallback")
            fish_data = await get_suitable_fish(pnl_percent, 1, 1, 1)
        
        if fish_data:
            # Generate the catch story from database 
            catch_story = get_catch_story_from_db(fish_data)
            
            # Create complete caption using new structured format
            from src.bot.message_templates import format_fishing_complete_caption
            complete_story = format_fishing_complete_caption(
                username=username,
                catch_story=catch_story,
                rod_name=rod['name'] if rod else 'Стартовая удочка',
                leverage=leverage,
                pond_name=pond['name'] if pond else '🌊 Криптовые Воды',
                pond_pair=pond['trading_pair'] if pond else 'ETH/USDT',
                time_fishing=time_fishing,
                entry_price=entry_price,
                current_price=current_price,
                pnl_percent=pnl_percent,
                user_level=user_level
            )
            
            # Start generating the image while animation is playing
            card_task = asyncio.create_task(
                generate_fish_card_from_db(fish_data)
            )
            
            # Close position with fish ID
            await close_position(position['id'], current_price, pnl_percent, fish_data['id'])
            
            # Wait for both animation and card generation to complete
            animation_message = await hook_task
            card_image = await card_task
            
            # Send the fish card with complete story
            await send_fish_card_or_fallback(
                animation_message,
                card_image,
                complete_story
            )
        else:
            # Emergency fallback - should never happen with expanded fish database
            await hook_task  # Wait for animation to complete
            await safe_reply(update, f"🎣 {username} поймал что-то странное! P&L: {pnl_percent:+.1f}%")
            await close_position(position['id'], current_price, pnl_percent, None)
        
    except Exception as e:
        logger.error(f"Error in hook command: {e}")
        await safe_reply(update, "🎣 Ошибка при вытаскивании рыбы! Попробуйте еще раз.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show current fishing position"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Get user
        user = await get_user(user_id)
        if not user:
            await safe_reply(update, format_new_user_status(username))
            return
        
        # Get active position
        position = await get_active_position(user_id)
        
        if not position:
            bait_tokens = user['bait_tokens'] if user else 0
            await safe_reply(update, format_no_fishing_status(username, bait_tokens))
            return
        
        # Get current P&L with enhanced display
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None
        
        base_currency = pond['base_currency'] if pond else 'ETH'
        leverage = rod['leverage'] if rod else 1.5
        
        current_price = get_crypto_price(base_currency)
        entry_price = position['entry_price']
        
        pnl_percent = calculate_pnl(entry_price, current_price, leverage)
        pnl_color = get_pnl_color(pnl_percent)
        time_fishing = format_time_fishing(position['entry_time'])
        
        # Send enhanced status message
        pond_name = pond['name'] if pond else 'Неизвестный водоем'
        pond_pair = pond['trading_pair'] if pond else f'{base_currency}/USDT'
        rod_name = rod['name'] if rod else 'Неизвестная удочка'
        user_level = user['level'] if user else 1
        
        await safe_reply(update, format_enhanced_status_message(
            username, pond_name, pond_pair, rod_name, leverage, 
            entry_price, current_price, pnl_percent, time_fishing, user_level
        ))
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await safe_reply(update, "🎣 Ошибка при проверке статуса! Попробуйте еще раз.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show dynamic help from database"""
    help_text = await get_help_text()
    await safe_reply(update, help_text)

async def test_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /test_card command - for development only"""
    try:
        # Check if it's development mode (you can add your own check here)
        if update.effective_user.id not in [6919477427]:  # Replace with your dev user IDs
            await safe_reply(update, "🎣 Эта команда доступна только разработчикам!")
            return
        
        username = update.effective_user.username or update.effective_user.first_name
        await safe_reply(update, "🎨 Генерирую тестовую карточку...")
        
        # Generate test card with random fish
        import random
        pnl = random.uniform(-50, 100)
        
        # Get a random fish
        fish_data = await get_suitable_fish(pnl, 1, 9, 9)  # Use real IDs
        
        if fish_data:
            card_image = await generate_fish_card_from_db(fish_data)
            
            if card_image:
                await update.message.reply_photo(
                    photo=BytesIO(card_image),
                    caption=f"🎣 Тестовая карточка: {fish_data['emoji']} {fish_data['name']}"
                )
            else:
                await safe_reply(update, "🎣 Не удалось сгенерировать изображение")
        else:
            await safe_reply(update, "🎣 Не удалось найти подходящую рыбу")
            
    except Exception as e:
        logger.error(f"Error in test_card command: {e}")
        await safe_reply(update, f"🎣 Ошибка генерации: {str(e)}")