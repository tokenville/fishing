"""
Command handlers for the fishing bot.
Contains all Telegram bot command handlers (cast, hook, status, help, test_card).
"""

import os
import asyncio
import logging
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Chat
from telegram.ext import ContextTypes, CallbackQueryHandler

from src.database.db_manager import (
    get_user, create_user, get_active_position, close_position, use_bait, create_position_with_gear,
    ensure_user_has_level, give_starter_rod, get_user_rods, get_pond_by_id,
    get_rod_by_id, get_suitable_fish, get_fish_by_id, check_rate_limit, check_hook_rate_limit,
    get_user_virtual_balance, get_flexible_leaderboard,
    get_group_pond_by_chat_id, get_user_group_ponds, add_user_to_group
)
from src.utils.crypto_price import get_crypto_price, calculate_pnl, get_pnl_color, format_time_fishing, get_fishing_time_seconds, get_price_error_message
from src.bot.message_templates import (
    get_help_text,
    format_no_fishing_status, format_new_user_status,
    format_enhanced_status_message, get_catch_story_from_db, get_quick_fishing_message
)
from src.bot.animations import (
    safe_reply, animate_casting_sequence,
    animate_hook_sequence, send_fish_card_or_fallback
)
from src.generators.fish_card_generator import generate_fish_card_from_db

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
                await _start_private_fishing_from_group(user_id, username, group_pond['id'], context)
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
            await safe_reply(update, "🎣 No $BAIT tokens! Need more worms for fishing 🪱")
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
                await _complete_private_hook_from_group(user_id, username, context)
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
            from src.bot.message_templates import format_fishing_complete_caption
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
                    group_notification = f"🎣 <b>{username}</b> caught {fish_data['emoji']} {fish_data['name']} from <b>{pond['name']}</b>! {pnl_color} P&L: {pnl_percent:+.1f}%"
                    
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - show personalized user stats and welcome"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    logger.debug(f"START command called by user {user_id} ({username})")
    
    try:
        # Get or create user
        user = await get_user(user_id)
        if not user:
            await create_user(user_id, username)
            user = await get_user(user_id)
            await give_starter_rod(user_id)
            user = await get_user(user_id)  # Refresh after starter rod
        else:
            # Ensure existing user has level and starter rod
            await ensure_user_has_level(user_id)
            await give_starter_rod(user_id)
            user = await get_user(user_id)  # Refresh user data
        
        # Get user statistics
        user_level = user['level'] if user else 1
        bait_tokens = user['bait_tokens'] if user else 10
        experience = user['experience'] if user else 0
        
        # Check if user is currently fishing
        active_position = await get_active_position(user_id)
        
        # Get user's available equipment count
        user_rods = await get_user_rods(user_id)
        user_group_ponds = await get_user_group_ponds(user_id)
        rods_count = len(user_rods) if user_rods else 0
        ponds_count = len(user_group_ponds) if user_group_ponds else 0
        
        # Create personalized start message
        status_emoji = "🎣" if active_position else "🌊"
        fishing_status = "Currently fishing!" if active_position else "Ready to fish"
        
        start_message = f"""<b>🎣 Welcome to Big Catchy, {username}!</b>

<b>DEX trading meets fishing!</b>
Make leveraged trades and catch fish based on your performance - from trash catches to legendary sea monsters!

<b>🎮 How it works:</b>
- Add bot to any group to create fishing pond
- Cast line = open real trading position  
- Watch prices like waiting for fish bite
- Close trade = discover your catch!

<b>Your Stats:</b>
🎯 <b>Level:</b> {user_level}
🪱 <b>$BAIT Tokens:</b> {bait_tokens}
🎣 <b>Fishing Rods:</b> {rods_count}
🌊 <b>Available Ponds:</b> {ponds_count}
📊 <b>Status:</b> {fishing_status}

<b>🎣 Quick Commands:</b>
- /cast - Start fishing (make trade)
- /hook - Close position & see catch
- /leaderboard - Top fishermen
- /help - This guide

<b>🐟 Your catches depend on trading results:</b>
🗑️ Losses = Trash (soggy pizza, broken dreams)
🐟 Small profit = Tiny fish (anxiety anchovy)
🦈 Big gains = Epic fish (millionaire marlin)
🐋 Massive wins = Legends (cosmic whale)

<i>Each cast costs 1 $BAIT token!</i>"""

        # Create web app button
        webapp_url = os.environ.get('WEBAPP_URL')
        logger.debug(f"WEBAPP_URL: {webapp_url}")
        
        if not webapp_url:
            logger.error("WEBAPP_URL environment variable not set!")
            await update.message.reply_text(start_message, parse_mode='HTML')
            return
            
        try:
            keyboard = [[
                InlineKeyboardButton(
                    "🎮 Open Miniapp", 
                    web_app=WebAppInfo(url=webapp_url)
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            logger.debug(f"Created keyboard with webapp URL: {webapp_url}")
        except Exception as e:
            logger.error(f"Error creating WebApp button: {e}")
            await update.message.reply_text(start_message, parse_mode='HTML')
            return
        
        logger.debug(f"Sending start message with webapp button to user {user_id}")
        await update.message.reply_text(start_message, reply_markup=reply_markup, parse_mode='HTML')
        logger.debug(f"Successfully sent start message to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in start command for user {user_id}: {e}")
        logger.exception("Full start command error traceback:")
        await safe_reply(update, "🎣 Welcome! Use /help for guide.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show same content as /start"""
    await start_command(update, context)

async def test_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /test_card command - for development only"""
    try:
        # Check if it's development mode (you can add your own check here)
        if update.effective_user.id not in [6919477427]:  # Replace with your dev user IDs
            await safe_reply(update, "🎣 This command is only available to developers!")
            return
        
        username = update.effective_user.username or update.effective_user.first_name
        await safe_reply(update, "🎨 Generating test card...")
        
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
                    caption=f"🎣 Test card: {fish_data['emoji']} {fish_data['name']}"
                )
            else:
                await safe_reply(update, "🎣 Failed to generate image")
        else:
            await safe_reply(update, "🎣 Failed to find suitable fish")
            
    except Exception as e:
        logger.error(f"Error in test_card command: {e}")
        await safe_reply(update, f"🎣 Generation error: {str(e)}")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /leaderboard command - show group leaderboard in groups, global in private"""
    try:
        user_id = update.effective_user.id
        chat = update.effective_chat
        
        # Parse arguments for different leaderboard types
        args = context.args
        time_period = 'all'
        
        if args and len(args) > 0:
            if args[0].lower() in ['week', 'day', 'month']:
                time_period = args[0].lower()
        
        # Determine if this is a group chat or private chat
        is_group_chat = chat.type in [Chat.GROUP, Chat.SUPERGROUP]
        pond_id = None
        group_pond = None
        
        if is_group_chat:
            # GROUP CHAT: Get leaderboard for this group's pond only
            group_pond = await get_group_pond_by_chat_id(chat.id)
            if not group_pond:
                await safe_reply(update, "❌ This group doesn't have a pond yet! The bot needs to be properly added to the group.")
                return
            pond_id = group_pond['id']
        
        # Get leaderboard data (filtered by pond for groups, global for private)
        data = await get_flexible_leaderboard(
            pond_id=pond_id,  # None for private chats (global), specific pond_id for groups
            time_period=time_period,
            user_id=user_id if not is_group_chat else None,  # Only get user position in private chats
            limit=10,
            include_bottom=False  # Only show top 10 for now
        )
        
        # Format title based on chat type and period
        if is_group_chat:
            titles = {
                'all': f'📊 <b>This Group\'s Leaderboard</b>',
                'week': f'📊 <b>This Group\'s Weekly Leaderboard</b>',
                'day': f'📊 <b>This Group\'s Daily Leaderboard</b>',
                'month': f'📊 <b>This Group\'s Monthly Leaderboard</b>'
            }
        else:
            titles = {
                'all': '📊 <b>Overall Leaderboard</b>',
                'week': '📊 <b>Weekly Leaderboard</b>',
                'day': '📊 <b>Daily Leaderboard</b>',
                'month': '📊 <b>Monthly Leaderboard</b>'
            }
        
        message = [titles.get(time_period, '📊 <b>Leaderboard</b>')]
        
        # Add group pond info if in group chat
        if is_group_chat and group_pond:
            message.append(f"🌊 <b>Pond:</b> {group_pond['name']}")
        
        message.append('')
        
        # Top players
        if data['top']:
            message.append('<b>🏆 Top 10 Players:</b>')
            for i, player in enumerate(data['top'], 1):
                emoji = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
                balance_str = f"${player['balance']:,.2f}"
                win_rate = (player['avg_pnl'] > 0)
                trend = '📈' if win_rate else '📉'
                message.append(
                    f"{emoji} <b>{player['username']}</b>: {balance_str} {trend}"
                )
                message.append(f"    └ {player['total_trades']} trades, avg P&L: {player['avg_pnl']:.1f}%")
        else:
            if is_group_chat:
                message.append('No trades in this group yet')
                message.append('<i>Use /cast to start fishing!</i>')
            else:
                message.append('No active players yet')
        
        # User position (ONLY in private chats)
        if not is_group_chat and data['user_position']:
            pos = data['user_position']
            message.append('')
            message.append(f"<b>📍 Your Position:</b>")
            balance_color = '🟢' if pos['balance'] >= 10000 else '🔴'
            message.append(
                f"Rank: <b>#{pos['rank']}</b> of {data['total_players']} (top {pos['percentile']:.0f}%)"
            )
            message.append(
                f"Balance: {balance_color} <b>${pos['balance']:,.2f}</b>"
            )
            if pos['total_trades'] > 0:
                message.append(
                    f"Avg P&L: {pos['avg_pnl']:.1f}%"
                )
        
        # Help text
        message.append('')
        if is_group_chat:
            message.append('<i>This leaderboard shows only trades made in this group</i>')
        else:
            message.append('<i>Use /leaderboard week for weekly rating</i>')
        
        await update.message.reply_text(
            '\n'.join(message),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in leaderboard command: {e}")
        await safe_reply(update, "🎣 Error loading leaderboard. Try later.")

async def pnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pnl command - show user's P&L and balance"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Get user balance data
        balance_data = await get_user_virtual_balance(user_id)
        
        # Format message
        message = [f"<b>💰 P&L Statistics for {username}</b>", ""]
        
        # Balance with color indicator
        balance = balance_data['balance']
        balance_color = '🟢' if balance >= 10000 else '🔴'
        profit_loss = balance - 10000
        profit_loss_str = f"+${profit_loss:,.2f}" if profit_loss > 0 else f"-${abs(profit_loss):,.2f}"
        
        message.append(f"<b>Current Balance:</b> {balance_color} ${balance:,.2f}")
        message.append(f"<b>Total P&L:</b> {profit_loss_str} ({(profit_loss/10000)*100:.1f}%)")
        message.append("")
        
        # Trading stats
        if balance_data['total_trades'] > 0:
            win_rate = (balance_data['winning_trades'] / balance_data['total_trades']) * 100
            message.append("<b>📊 Trading Statistics:</b>")
            message.append(f"Total Trades: {balance_data['total_trades']}")
            message.append(f"Profitable: {balance_data['winning_trades']} ({win_rate:.0f}%)")
            message.append(f"Average P&L: {balance_data['avg_pnl']:.2f}%")
        else:
            message.append("<i>You have no completed trades yet</i>")
            message.append("Use /cast to start fishing!")
        
        # Position in leaderboard
        leaderboard_data = await get_flexible_leaderboard(user_id=user_id, limit=1)
        if leaderboard_data['user_position']:
            pos = leaderboard_data['user_position']
            message.append("")
            message.append(f"<b>🏆 Leaderboard Position:</b> #{pos['rank']} (top {pos['percentile']:.0f}%)")
        
        await update.message.reply_text(
            '\n'.join(message),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in pnl command: {e}")
        await safe_reply(update, "🎣 Error loading P&L. Try later.")

async def pond_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pond selection callback from private chat"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Parse callback data: "select_pond_<pond_id>"
        if not query.data.startswith("select_pond_"):
            return
            
        pond_id = int(query.data.split("_")[-1])
        
        # Get pond info
        pond = await get_pond_by_id(pond_id)
        if not pond:
            await query.edit_message_text("❌ Pond not found!")
            return
        
        # Check if user has active position
        active_position = await get_active_position(user_id)
        if active_position:
            await query.edit_message_text(f"🎣 You already have a fishing rod in the water! Use /hook to pull out the catch.")
            return
        
        # Use bait
        if not await use_bait(user_id):
            await query.edit_message_text("🎣 No $BAIT tokens! Need more worms for fishing 🪱")
            return
        
        # Get user's active rod
        from src.database.db_manager import ensure_user_has_active_rod
        active_rod = await ensure_user_has_active_rod(user_id)
        
        if not active_rod:
            await query.edit_message_text("🎣 Failed to find active fishing rod! Try again.")
            return
        
        # Get current price and create position
        base_currency = pond['base_currency']
        current_price = await get_crypto_price(base_currency)
        
        # Create position
        await create_position_with_gear(user_id, pond_id, active_rod['id'], current_price)
        
        # Send confirmation message
        await query.edit_message_text(
            f"🎣 <b>{username}</b> cast their rod into <b>{pond['name']}</b>!\n\n"
            f"🌊 <b>Pond:</b> {pond['name']}\n"
            f"🎣 <b>Rod:</b> {active_rod['name']}\n"
            f"💰 <b>Entry Price:</b> ${current_price:,.4f}\n\n"
            f"<i>Use /hook when you're ready to catch the fish!</i>"
        )
        
        # If pond is a group pond, send notification to the group
        if pond.get('pond_type') == 'group' and pond.get('chat_id'):
            try:
                from src.bot.group_handlers import group_cast_message
                # Create a fake update object for the group message
                group_message = await context.bot.send_message(
                    chat_id=pond['chat_id'],
                    text=f"🎣 <b>{username}</b> cast their rod into <b>{pond['name']}</b>",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Could not send group notification: {e}")
        
    except Exception as e:
        logger.error(f"Error in pond selection callback: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text("🎣 Error selecting pond! Try again.")

async def gofishing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gofishing command - connect group pond to user account"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat
    
    logger.debug(f"GOFISHING command called by user {user_id} ({username}) in chat {chat.id if chat else 'unknown'}")
    
    try:
        # PRIVATE CHAT RESTRICTION: Only works in groups
        if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
            await safe_reply(update, 
                f"🎣 <b>This command only works in group chats!</b>\n\n"
                f"<b>🌊 To start fishing:</b>\n"
                f"1. Add me to a Telegram group\n"
                f"2. Use /gofishing in that group\n"
                f"3. Then fish from private chat with access to that group's pond\n\n"
                f"<i>You can already fish from available group ponds using /cast!</i>"
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
        
        # Add user to group membership if not already added
        await add_user_to_group(user_id, chat.id)
        
        # Get or create group pond
        group_pond = await get_group_pond_by_chat_id(chat.id)
        if not group_pond:
            await safe_reply(update, "❌ This group doesn't have a pond yet! The bot needs to be properly added to the group.")
            return
        
        # Send confirmation to private chat instead of spamming group
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎣 <b>Welcome to {group_pond['name']}!</b>\n\n"
                     f"🌊 <b>Pond:</b> {group_pond['name']}\n"
                     f"💱 <b>Trading Pair:</b> {group_pond['trading_pair']}\n\n"
                     f"<b>🎮 Ready to Fish!</b>\n"
                     f"• Use /cast in any group with the bot to start fishing\n"
                     f"• All fishing happens here in private chat\n"
                     f"• Your catches will be announced in the group\n\n"
                     f"<i>Start fishing now with /cast! 🐟</i>",
                parse_mode='HTML'
            )
            
            # Show minimal confirmation in group (no spam)
            await safe_reply(update, f"✅ <b>{username}</b> joined the fishing community!")
            
        except Exception as e:
            logger.warning(f"Could not send private gofishing confirmation: {e}")
            # Fallback to group message if private chat fails
            await safe_reply(update, 
                f"🎣 <b>{username} joined the fishing community!</b>\n\n"
                f"Start a private chat with @{context.bot.username} to begin fishing!"
            )
        
        logger.info(f"User {username} connected to group pond {chat.id} ({group_pond['name']})")
        
    except Exception as e:
        logger.error(f"Error in gofishing command for user {user_id}: {e}")
        logger.exception("Full gofishing command error traceback:")
        await safe_reply(update, "🎣 Something went wrong! Try again.")

async def _start_private_fishing_from_group(user_id: int, username: str, pond_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start fishing process in private chat from group command"""
    try:
        # Ensure user has level and starter rod
        await ensure_user_has_level(user_id)
        await give_starter_rod(user_id)
        user = await get_user(user_id)
        
        # Check if user has enough BAIT
        if user['bait_tokens'] <= 0:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎣 No $BAIT tokens! Need more worms for fishing 🪱"
            )
            return
        
        # Check if user is already fishing
        active_position = await get_active_position(user_id)
        if active_position:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎣 {username} already has a fishing rod in the water! Use /hook to pull out the catch or /status to check progress."
            )
            return
        
        # Use bait
        if not await use_bait(user_id):
            await context.bot.send_message(
                chat_id=user_id,
                text="🎣 Failed to use bait. Try again!"
            )
            return
        
        # Get user's active rod
        from src.database.db_manager import ensure_user_has_active_rod
        active_rod = await ensure_user_has_active_rod(user_id)
        
        if not active_rod:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎣 Failed to find active fishing rod! Try again."
            )
            return
        
        # Get pond info
        pond = await get_pond_by_id(pond_id)
        if not pond:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎣 Pond not found! Try again."
            )
            return
        
        # Get current price and create position
        base_currency = pond['base_currency']
        current_price = await get_crypto_price(base_currency)
        
        # Create position
        await create_position_with_gear(user_id, pond_id, active_rod['id'], current_price)
        
        # Send success message to private chat
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎣 <b>Cast successful!</b>\n\n"
                 f"🌊 <b>Pond:</b> {pond['name']}\n"
                 f"🎣 <b>Rod:</b> {active_rod['name']}\n"
                 f"💰 <b>Entry Price:</b> ${current_price:,.4f}\n\n"
                 f"<i>Use /hook when you're ready to catch the fish!</i>",
            parse_mode='HTML'
        )
        
        # Send group notification if pond is a group pond
        if pond.get('pond_type') == 'group' and pond.get('chat_id'):
            try:
                group_message = f"🎣 <b>{username}</b> cast their rod into <b>{pond['name']}</b>"
                await context.bot.send_message(
                    chat_id=pond['chat_id'],
                    text=group_message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Could not send group cast notification: {e}")
        
        logger.info(f"User {username} started fishing from group in private chat, pond {pond_id}")
        
    except Exception as e:
        logger.error(f"Error in _start_private_fishing_from_group for user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="🎣 Something went wrong! Try /cast again."
        )

async def _complete_private_hook_from_group(user_id: int, username: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Complete hook process in private chat from group command"""
    try:
        # Get active position
        position = await get_active_position(user_id)
        if not position:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎣 {username} is not fishing! Use /cast to throw the fishing rod."
            )
            return
        
        # Check hook rate limit
        if not await check_hook_rate_limit(user_id):
            await context.bot.send_message(
                chat_id=user_id,
                text="🎣 Easy there, fisherman! Hook attempts are limited to prevent spam.\n\n<i>Max 3 hook attempts per minute. Give the fish a chance to bite! 🐟</i>",
                parse_mode='HTML'
            )
            return
        
        # Get pond and rod data for the position
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None
        
        # Get base currency for price fetching
        base_currency = pond['base_currency'] if pond else 'ETH'
        leverage = rod['leverage'] if rod else 1.5
        entry_price = position['entry_price']
        
        # Pre-calculate time for quick fishing check
        time_fishing = format_time_fishing(position['entry_time'])
        fishing_time_seconds = get_fishing_time_seconds(position['entry_time'])
        
        # QUICK FISHING CHECK - must be done BEFORE animation starts!
        if fishing_time_seconds < 60:
            try:
                quick_price = await get_crypto_price(base_currency)
                quick_pnl = calculate_pnl(entry_price, quick_price, leverage)
                
                if abs(quick_pnl) < 0.1:
                    quick_message = get_quick_fishing_message(fishing_time_seconds)
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"{quick_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n📈 <b>P&L:</b> {quick_pnl:+.4f}%\n\n<i>Wait at least 1 minute for the market to move!</i>",
                        parse_mode='HTML'
                    )
                    return
            except Exception as e:
                logger.warning(f"Quick fishing check failed, allowing hook anyway: {e}")
        
        # Get user level
        user = await get_user(user_id)
        user_level = user['level'] if user else 1
        
        # Create a mock message for animations (we'll send to private chat instead)
        class MockMessage:
            def __init__(self, chat_id):
                self.chat_id = chat_id
                self.message_id = None
            
            async def edit_text(self, text, parse_mode=None, reply_markup=None):
                # Send as new message instead of editing
                await context.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=parse_mode
                )
            
            async def edit_caption(self, caption, parse_mode=None):
                await context.bot.send_message(
                    chat_id=self.chat_id,
                    text=caption,
                    parse_mode=parse_mode
                )
        
        mock_message = MockMessage(user_id)
        
        # Start PARALLEL tasks immediately - no blocking!
        # 1. Hook animation (simplified for private chat)
        hook_task = asyncio.create_task(
            _private_hook_animation(context, user_id, username)
        )
        
        # 2. Price fetching with retry
        async def fetch_price_and_calculate():
            try:
                current_price = await get_crypto_price(base_currency)
                pnl_percent = calculate_pnl(entry_price, current_price, leverage)
                return current_price, pnl_percent
            except Exception as e:
                logger.error(f"Price fetch failed in private hook: {e}")
                return "ERROR", None
                
        price_task = asyncio.create_task(fetch_price_and_calculate())
        
        # Wait for price calculation to complete (runs in parallel with animation)
        current_price, pnl_percent = await price_task
        
        # Handle price fetch failure
        if current_price == "ERROR":
            await hook_task  # Wait for animation to complete
            error_message = get_price_error_message()
            await context.bot.send_message(
                chat_id=user_id,
                text=f"{error_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n\n<i>Try pulling the hook again!</i>",
                parse_mode='HTML'
            )
            return
        
        # Normal fishing - proceed with fish selection and generation
        fish_data = await get_suitable_fish(
            pnl_percent, 
            user_level,
            position['pond_id'] if position['pond_id'] else 1,
            position['rod_id'] if position['rod_id'] else 1
        )
        
        if not fish_data:
            logger.warning(f"No suitable fish found for PnL {pnl_percent}%, using fallback")
            fish_data = await get_suitable_fish(pnl_percent, 1, 1, 1)
        
        if fish_data:
            # Generate the catch story from database 
            catch_story = get_catch_story_from_db(fish_data)
            
            # Create complete caption using structured format
            from src.bot.message_templates import format_fishing_complete_caption
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
            await hook_task
            card_image = await card_task
            
            # Send the fish card to private chat
            if card_image:
                try:
                    from io import BytesIO
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=BytesIO(card_image),
                        caption=complete_story,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Failed to send fish card to private chat: {e}")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=complete_story,
                        parse_mode='HTML'
                    )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=complete_story,
                    parse_mode='HTML'
                )
            
            # Send group notification if this was a group pond
            if pond and pond.get('pond_type') == 'group' and pond.get('chat_id'):
                try:
                    pnl_color = "🟢" if pnl_percent > 0 else "🔴" if pnl_percent < 0 else "⚪"
                    group_notification = f"🎣 <b>{username}</b> caught {fish_data['emoji']} {fish_data['name']} from <b>{pond['name']}</b>! {pnl_color} P&L: {pnl_percent:+.1f}%"
                    
                    await context.bot.send_message(
                        chat_id=pond['chat_id'],
                        text=group_notification,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Could not send group hook notification: {e}")
        else:
            # Emergency fallback
            await hook_task
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎣 {username} caught something strange! P&L: {pnl_percent:+.1f}%"
            )
            await close_position(position['id'], current_price, pnl_percent, None)
        
        logger.info(f"User {username} completed hook from group in private chat")
        
    except Exception as e:
        logger.error(f"Error in _complete_private_hook_from_group for user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="🎣 Error pulling out fish! Try /hook again."
        )

async def _private_hook_animation(context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str):
    """Simplified hook animation for private chat"""
    try:
        # Simple text-based animation for private chat
        animation_steps = [
            f"🎣 <b>{username}</b> is pulling the line...",
            f"🌊 Something's biting! <b>{username}</b> fights the catch...",
            f"⚡ The line is tense! <b>{username}</b> reels it in...",
            f"🐟 Almost got it! <b>{username}</b> pulls harder...",
            f"🎯 <b>Success!</b> <b>{username}</b> caught something!"
        ]
        
        for i, step in enumerate(animation_steps):
            await context.bot.send_message(
                chat_id=user_id,
                text=step,
                parse_mode='HTML'
            )
            if i < len(animation_steps) - 1:  # Don't sleep after the last step
                await asyncio.sleep(2.5)  # Match original animation timing
                
    except Exception as e:
        logger.warning(f"Error in private hook animation: {e}")

async def join_fishing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button click for joining fishing"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Parse callback data: "join_fishing_<chat_id>"
        if not query.data.startswith("join_fishing_"):
            return
            
        chat_id = int(query.data.split("_")[-1])
        
        # Check rate limit
        if not await check_rate_limit(user_id):
            await query.edit_message_text("⏳ Too many requests! Wait a bit before joining.")
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
        
        # Add user to group membership
        await add_user_to_group(user_id, chat_id)
        
        # Get group pond
        group_pond = await get_group_pond_by_chat_id(chat_id)
        if not group_pond:
            await query.edit_message_text("❌ This group doesn't have a pond yet!")
            return
        
        # Send confirmation to private chat instead of group
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎣 <b>Welcome to {group_pond['name']}!</b>\n\n"
                     f"🌊 <b>Pond:</b> {group_pond['name']}\n"
                     f"💱 <b>Trading Pair:</b> {group_pond['trading_pair']}\n\n"
                     f"<b>🎮 Ready to Fish!</b>\n"
                     f"• Use /cast in any group with the bot to start fishing\n"
                     f"• All fishing happens here in private chat\n"
                     f"• Your catches will be announced in the group\n\n"
                     f"<i>Start fishing now with /cast! 🐟</i>",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.warning(f"Could not send private welcome message: {e}")
            # If can't send private message, show instruction
            await query.edit_message_text(
                f"🎣 <b>Almost ready!</b>\n\n"
                f"Start a private chat with @{context.bot.username} first, then try again.\n\n"
                f"<i>Click the button again after starting the chat!</i>"
            )
            return
        
        # Update the group message with new joined count
        joined_count = await get_group_joined_count(chat_id)
        
        # Get pond info for updating the message
        from src.database.db_manager import get_pond_name_and_type
        pond_name, pair_count = get_pond_name_and_type(group_pond['name'], group_pond.get('member_count', 2))
        
        # Update the welcome message with new count
        updated_msg = f"""🎣 <b>Welcome to Big Catchy Fishing!</b>

🌊 <b>Pond:</b> {pond_name}
👥 <b>Group Members:</b> {group_pond.get('member_count', 2)}
💰 <b>Trading Pairs:</b> {pair_count}
🎯 <b>Joined:</b> {joined_count}

<b>🎮 How it works:</b>
• Click "Join Fishing" below to connect this pond
• Fish using /cast in any group with the bot
• All catches happen in private chat with full animations
• Results are announced here for everyone to see

<b>📊 Group Commands:</b> /leaderboard

<i>One click to start fishing! 🐟</i>"""

        # Keep the same button for other users
        keyboard = [[
            InlineKeyboardButton(
                "🎣 Join Fishing", 
                callback_data=f"join_fishing_{chat_id}"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=updated_msg,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        logger.info(f"User {username} joined fishing pond {chat_id} via inline button")
        
    except Exception as e:
        logger.error(f"Error in join_fishing_callback: {e}")
        if update.callback_query:
            await update.callback_query.answer("❌ Error joining fishing! Try /gofishing command instead.", show_alert=True)