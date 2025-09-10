"""
Group event handlers for managing group ponds.
Handles bot addition to groups, member changes, and group pond creation.
"""

import logging
from telegram import Update, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import (
    create_or_update_group_pond, deactivate_group_pond,
    add_user_to_group, remove_user_from_group,
    update_group_member_count, get_user, create_user
)
from src.bot.animations import safe_reply

logger = logging.getLogger(__name__)

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bot being added or removed from groups"""
    try:
        chat = update.effective_chat
        new_member = update.my_chat_member.new_chat_member
        old_member = update.my_chat_member.old_chat_member
        
        # Only handle groups and supergroups
        if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
            return
        
        # Bot was added to the group
        if (new_member.status in ['member', 'administrator'] and 
            old_member.status in ['left', 'kicked']):
            
            # Get approximate member count (this may not be exact due to Telegram limitations)
            try:
                member_count = await context.bot.get_chat_member_count(chat.id)
            except Exception as e:
                logger.warning(f"Could not get member count for {chat.id}: {e}")
                member_count = 2  # Default fallback
            
            # Create group pond
            pond_id = await create_or_update_group_pond(
                chat.id, 
                chat.title or f"Group {chat.id}",
                chat.type,
                member_count
            )
            
            # Send welcome message to the group
            from src.database.db_manager import get_pond_name_and_type
            pond_name, pair_count = get_pond_name_and_type(chat.title or f"Group {chat.id}", member_count)
            
            welcome_msg = f"""🎣 <b>Fishing Bot Added!</b>

🌊 <b>New Pond Created:</b> {pond_name}
👥 <b>Members:</b> {member_count}
💰 <b>Available Trading Pairs:</b> {pair_count}

<b>🎮 How to Fish:</b>
• Use /cast to throw your fishing rod
• Use /hook to catch the fish
• Use /status to check your progress

<i>The more members in your group, the more trading pairs become available!</i>

Join this pond by using commands here in the group!"""
            
            await safe_reply(update, welcome_msg)
            
        # Bot was removed from the group
        elif (new_member.status in ['left', 'kicked'] and 
              old_member.status in ['member', 'administrator']):
            
            await deactivate_group_pond(chat.id)
            logger.info(f"Bot removed from group {chat.id} ({chat.title})")
            
    except Exception as e:
        logger.error(f"Error in my_chat_member_handler: {e}")

async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle member joins/leaves to update group pond member count"""
    try:
        chat = update.effective_chat
        
        # Only handle groups and supergroups
        if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
            return
        
        # Get current member count
        try:
            member_count = await context.bot.get_chat_member_count(chat.id)
            await update_group_member_count(chat.id, member_count)
        except Exception as e:
            logger.warning(f"Could not update member count for {chat.id}: {e}")
        
        # Handle user membership tracking
        user_id = update.chat_member.user.id
        new_member = update.chat_member.new_chat_member
        old_member = update.chat_member.old_chat_member
        
        # User joined the group
        if (new_member.status in ['member', 'administrator'] and 
            old_member.status in ['left', 'kicked', 'restricted']):
            
            # Ensure user exists in our database
            user = await get_user(user_id)
            if not user:
                username = update.chat_member.user.username or update.chat_member.user.first_name
                await create_user(user_id, username)
            
            await add_user_to_group(user_id, chat.id)
            logger.info(f"User {user_id} joined group {chat.id}")
            
        # User left the group
        elif (new_member.status in ['left', 'kicked', 'restricted'] and 
              old_member.status in ['member', 'administrator']):
            
            await remove_user_from_group(user_id, chat.id)
            logger.info(f"User {user_id} left group {chat.id}")
            
    except Exception as e:
        logger.error(f"Error in chat_member_handler: {e}")

async def group_cast_message(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str, pond_name: str):
    """Send cast announcement message to the group"""
    try:
        cast_msg = f"🎣 <b>{username}</b> cast their rod into <b>{pond_name}</b>!"
        await safe_reply(update, cast_msg)
    except Exception as e:
        logger.error(f"Error sending group cast message: {e}")

async def group_hook_message(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str, fish_name: str, pnl_percent: float):
    """Send hook result announcement to the group"""
    try:
        pnl_color = "🟢" if pnl_percent > 0 else "🔴" if pnl_percent < 0 else "⚪"
        hook_msg = f"🎣 <b>{username}</b> caught {fish_name}! {pnl_color} P&L: {pnl_percent:+.1f}%"
        await safe_reply(update, hook_msg)
    except Exception as e:
        logger.error(f"Error sending group hook message: {e}")