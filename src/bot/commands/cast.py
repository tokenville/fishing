"""
/cast command - Start fishing operation
"""

import logging
from typing import Optional
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, get_active_position, ensure_user_has_level, give_starter_rod,
    get_user_group_ponds, get_group_pond_by_chat_id, add_user_to_group,
    check_rate_limit, can_use_free_cast, is_onboarding_completed
)
from src.bot.utils.telegram_utils import safe_reply
from src.bot.features.onboarding import onboarding_handler

logger = logging.getLogger(__name__)


async def _resolve_onboarding_pond_id(
    context: ContextTypes.DEFAULT_TYPE,
) -> Optional[int]:
    """Best-effort lookup for the onboarding pond id using env configuration."""
    # Prefer explicit chat id if provided via env
    chat_id = getattr(onboarding_handler, "group_chat_id", None)
    if chat_id:
        pond = await get_group_pond_by_chat_id(chat_id)
        if pond:
            return pond["id"]
        logger.warning(
            "Configured onboarding chat id %s has no active pond entry", chat_id
        )

    invite_link = getattr(onboarding_handler, "group_invite_link", None)
    if not invite_link:
        return None

    slug = urlparse(invite_link).path.strip("/")
    if not slug:
        logger.warning("Invite URL %s contains no path segment for onboarding pond", invite_link)
        return None

    # Attempt to treat slug as numeric chat id first
    numeric_slug = slug.replace("-", "")
    if numeric_slug.isdigit():
        numeric_id = int(slug)
        pond = await get_group_pond_by_chat_id(numeric_id)
        if pond:
            return pond["id"]
        logger.info(
            "No pond found for numeric chat id %s parsed from invite URL", numeric_id
        )

    username = slug if slug.startswith("@") else f"@{slug}"
    try:
        chat = await context.bot.get_chat(username)
    except TelegramError as exc:
        logger.warning("Failed to resolve onboarding chat %s: %s", username, exc)
        return None

    pond = await get_group_pond_by_chat_id(chat.id)
    if pond:
        return pond["id"]

    logger.info(
        "Onboarding chat %s resolved to id %s but no pond entry exists; ensure group pond initialization runs",
        username,
        chat.id,
    )
    return None


async def cast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cast command - start fishing in private chat with pond selection only"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat
    message = update.effective_message
    if not message and getattr(update, "callback_query", None):
        message = update.callback_query.message

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
                from src.bot.features.fishing_flow import start_private_fishing_from_group
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

        # Check if user can use free tutorial cast
        can_use_free = await can_use_free_cast(user_id)

        # Check if user has enough BAIT (skip check for free tutorial cast)
        if not can_use_free and user['bait_tokens'] <= 0:
            from src.bot.commands.payments import send_low_bait_purchase_offer
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

        # Special case: If user is in onboarding and has no ponds, use default pond
        if not user_group_ponds:
            onboarding_completed = await is_onboarding_completed(user_id)
            if not onboarding_completed:
                logger.info("User %s onboarding cast requested — resolving tutorial pond", user_id)
                try:
                    from src.bot.features.fishing_flow import start_private_fishing_from_group

                    onboarding_pond_id = await _resolve_onboarding_pond_id(context)
                    if onboarding_pond_id:
                        await start_private_fishing_from_group(
                            user_id,
                            username,
                            onboarding_pond_id,
                            context,
                        )
                        return
                    logger.warning(
                        "Onboarding pond could not be resolved for user %s; falling back to no-pond message",
                        user_id,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to start onboarding fishing for user %s: %s",
                        user_id,
                        e,
                    )
                    await safe_reply(update, "🎣 Something went wrong! Try again.")
                    return

            # User not in onboarding and has no group ponds
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

        if message:
            await message.reply_text(
                selection_msg,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=selection_msg,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error in cast command for user {user_id}: {e}")
        logger.exception("Full cast command error traceback:")
        await safe_reply(update, "🎣 Something went wrong! Try again.")
