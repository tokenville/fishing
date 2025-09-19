"""
User commands for the fishing bot.
Contains user-oriented commands: start, help, and personal statistics.
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, get_active_position, ensure_user_has_level, 
    give_starter_rod, get_user_rods, get_user_group_ponds, get_user_virtual_balance,
    get_flexible_leaderboard, check_inheritance_status
)
from src.bot.animations import safe_reply

logger = logging.getLogger(__name__)

async def get_full_start_message(user_id: int, username: str) -> str:
    """Build the complete start message for users who have claimed inheritance"""
    try:
        # Get user statistics
        user = await get_user(user_id)
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
        
        return start_message
        
    except Exception as e:
        logger.error(f"Error building full start message for user {user_id}: {e}")
        return f"<b>🎣 Welcome to Big Catchy, {username}!</b>\n\nUse /help for game guide."

def get_inheritance_welcome_message(username: str) -> str:
    """Get welcome message for users who haven't claimed their inheritance yet"""
    return f"""<b>📜 Welcome, {username}!</b>

You have received a mysterious letter...

🏴‍☠️ <i>From your grandfather, the legendary crypto anarchist</i>

Open the app to learn about your inheritance!"""

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
        
        # Check inheritance status to determine which message to show
        has_claimed_inheritance = await check_inheritance_status(user_id)
        
        if has_claimed_inheritance:
            # Show full game guide for existing players
            start_message = await get_full_start_message(user_id, username)
        else:
            # Show inheritance welcome for new players
            start_message = get_inheritance_welcome_message(username)

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
    """Handle /help command - always show full game guide regardless of inheritance status"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    logger.debug(f"HELP command called by user {user_id} ({username})")
    
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
        
        # Always show full game guide for help command
        start_message = await get_full_start_message(user_id, username)
        
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
        
        logger.debug(f"Sending help message with webapp button to user {user_id}")
        await update.message.reply_text(start_message, reply_markup=reply_markup, parse_mode='HTML')
        logger.debug(f"Successfully sent help message to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in help command for user {user_id}: {e}")
        logger.exception("Full help command error traceback:")
        await safe_reply(update, "🎣 Welcome! Use /cast to start fishing.")

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