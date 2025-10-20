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


def get_group_welcome_message() -> str:
    """Generate welcome message for group pond"""
    return f"""🎣 <b>This group is now Hooked!</b>

@hookedcryptobot is a fishing skin for perpetual trading on tac.build.

<b>🎮 How it works:</b>
• Click "Join Fishing"
• DM bot to start fishing:
- Cast = open a position
- Hook = close position & collect JPEG
• High Pnl - cool fish; Low Pnl - Fun Trash.

The beta runs in demo-trading mode.

<b>📊 Group Commands:</b> /leaderboard

<i>One click to start fishing! 🐟</i>"""


def get_pond_join_success_message(pond_name: str, trading_pair: str) -> str:
    """Generate success message when user joins a pond"""
    return f"""<b>You unlocked a new pond!</b>

🌊 <b>Pond:</b> {pond_name}
💱 <b>Trading Pair:</b> {trading_pair}

<b>🎮 Ready to Fish!</b>

<i>Start fishing now with /cast! 🐟</i>"""

async def show_already_member_cta(context: ContextTypes.DEFAULT_TYPE, user_id: int, pond_name: str, update: Update = None) -> None:
    """Show CTA block when user is already a member of the pond"""
    from src.bot.ui.view_controller import get_view_controller
    from src.bot.ui.blocks import BlockData, CTABlock, get_miniapp_button

    # Delete the old message if it's a callback
    if update and update.callback_query:
        try:
            await update.callback_query.delete_message()
        except Exception:
            try:
                await update.callback_query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass

    # Show cast CTA
    view = get_view_controller(context, user_id)
    await view.show_cta_block(
        chat_id=user_id,
        block_type=CTABlock,
        data=BlockData(
            header="🎣 You're already a member of <b>{pond_name}",
            body=f"Ready to cast your line?",
            buttons=[("🎣 Cast Now", "quick_cast")],
            web_app_buttons=get_miniapp_button(),
            footer="Tip: you can also use <code>/cast</code> command"
        )
    )

async def connect_user_to_pond(user_id: int, username: str, chat_id: int) -> tuple:
    """Connect user to a group pond

    Args:
        user_id: Telegram user ID
        username: User's username or first name
        chat_id: Group chat ID to connect to

    Returns:
        tuple: (success: bool, message: str, pond_name: str or None, is_new_member: bool)
    """
    from src.database.db_manager import (
        get_user, create_user, ensure_user_has_level,
        give_starter_rod, add_user_to_group, get_group_pond_by_chat_id,
        is_user_in_group_pond
    )

    try:
        # Check if user is already a member
        is_already_member = await is_user_in_group_pond(user_id, chat_id)

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
            return (False, "❌ This group doesn't have a pond yet!", None, False)

        # Generate welcome message
        welcome_text = get_pond_join_success_message(group_pond['name'], group_pond['trading_pair'])

        return (True, welcome_text, group_pond['name'], not is_already_member)

    except Exception as e:
        logger.error(f"Error connecting user {user_id} to pond {chat_id}: {e}")
        return (False, "🎣 Something went wrong! Try again.", None, False)


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
            
            # Send welcome message with Join button to the group
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            welcome_msg = get_group_welcome_message()

            # Get bot username for deep link
            bot_username = (await context.bot.get_me()).username

            keyboard = [[
                InlineKeyboardButton(
                    "🎣 Join Fishing",
                    url=f"https://t.me/{bot_username}?start=join_{chat.id}"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=chat.id,
                text=welcome_msg,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
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

async def handle_join_fishing_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    username: str,
    chat_id: int,
    from_group: bool = False
) -> None:
    """
    Common handler for joining a fishing pond (used by both /gofishing and join button)

    Args:
        update: Telegram update object
        context: Bot context
        user_id: User's Telegram ID
        username: User's username or first name
        chat_id: Group chat ID to join
        from_group: True if called from group command, False if from private chat button/link
    """
    from src.database.db_manager import check_rate_limit

    try:
        # Check rate limit
        if not await check_rate_limit(user_id):
            if from_group:
                await safe_reply(update, "⏳ Too many requests! Wait a bit before the next command.")
            else:
                # For callback queries
                if update.callback_query:
                    await update.callback_query.edit_message_text("⏳ Too many requests! Wait a bit before joining.")
                else:
                    await safe_send_message(context, user_id, "⏳ Too many requests! Wait a bit.")
            return

        # Connect user to pond
        success, message, pond_name, is_new_member = await connect_user_to_pond(user_id, username, chat_id)

        if not success:
            if from_group:
                await safe_reply(update, message)
            elif update.callback_query:
                await update.callback_query.edit_message_text(message)
            else:
                await safe_send_message(context, user_id, message)
            return

        # Handle existing member - show cast interface
        if not is_new_member:
            logger.info(f"User {username} is already in group {chat_id}, showing cast interface")

            if from_group:
                # In group context, trigger cast command directly
                from src.bot.commands.cast import cast
                await cast(update, context)
            else:
                # In private chat, show CTA block
                await show_already_member_cta(context, user_id, pond_name, update)
            return

        # Handle new member - send welcome messages
        if from_group:
            # Send confirmation to private chat
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
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
        else:
            # Private chat context (button or deep link)
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Could not send private welcome message: {e}")
                # If can't send private message, show instruction
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        f"🎣 <b>Almost ready!</b>\n\n"
                        f"Start a private chat with @{context.bot.username} first, then try again.\n\n"
                        f"<i>Click the button again after starting the chat!</i>"
                    )
                return

            # Update the group message with welcome text if it's a callback
            if update.callback_query:
                updated_msg = get_group_welcome_message()
                keyboard = [[
                    InlineKeyboardButton(
                        "🎣 Join Fishing",
                        callback_data=f"join_fishing_{chat_id}"
                    )
                ]]
                from telegram import InlineKeyboardMarkup
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.callback_query.edit_message_text(
                    text=updated_msg,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )

        logger.info(f"User {username} connected to group pond {chat_id} ({pond_name})")

    except Exception as e:
        logger.error(f"Error in handle_join_fishing_request for user {user_id}: {e}")
        logger.exception("Full join fishing error traceback:")
        if from_group:
            await safe_reply(update, "🎣 Something went wrong! Try again.")
        elif update.callback_query:
            await update.callback_query.answer("❌ Error joining fishing! Try /gofishing command instead.", show_alert=True)


async def gofishing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gofishing command - connect group pond to user account"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat

    logger.debug(f"GOFISHING command called by user {user_id} ({username}) in chat {chat.id if chat else 'unknown'}")

    # Only works in groups - ignore in private chats
    if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    # Use common handler
    await handle_join_fishing_request(
        update=update,
        context=context,
        user_id=user_id,
        username=username,
        chat_id=chat.id,
        from_group=True
    )


async def join_fishing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button click for joining fishing (legacy fallback for old messages)"""
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name

        # Parse callback data: "join_fishing_<chat_id>"
        if not query.data.startswith("join_fishing_"):
            return

        chat_id = int(query.data.split("_")[-1])

        # Use common handler
        await handle_join_fishing_request(
            update=update,
            context=context,
            user_id=user_id,
            username=username,
            chat_id=chat_id,
            from_group=False
        )

    except Exception as e:
        logger.error(f"Error in join_fishing_callback: {e}")
        if update.callback_query:
            await update.callback_query.answer("❌ Error joining fishing! Try /gofishing command instead.", show_alert=True)