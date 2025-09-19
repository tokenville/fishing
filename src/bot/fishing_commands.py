"""
Fishing commands for the fishing bot.
Contains core fishing functionality: cast, hook, and status commands.
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, get_active_position, close_position, use_bait, create_position_with_gear,
    ensure_user_has_level, give_starter_rod, get_user_group_ponds, get_pond_by_id,
    get_rod_by_id, get_suitable_fish, check_rate_limit, check_hook_rate_limit,
    get_group_pond_by_chat_id, add_user_to_group
)
from src.utils.crypto_price import get_crypto_price, calculate_pnl, get_pnl_color, format_time_fishing, get_fishing_time_seconds, get_price_error_message
from src.bot.message_templates import (
    format_no_fishing_status, format_new_user_status,
    format_enhanced_status_message, get_catch_story_from_db, get_quick_fishing_message, 
    format_fishing_complete_caption
)
from src.bot.animations import (
    safe_reply, animate_hook_sequence, send_fish_card_or_fallback
)
from src.generators.fish_card_generator import generate_fish_card_from_db
from src.bot.random_messages import get_random_hook_appendix

logger = logging.getLogger(__name__)

async def cast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cast command - start fishing in private chat with pond selection only"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat
    
    logger.debug(f"CAST command called by user {user_id} ({username}) in chat {chat.id if chat else 'unknown'}")
    
    try:
        # GROUP CHAT LOGIC: Auto-redirect to private chat fishing
        if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
            # Check if user exists in database (has started bot)
            user = await get_user(user_id)
            if not user:
                # User hasn't started bot yet - send instruction message
                await safe_reply(update, 
                    f"🎣 <b>Start the bot first!</b>\n\n"
                    f"Go to private chat with @{context.bot.username} and press /start\n\n"
                    f"<i>After that, you can fish from any group pond!</i>"
                )
                return
            
            # Add user to group membership 
            await add_user_to_group(user_id, chat.id)
            
            # Get group pond
            group_pond = await get_group_pond_by_chat_id(chat.id)
            if not group_pond:
                await safe_reply(update, "❌ This group doesn't have a pond yet! The bot needs to be properly added to the group.")
                return
            
            # Start fishing in private chat directly
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎣 <b>Starting fishing from {group_pond['name']}!</b>\n\n"
                         f"<i>Casting your line now...</i>"
                )
                
                # Continue with private fishing logic but send to private chat
                # This essentially replicates the private chat logic
                from src.bot.private_fishing_helpers import start_private_fishing_from_group
                await start_private_fishing_from_group(user_id, username, group_pond['id'], context)
                return
                
            except Exception as e:
                logger.warning(f"Could not start private fishing for user {user_id}: {e}")
                await safe_reply(update, 
                    f"🎣 <b>Go to private chat to fish!</b>\n\n"
                    f"Start chat with @{context.bot.username} and use /cast there."
                )
                return
        
        # Check rate limit
        if not await check_rate_limit(user_id):
            await safe_reply(update, "⏳ Too many requests! Wait a bit before the next command.")
            return
            
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
            from src.bot.payment_commands import send_low_bait_purchase_offer
            await send_low_bait_purchase_offer(update, context)
            return
        
        # Check if user is already fishing
        active_position = await get_active_position(user_id)
        if active_position:
            await safe_reply(update, f"🎣 {username} already has a fishing rod in the water! Use /hook to pull out the catch or /status to check progress.")
            return
        
        # PRIVATE CHAT LOGIC: Show pond selection interface
        # Get user's available group ponds
        user_group_ponds = await get_user_group_ponds(user_id)
        
        if not user_group_ponds:
            # User has no group ponds available
            no_ponds_msg = f"""🎣 <b>No fishing ponds available!</b>

<b>🌊 To start fishing, you need to:</b>

1. Add this bot to a Telegram group
2. The group will automatically become a fishing pond for you and others
3. Then you can /cast here or right in the group

