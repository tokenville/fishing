"""
Leaderboard and testing commands for the fishing bot.
Contains commands for rankings, statistics, and development testing.
"""

import random
import logging
from io import BytesIO
from telegram import Update, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_flexible_leaderboard, get_group_pond_by_chat_id, get_suitable_fish
)
from src.bot.utils.telegram_utils import safe_reply
from src.generators.fish_card_generator import generate_fish_card_from_db

logger = logging.getLogger(__name__)

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