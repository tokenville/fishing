"""
Group commands and callbacks for the fishing bot.
Contains group-specific commands, pond selection, and callback handlers.
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, get_active_position, use_bait, create_position_with_gear,
    ensure_user_has_level, give_starter_rod, get_pond_by_id, get_group_pond_by_chat_id,
    add_user_to_group, check_rate_limit, ensure_user_has_active_rod,
    can_use_free_cast, mark_onboarding_action, award_group_bonus, award_first_cast_reward
)
from src.bot.onboarding_handler import (
    onboarding_handler,
    send_onboarding_message,
    skip_onboarding,
    handle_onboarding_command,
)
from src.bot.fishing_commands import cast, hook
from src.utils.crypto_price import get_crypto_price
from src.bot.animations import safe_reply
from src.bot.random_messages import get_random_cast_appendix

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

        user = await get_user(user_id)
        user_level = user['level'] if user else 1

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
        
        # Check if user can use free tutorial cast
        can_use_free = await can_use_free_cast(user_id)
        
        # Use bait (skip for free tutorial cast)
        if can_use_free:
            # Mark that user used their free cast
            await mark_onboarding_action(user_id, 'first_cast')
        else:
            # Normal bait usage
            if not await use_bait(user_id):
                await query.edit_message_text("🎣 No $BAIT tokens! Use /buy command to purchase more 🪱")
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
        
        await query.edit_message_text(
            f"🎣 <b>{username}</b> cast their rod into <b>{pond['name']}!</b>\n\n"
            f"🌊 <b>Pond:</b> {pond['name']}\n"
            f"🎣 <b>Rod:</b> {active_rod['name']}\n"
            f"💰 <b>Entry Price:</b> ${current_price:,.4f}\n\n"
            f"<i>Use /hook when you're ready to catch the fish!</i>"
        )

        # Trigger casting animation in parallel
        try:
            from src.bot.animations import animate_casting_sequence
            await animate_casting_sequence(
                query.message,
                username,
                user_level,
                current_price,
                pond_id=pond['id'],
                rod_id=active_rod['id']
            )
        except Exception as anim_err:
            logger.warning(f"Cast animation failed for user {user_id}: {anim_err}")

        # If pond is a group pond, send notification to the group
        if pond.get('pond_type') == 'group' and pond.get('chat_id'):
            try:
                # Create a fake update object for the group message
                cast_appendix = get_random_cast_appendix()
                await context.bot.send_message(
                    chat_id=pond['chat_id'],
                    text=f"🎣 <b>{username}</b> cast their rod into <b>{pond['name']}</b>.{cast_appendix}",
                    parse_mode='HTML',
                    disable_notification=True
                )
            except Exception as e:
                logger.warning(f"Could not send group notification: {e}")

        # Check if user gets first cast reward (gear unlock)
        cast_reward_message = await award_first_cast_reward(user_id)

        # Handle onboarding progression if applicable
        onboarding_result = await handle_onboarding_command(user_id, '/cast')
        if isinstance(onboarding_result, dict) and onboarding_result.get('send_message'):
            # In onboarding - show gear claim button if applicable
            if cast_reward_message:
                # Store reward message for later display
                context.user_data['pending_gear_reward'] = cast_reward_message
                # Store onboarding result to show after gear claim
                context.user_data['pending_onboarding_message'] = onboarding_result['send_message']
                context.user_data['pending_onboarding_markup'] = onboarding_result.get('reply_markup')

                gear_keyboard = [[InlineKeyboardButton("🎣 Claim gear", callback_data="claim_gear_reward")]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🎁 <b>New gear unlocked!</b>\n\nClaim your starter rods now.",
                    reply_markup=InlineKeyboardMarkup(gear_keyboard),
                    parse_mode='HTML'
                )
            else:
                # No gear reward - show tutorial message directly
                await asyncio.sleep(3)
                sent_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=onboarding_result['send_message'],
                    reply_markup=onboarding_result.get('reply_markup'),
                    parse_mode='HTML'
                )
                # Store message ID for later deletion
                context.user_data['tutorial_message_id'] = sent_message.message_id
        else:
            # Not in onboarding - show regular reward
            if cast_reward_message:
                # Store reward message for later display
                context.user_data['pending_gear_reward'] = cast_reward_message

                gear_keyboard = [[InlineKeyboardButton("🎣 Claim gear", callback_data="claim_gear_reward")]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🎁 <b>New gear unlocked!</b>\n\nClaim your starter rods now.",
                    reply_markup=InlineKeyboardMarkup(gear_keyboard),
                    parse_mode='HTML'
                )

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

async def onboarding_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the streamlined onboarding flow."""
    query = update.callback_query
    try:
        await query.answer()
        user_id = update.effective_user.id

        current_step = await onboarding_handler.get_user_current_step(user_id)
        if current_step == onboarding_handler.STEP_COMPLETED:
            await query.answer("Tutorial already completed.", show_alert=True)
            return

        # Delete the intro message
        if query.message:
            try:
                await query.message.delete()
            except Exception as del_err:
                logger.warning(f"Could not delete intro message: {del_err}")

        await onboarding_handler.advance_step(user_id, onboarding_handler.STEP_JOIN_GROUP)
        await send_onboarding_message(update, context, user_id, onboarding_handler.STEP_JOIN_GROUP)
        logger.info("User %s started onboarding", user_id)
    except Exception as exc:
        logger.error("Error in onboarding_start_callback: %s", exc)
        await query.answer("❌ Failed to start tutorial. Try again.", show_alert=True)


