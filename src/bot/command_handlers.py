"""
Command handlers for the fishing bot.
Contains all Telegram bot command handlers (cast, hook, status, help, test_card).
"""

import os
import asyncio
import logging
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, get_active_position, close_position, use_bait, create_position_with_gear,
    ensure_user_has_level, give_starter_rod, get_available_ponds, get_user_rods, get_pond_by_id,
    get_rod_by_id, get_suitable_fish, get_fish_by_id, check_rate_limit,
    get_user_virtual_balance, get_flexible_leaderboard
)
from src.utils.crypto_price import get_crypto_price, calculate_pnl, get_pnl_color, format_time_fishing, get_fishing_time_seconds
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
    """Handle /cast command - start animated fishing with rate limiting"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
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
        
        # Use bait and get current price
        if not await use_bait(user_id):
            await safe_reply(update, "🎣 Failed to use bait. Try again!")
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
            await safe_reply(update, "🎣 Something went wrong with equipment! Try again.")
            return
        
        # Use active rod instead of random selection
        from src.database.db_manager import ensure_user_has_active_rod
        active_rod = await ensure_user_has_active_rod(user_id)
        
        if not active_rod:
            await safe_reply(update, "🎣 Failed to find active fishing rod! Try again.")
            return
            
        # Pre-select pond and use active rod
        import random
        selected_pond = random.choice(available_ponds)
        selected_rod = active_rod
        pond_id = selected_pond['id']
        rod_id = selected_rod['id']
        
        # Get actual crypto price before animation
        pond = await get_pond_by_id(pond_id)
        base_currency = pond['base_currency'] if pond else 'ETH'
        current_price = await get_crypto_price(base_currency)
        
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
        await safe_reply(update, "🎣 Something went wrong! Try again.")

async def hook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /hook command - pull out fish with animated sequence and rate limiting"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Check rate limit
        if not await check_rate_limit(user_id):
            await safe_reply(update, "⏳ Too many requests! Wait a bit before the next command.")
            return
        # Check if user is fishing
        position = await get_active_position(user_id)
        
        if not position:
            await safe_reply(update, f"🎣 {username} is not fishing! Use /cast to throw the fishing rod.")
            return
        
        # Get pond and rod data for the position
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None
        
        # Get base currency and calculate P&L with leverage
        base_currency = pond['base_currency'] if pond else 'ETH'
        leverage = rod['leverage'] if rod else 1.5
        
        current_price = await get_crypto_price(base_currency)
        entry_price = position['entry_price']
        
        # Calculate P&L with leverage
        time_fishing = format_time_fishing(position['entry_time'])
        fishing_time_seconds = get_fishing_time_seconds(position['entry_time'])
        pnl_percent = calculate_pnl(entry_price, current_price, leverage)
        
        # Check for quick fishing with minimal PnL
        if fishing_time_seconds < 60 and abs(pnl_percent) < 0.1:
            quick_message = get_quick_fishing_message(fishing_time_seconds)
            remaining_time = 60 - fishing_time_seconds
            await safe_reply(update, f"{quick_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n📈 <b>P&L:</b> {pnl_percent:+.4f}%\n\n<i>Wait at least {remaining_time} more seconds (minimum 1 minute total) for the market to move!</i>")
            return
        
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
        available_ponds = await get_available_ponds(user_level)
        rods_count = len(user_rods) if user_rods else 0
        ponds_count = len(available_ponds) if available_ponds else 0
        
        # Create personalized start message
        status_emoji = "🎣" if active_position else "🌊"
        fishing_status = "Currently fishing!" if active_position else "Ready to fish"
        
        start_message = f"""<b>🎣 Welcome, {username}!</b>

{status_emoji} <b>Your Stats:</b>

🎯 <b>Level:</b> {user_level}
⚡ <b>Experience:</b> {experience} XP
🪱 <b>$BAIT Tokens:</b> {bait_tokens}
🎣 <b>Fishing Rods:</b> {rods_count}
🌊 <b>Available Ponds:</b> {ponds_count}
📊 <b>Status:</b> {fishing_status}

<b>🎮 Quick Start:</b>
• /cast - Cast your rod
• /hook - Hook the fish
• /status - Check progress
• /leaderboard - Best anglers
• /help - Full guide

<i>Each cast costs 1 $BAIT token!</i>"""

        # Create web app button
        webapp_url = os.environ.get('WEBAPP_URL', 'http://localhost:8000/webapp')
        keyboard = [[
            InlineKeyboardButton(
                "🎮 Open Game", 
                web_app=WebAppInfo(url=webapp_url)
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(start_message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await safe_reply(update, "🎣 Welcome! Use /help for guide.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show dynamic help from database"""
    help_text = await get_help_text()
    await safe_reply(update, help_text)

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
    """Handle /leaderboard command - show top 10 players"""
    try:
        user_id = update.effective_user.id
        
        # Parse arguments for different leaderboard types
        args = context.args
        time_period = 'all'
        
        if args and len(args) > 0:
            if args[0].lower() in ['week', 'day', 'month']:
                time_period = args[0].lower()
        
        # Get leaderboard data
        data = await get_flexible_leaderboard(
            time_period=time_period,
            user_id=user_id,
            limit=10,
            include_bottom=False  # Only show top 10 for now
        )
        
        # Format title based on period
        titles = {
            'all': '📊 <b>Overall Leaderboard</b>',
            'week': '📊 <b>Weekly Leaderboard</b>',
            'day': '📊 <b>Daily Leaderboard</b>',
            'month': '📊 <b>Monthly Leaderboard</b>'
        }
        
        message = [titles.get(time_period, '📊 <b>Leaderboard</b>')]
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
            message.append('No active players yet')
        
        # User position
        if data['user_position']:
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