<b>🎮 Group Pond Benefits:</b>
• Bigger groups = More trading pairs
• Fish with friends socially
• Group announcements when you catch fish
• Group specific leaderboards and events

<i>Add me to a group to create your first pond!</i>"""
            
            await safe_reply(update, no_ponds_msg)
            return
        
        # Show pond selection buttons
        keyboard = []
        for pond in user_group_ponds[:10]:  # Limit to 10 ponds to avoid button limit
            pond_name = pond['name']
            member_info = f"({pond['member_count']} members)" if pond.get('member_count') else ""
            button_text = f"{pond_name} {member_info}"[:64]  # Telegram button text limit
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"select_pond_{pond['id']}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        selection_msg = f"""🎣 <b>Choose Your Fishing Pond</b>

<b>🌊 Available Ponds:</b>
You have access to {len(user_group_ponds)} pond(s) from your group memberships.

<i>Select a pond below to cast your fishing rod:</i>"""
        
        await update.message.reply_text(
            selection_msg,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in cast command for user {user_id}: {e}")
        logger.exception("Full cast command error traceback:")
        await safe_reply(update, "🎣 Something went wrong! Try again.")

async def hook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /hook command - pull out fish with animated sequence and rate limiting"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat
    
    logger.debug(f"HOOK command called by user {user_id} ({username})")
    
    try:
        # GROUP CHAT LOGIC: Auto-redirect to private chat hook
        if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
            # Check if user exists and is fishing
            position = await get_active_position(user_id)
            
            if not position:
                # User is not fishing - just ignore the command silently
                return
            
            # User is fishing - continue hook process in private chat
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎣 <b>Pulling in your catch...</b>\n\n"
                         f"<i>Hook animation starting!</i>"
                )
                
                # Continue with hook logic but send to private chat
                from src.bot.private_fishing_helpers import complete_private_hook_from_group
                await complete_private_hook_from_group(user_id, username, context)
                return
                
            except Exception as e:
                logger.warning(f"Could not complete private hook for user {user_id}: {e}")
                # Silently fail - don't spam group
                return
        # Check general rate limit
        if not await check_rate_limit(user_id):
            await safe_reply(update, "⏳ Too many requests! Wait a bit before the next command.")
            return
            
        # Check hook-specific rate limit (more restrictive)
        if not await check_hook_rate_limit(user_id):
            await safe_reply(update, "🎣 Easy there, fisherman! Hook attempts are limited to prevent spam.\n\n<i>Max 3 hook attempts per minute. Give the fish a chance to bite! 🐟</i>")
            return
            
        # Check if user is fishing
        position = await get_active_position(user_id)
        
        if not position:
            await safe_reply(update, f"🎣 {username} is not fishing! Use /cast to throw the fishing rod.")
            return
        
        # Get pond and rod data for the position
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None
        
        # Get base currency for price fetching
        base_currency = pond['base_currency'] if pond else 'ETH'
        leverage = rod['leverage'] if rod else 1.5
        entry_price = position['entry_price']
        
        # Pre-calculate time for quick fishing check (no API call needed)
        time_fishing = format_time_fishing(position['entry_time'])
        fishing_time_seconds = get_fishing_time_seconds(position['entry_time'])
        
        # QUICK FISHING CHECK - must be done BEFORE animation starts!
        if fishing_time_seconds < 60:
            # We need a quick price check to see if P&L is minimal
            try:
                quick_price = await get_crypto_price(base_currency)
                quick_pnl = calculate_pnl(entry_price, quick_price, leverage)
                
                if abs(quick_pnl) < 0.1:
                    quick_message = get_quick_fishing_message(fishing_time_seconds)
                    await safe_reply(update, f"{quick_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n📈 <b>P&L:</b> {quick_pnl:+.4f}%\n\n<i>Wait at least 1 minute for the market to move!</i>")
                    return
            except Exception as e:
                logger.warning(f"Quick fishing check failed, allowing hook anyway: {e}")
                # If price check fails, allow fishing to continue
        
        # Get user level
        user = await get_user(user_id)
        user_level = user['level'] if user else 1
        
        # Start PARALLEL tasks immediately - no blocking!
        # 1. Hook animation (12.5 seconds)
        hook_task = asyncio.create_task(
            animate_hook_sequence(update.message, username)
        )
        
        # 2. Price fetching with retry (may take up to 9+ seconds)
        async def fetch_price_and_calculate():
            try:
                current_price = await get_crypto_price(base_currency)
                pnl_percent = calculate_pnl(entry_price, current_price, leverage)
                return current_price, pnl_percent
            except Exception as e:
                logger.error(f"Price fetch failed in hook: {e}")
                return "ERROR", None
                
        price_task = asyncio.create_task(fetch_price_and_calculate())
        
        # Wait for price calculation to complete (runs in parallel with animation)
        current_price, pnl_percent = await price_task
        
        # Handle price fetch failure
        if current_price == "ERROR":
            # Price fetch failed - wait for animation to complete and show game error
            animation_message = await hook_task
            error_message = get_price_error_message()
            await safe_reply(update, f"{error_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n\n<i>Try pulling the hook again!</i>")
            return
        
        # Normal fishing - proceed with fish selection and generation
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
            complete_story = format_fishing_complete_caption(
                username=username,
                catch_story=catch_story,
                rod_name=rod['name'] if rod else 'Starter rod',
                leverage=leverage,
                pond_name=pond['name'] if pond else '🌊 Crypto Waters',
                pond_pair=pond['trading_pair'] if pond else 'ETH/USDT',
                time_fishing=time_fishing,
                entry_price=entry_price,
                current_price=current_price,
                pnl_percent=pnl_percent,
                user_level=user_level
            )
            
            # Start generating the image while animation continues
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
            
            # Send group notification if this was a group pond
            if pond and pond.get('pond_type') == 'group' and pond.get('chat_id') and update.effective_chat.type == Chat.PRIVATE:
                try:
                    # Send notification to the group
                    pnl_color = "🟢" if pnl_percent > 0 else "🔴" if pnl_percent < 0 else "⚪"
                    hook_appendix = get_random_hook_appendix()
                    group_notification = f"🎣 <b>{username}</b> caught {fish_data['emoji']} {fish_data['name']} from <b>{pond['name']}</b>! {pnl_color} P&L: {pnl_percent:+.1f}%{hook_appendix}"
                    
                    await context.bot.send_message(
                        chat_id=pond['chat_id'],
                        text=group_notification,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Could not send group hook notification: {e}")
        else:
            # Emergency fallback - should never happen with expanded fish database
            await hook_task  # Wait for animation to complete
            await safe_reply(update, f"🎣 {username} caught something strange! P&L: {pnl_percent:+.1f}%")
            await close_position(position['id'], current_price, pnl_percent, None)
        
    except Exception as e:
        logger.error(f"Error in hook command: {e}")
        await safe_reply(update, "🎣 Error pulling out fish! Try again.")

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
        
        current_price = await get_crypto_price(base_currency)
        entry_price = position['entry_price']
        
        pnl_percent = calculate_pnl(entry_price, current_price, leverage)
        pnl_color = get_pnl_color(pnl_percent)
        time_fishing = format_time_fishing(position['entry_time'])
        
        # Send enhanced status message
        pond_name = pond['name'] if pond else 'Unknown Pond'
        pond_pair = pond['trading_pair'] if pond else f'{base_currency}/USDT'
        rod_name = rod['name'] if rod else 'Unknown Rod'
        user_level = user['level'] if user else 1
        
        await safe_reply(update, format_enhanced_status_message(
            username, pond_name, pond_pair, rod_name, leverage, 
            entry_price, current_price, pnl_percent, time_fishing, user_level
        ))
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await safe_reply(update, "🎣 Error checking status! Try again.")