async def onboarding_skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Skip onboarding and jump straight to completion."""
    query = update.callback_query
    try:
        await query.answer()
        user_id = update.effective_user.id

        current_step = await onboarding_handler.get_user_current_step(user_id)
        if current_step == onboarding_handler.STEP_COMPLETED:
            await query.answer("Tutorial already completed.", show_alert=True)
            return

        # Delete the intro message
        if query.message:
            try:
                await query.message.delete()
            except Exception as del_err:
                logger.warning(f"Could not delete intro message: {del_err}")

        await skip_onboarding(user_id)
        await send_onboarding_message(update, context, user_id, onboarding_handler.STEP_COMPLETED)
        logger.info("User %s skipped onboarding via button", user_id)
    except Exception as exc:
        logger.error("Error in onboarding_skip_callback: %s", exc)
        await query.answer("❌ Failed to skip tutorial. Try again.", show_alert=True)


async def onboarding_claim_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Grant BAIT bonus for joining the primary group and continue to next step."""
    query = update.callback_query
    try:
        user_id = update.effective_user.id
        current_step = await onboarding_handler.get_user_current_step(user_id)
        if current_step not in (
            onboarding_handler.STEP_JOIN_GROUP,
            onboarding_handler.STEP_CAST,
        ):
            await query.answer("This reward is not available right now.", show_alert=True)
            return
        reward_message = await award_group_bonus(user_id)

        # Show alert first
        await query.answer(reward_message, show_alert=True)

        # Delete the join group message after alert is shown
        # (user will see deletion after closing alert)
        if query.message:
            try:
                await query.message.delete()
            except Exception as del_err:
                logger.warning(f"Could not delete join group message: {del_err}")

        primary_chat_id = getattr(onboarding_handler, 'group_chat_id', None)
        if primary_chat_id:
            try:
                await add_user_to_group(user_id, primary_chat_id)
                primary_pond = await get_group_pond_by_chat_id(primary_chat_id)
                if primary_pond:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🌊 <b>{primary_pond['name']}</b> added to your ponds!\n"
                            "You can now select it when casting."
                        ),
                        parse_mode='HTML'
                    )
            except Exception as add_err:
                logger.warning("Failed to register onboarding group for user %s: %s", user_id, add_err)

        await onboarding_handler.advance_step(user_id, onboarding_handler.STEP_CAST)
        await send_onboarding_message(update, context, user_id, onboarding_handler.STEP_CAST)
    except Exception as exc:
        logger.error("Error in onboarding_claim_bonus_callback: %s", exc)
        await query.answer("❌ Failed to grant bonus. Try again later.", show_alert=True)


