"""
Group commands and callbacks for the fishing bot.
Contains group-specific commands, pond selection, and callback handlers.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, get_active_position, use_bait, create_position_with_gear,
    ensure_user_has_level, give_starter_rod, get_pond_by_id, get_group_pond_by_chat_id,
    add_user_to_group, check_rate_limit, ensure_user_has_active_rod
)
from src.utils.crypto_price import get_crypto_price
from src.bot.animations import safe_reply

logger = logging.getLogger(__name__)

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
                # Create a fake update object for the group message
                await context.bot.send_message(
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
        from src.database.db_manager import get_pond_name_and_type
        # For now, use a simple count - this can be enhanced later
        joined_count = "many"
        
        # Get pond info for updating the message
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