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
from src.bot.utils.telegram_utils import safe_reply, safe_send_message

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
            pond_name = chat.title or f"Group {chat.id}"

            welcome_msg = f"""🎣 <b>Fishing Bot Added!</b>

🌊 <b>New Pond Created:</b> {pond_name}
👥 <b>Members:</b> {member_count}

DM this bot and finish short tutorial to claim your welcome bonus!

<i>Invite more friends to grow your fishing community!</i>"""

            await safe_send_message(context, chat.id, welcome_msg)
            
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


# ===== GROUP COMMANDS AND CALLBACKS =====

async def gofishing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gofishing command - connect group pond to user account"""
    from src.database.db_manager import get_user, create_user, check_rate_limit, ensure_user_has_level, give_starter_rod, add_user_to_group, get_group_pond_by_chat_id

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat

    logger.debug(f"GOFISHING command called by user {user_id} ({username}) in chat {chat.id if chat else 'unknown'}")

    try:
        # Only works in groups - ignore in private chats
        if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
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


async def join_fishing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button click for joining fishing"""
    from src.database.db_manager import (
        get_user, create_user, check_rate_limit, ensure_user_has_level,
        give_starter_rod, add_user_to_group, get_group_pond_by_chat_id, get_pond_name_and_type
    )
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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
        # For now, use a simple count - this can be enhanced later
        joined_count = "many"
        pond_name = group_pond['name']

        # Update the welcome message with new count
        updated_msg = f"""🎣 <b>Welcome, crypto hookers!</b>

🌊 <b>Pond:</b> {pond_name}
👥 <b>Group Members:</b> {group_pond.get('member_count', 2)}
🎯 <b>Joined:</b> {joined_count}

<b>🎮 How it works:</b>
• Click "Join Fishing" below to connect this pond
• Fish using /cast in private chat with the bot
• All catches happen in private with full animations
• Share your catches with the group to earn rewards

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