async def claim_gear_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the gear reward in alert modal and then show next onboarding step."""
    query = update.callback_query
    try:
        user_id = update.effective_user.id

        # Get pending gear reward from context
        gear_reward_message = context.user_data.get('pending_gear_reward')

        if gear_reward_message:
            # Show reward in alert
            await query.answer(gear_reward_message, show_alert=True)
            # Clear the pending reward
            context.user_data.pop('pending_gear_reward', None)

            # Delete the gear claim message
            if query.message:
                try:
                    await query.message.delete()
                except Exception as del_err:
                    logger.warning(f"Could not delete gear claim message: {del_err}")

            # Check if there's a pending onboarding message to show
            pending_message = context.user_data.get('pending_onboarding_message')
            pending_markup = context.user_data.get('pending_onboarding_markup')

            if pending_message:
                # Wait 2 seconds before showing next step
                await asyncio.sleep(2)

                # Show the next onboarding step
                sent_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=pending_message,
                    reply_markup=pending_markup,
                    parse_mode='HTML'
                )
                # Store message ID for later deletion
                context.user_data['tutorial_message_id'] = sent_message.message_id

                # Clear pending onboarding data
                context.user_data.pop('pending_onboarding_message', None)
                context.user_data.pop('pending_onboarding_markup', None)
        else:
            await query.answer("🎣 Gear already claimed!", show_alert=True)
    except Exception as exc:
        logger.error("Error in claim_gear_reward_callback: %s", exc)
        await query.answer("❌ Failed to show gear info.", show_alert=True)


async def onboarding_claim_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the first catch reward in alert modal and complete tutorial."""
    query = update.callback_query
    try:
        user_id = update.effective_user.id

        # Get pending reward from context
        reward_message = context.user_data.get('pending_reward')

        if reward_message:
            # Show reward in alert (this is the only query.answer we need)
            await query.answer(reward_message, show_alert=True)
            # Clear the pending reward
            context.user_data.pop('pending_reward', None)

            # Delete the congrats message
            if query.message:
                try:
                    await query.message.delete()
                except Exception as del_err:
                    logger.warning(f"Could not delete congrats message: {del_err}")

            # Wait 2 seconds before showing final message
            await asyncio.sleep(2)

            # Mark onboarding as complete
            from src.bot.onboarding_handler import onboarding_handler, complete_onboarding
            await complete_onboarding(user_id)

            # Send final completion message
            final_message, final_keyboard = await onboarding_handler._build_completion_step(user_id)
            final_markup = InlineKeyboardMarkup(final_keyboard) if final_keyboard else None
            await context.bot.send_message(
                chat_id=user_id,
                text=final_message,
                reply_markup=final_markup,
                parse_mode='HTML'
            )
        else:
            await query.answer("🏆 Reward already claimed!", show_alert=True)
    except Exception as exc:
        logger.error("Error in onboarding_claim_reward_callback: %s", exc)
        await query.answer("❌ Failed to show reward.", show_alert=True)


async def onboarding_continue_cast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Move to the cast instruction step without claiming the bonus."""
    query = update.callback_query
    try:
        await query.answer()
        user_id = update.effective_user.id

        current_step = await onboarding_handler.get_user_current_step(user_id)
        if current_step == onboarding_handler.STEP_COMPLETED:
            await query.answer("Tutorial already completed.", show_alert=True)
            return

        await onboarding_handler.advance_step(user_id, onboarding_handler.STEP_CAST)
        await send_onboarding_message(update, context, user_id, onboarding_handler.STEP_CAST)
    except Exception as exc:
        logger.error("Error in onboarding_continue_cast_callback: %s", exc)
        await query.answer("❌ Failed to proceed to cast.", show_alert=True)


async def onboarding_send_cast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger cast flow directly from onboarding button."""
    query = update.callback_query
    try:
        await query.answer()
        user_id = update.effective_user.id

        # Delete the tutorial message
        if query.message:
            try:
                await query.message.delete()
            except Exception as del_err:
                logger.warning(f"Could not delete tutorial message: {del_err}")

        await cast(update, context)
    except Exception as exc:
        logger.error("Error in onboarding_send_cast_callback: %s", exc)
        await query.answer("❌ Failed to send command.", show_alert=True)


async def onboarding_send_hook_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger hook flow directly from onboarding button."""
    query = update.callback_query
    try:
        await query.answer()
        user_id = update.effective_user.id

        # Delete the tutorial message
        if query.message:
            try:
                await query.message.delete()
            except Exception as del_err:
                logger.warning(f"Could not delete tutorial message: {del_err}")

        await hook(update, context)
    except Exception as exc:
        logger.error("Error in onboarding_send_hook_callback: %s", exc)
        await query.answer("❌ Failed to send command.", show_alert=True)
