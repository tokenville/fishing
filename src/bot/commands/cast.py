"""
/cast command - Start fishing operation
"""

import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

from telegram import Update, Chat
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, get_active_position, ensure_user_has_level, give_starter_rod,
    get_user_group_ponds, get_group_pond_by_chat_id,
    check_rate_limit, can_use_free_cast, is_onboarding_completed,
    ensure_user_has_active_rod, use_bait, create_position_with_gear, get_pond_by_id,
    mark_onboarding_action, award_first_cast_reward
)
from src.bot.utils.telegram_utils import safe_reply
from src.bot.features.onboarding import onboarding_handler, handle_onboarding_command
from src.utils.crypto_price import get_crypto_price
from src.bot.ui.blocks import get_miniapp_button

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

    # Ignore in group chats
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    logger.debug(f"CAST command called by user {user_id} ({username}) in chat {chat.id if chat else 'unknown'}")

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
            # Show error block with action buttons
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ Already Fishing!",
                    body=f"{username}, you already have a rod in the water. Complete your current catch first!",
                    buttons=[
                        ("🪝 Hook Now", "quick_hook"),
                        ("📊 Check Status", "show_status")
                    ]
                )
            )
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
                    onboarding_pond_id = await _resolve_onboarding_pond_id(context)
                    if onboarding_pond_id:
                        await _start_cast_for_pond(
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
2. The group will automatically become a fishing pond
3. Send <code>/gofishing</code> in your group to start fishing there.

<b>🎮 Group Pond Benefits:</b>
• Fish with friends socially
• Share your catches to get BAITs back
• Group-specific leaderboards
• Build your fishing community

<i>Add me to a group to create your first pond!</i>"""

            await safe_reply(update, no_ponds_msg)
            return

        # Show pond selection using CTA block system
        from src.bot.ui.view_controller import get_view_controller
        from src.bot.ui.blocks import BlockData, CTABlock

        # Build pond selection buttons
        pond_buttons = []
        for pond in user_group_ponds[:10]:  # Limit to 10 ponds to avoid button limit
            pond_name = pond['name']
            member_info = f"({pond['member_count']} members)" if pond.get('member_count') else ""
            button_text = f"{pond_name} {member_info}"[:64]  # Telegram button text limit
            pond_buttons.append((button_text, f"select_pond_{pond['id']}"))

        view = get_view_controller(context, user_id)
        await view.show_cta_block(
            chat_id=user_id,
            block_type=CTABlock,
            data=BlockData(
                header="🎣 Choose Your Fishing Pond",
                body=f"You have access to {len(user_group_ponds)} pond(s) from your group memberships.",
                buttons=pond_buttons,
                footer="We will NOT notify group members."
            )
        )

    except Exception as e:
        logger.error(f"Error in cast command for user {user_id}: {e}")
        logger.exception("Full cast command error traceback:")
        await safe_reply(update, "🎣 Something went wrong! Try again.")


async def _start_cast_for_pond(
    user_id: int,
    username: str,
    pond_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Run the full cast sequence for a selected pond in private chat."""

    try:
        # Ensure user has level and starter rod
        await ensure_user_has_level(user_id)
        await give_starter_rod(user_id)
        user = await get_user(user_id)

        # Check if user has enough BAIT
        if user['bait_tokens'] <= 0:
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ No BAIT Tokens!",
                    body="You need BAIT tokens to cast your fishing rod.",
                    buttons=[("🛒 Buy BAIT", "quick_buy")],
                    web_app_buttons=get_miniapp_button(),
                    footer="Each cast costs 1 🪱 BAIT token"
                )
            )
            return

        # Check if user is already fishing
        active_position = await get_active_position(user_id)
        if active_position:
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ Already Fishing!",
                    body=f"{username}, you already have a rod in the water. Complete your current catch first!",
                    buttons=[
                        ("🪝 Hook Now", "quick_hook"),
                        ("📊 Check Status", "show_status")
                    ]
                )
            )
            return

        # Check if user can use free tutorial cast
        can_use_free = await can_use_free_cast(user_id)

        # Use bait (skip for free tutorial cast)
        if can_use_free:
            # Mark that user used their free cast
            await mark_onboarding_action(user_id, 'first_cast')
        else:
            if not await use_bait(user_id):
                from src.bot.ui.view_controller import get_view_controller
                from src.bot.ui.blocks import BlockData, ErrorBlock

                view = get_view_controller(context, user_id)
                await view.show_cta_block(
                    chat_id=user_id,
                    block_type=ErrorBlock,
                    data=BlockData(
                        header="❌ Failed to Use BAIT",
                        body="Something went wrong while using your BAIT token. Please try again!",
                        buttons=[("🎣 Try Again", "quick_cast")],
                    web_app_buttons=get_miniapp_button()
                    )
                )
                return

        # Get user's active rod
        active_rod = await ensure_user_has_active_rod(user_id)

        if not active_rod:
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ No Active Rod",
                    body="Failed to find your active fishing rod. This shouldn't happen!",
                    buttons=[("📊 Check Status", "show_status")],
                    web_app_buttons=get_miniapp_button()
                )
            )
            return

        # Get pond info
        pond = await get_pond_by_id(pond_id)
        if not pond:
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ Pond Not Found",
                    body="The selected fishing pond could not be found. Please try selecting a different pond.",
                    buttons=[("🎣 Cast Again", "quick_cast")],
                    web_app_buttons=get_miniapp_button()
                )
            )
            return

        # Get current price and create position
        base_currency = pond['base_currency']
        current_price = await get_crypto_price(base_currency)

        # Create position
        await create_position_with_gear(user_id, pond_id, active_rod['id'], current_price)

        # Trigger casting animation in private chat
        cast_msg = None
        try:
            from src.bot.ui.animations import animate_casting_sequence

            class _DummyMessage:
                def __init__(self, bot, chat_id):
                    self.bot = bot
                    self.chat_id = chat_id
                    self.from_user = type('user', (), {'id': chat_id})

                async def reply_text(self, text, parse_mode=None):
                    return await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=text,
                        parse_mode=parse_mode
                    )

            dummy_message = _DummyMessage(context.bot, user_id)
            user_level = user['level'] if user else 1
            cast_msg, _, _ = await animate_casting_sequence(
                dummy_message,
                username,
                user_level,
                current_price,
                pond_id=pond['id'],
                rod_id=active_rod['id']
            )
        except Exception as anim_err:
            logger.warning(f"Cast animation failed for user {user_id}: {anim_err}")
            cast_msg = None

        # Check if user gets first cast reward (gear unlock)
        cast_reward_message = await award_first_cast_reward(user_id)

        # Handle onboarding progression if applicable
        onboarding_result = await handle_onboarding_command(user_id, '/cast')
        if isinstance(onboarding_result, dict) and onboarding_result.get('send_message'):
            # In onboarding - show gear claim button if applicable
            if cast_reward_message:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                context.user_data['pending_gear_reward'] = cast_reward_message
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
                await asyncio.sleep(3)
                sent_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=onboarding_result['send_message'],
                    reply_markup=onboarding_result.get('reply_markup'),
                    parse_mode='HTML'
                )
                context.user_data['tutorial_message_id'] = sent_message.message_id
        else:
            # Normal cast completion - show CTA block with action buttons
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, CTABlock

            view = get_view_controller(context, user_id)

            if cast_reward_message:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                context.user_data['pending_gear_reward'] = cast_reward_message
                # Save flag to show CTA after gear claim
                context.user_data['pending_cast_cta'] = True
                context.user_data['is_first_cast'] = can_use_free

                gear_keyboard = [[InlineKeyboardButton("🎣 Claim gear", callback_data="claim_gear_reward")]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🎁 <b>New gear unlocked!</b>\n\nClaim your starter rods now.",
                    reply_markup=InlineKeyboardMarkup(gear_keyboard),
                    parse_mode='HTML'
                )
            elif can_use_free:
                # First cast - show encouragement with CTA
                await view.show_cta_block(
                    chat_id=user_id,
                    block_type=CTABlock,
                    data=BlockData(
                        header="✨ First Cast Complete!",
                        body="Your line is in the water. Wait for the right moment to maximize your catch!",
                        buttons=[
                            ("🪝 Hook Now", "quick_hook"),
                            ("📊 Check Status", "show_status")
                        ],
                        web_app_buttons=get_miniapp_button(),
                        footer="Pro tip: Check market movement before hooking"
                    )
                )
            else:
                # Regular cast - show standard CTA
                await view.show_cta_block(
                    chat_id=user_id,
                    block_type=CTABlock,
                    data=BlockData(
                        header="🎣 Cast Complete!",
                        body=f"Watch the market and hook when ready!",
                        buttons=[
                            ("🪝 Hook Now", "quick_hook"),
                            ("📊 Check Status", "show_status")
                        ],
                        web_app_buttons=get_miniapp_button(),
                        footer="Timing is everything in fishing"
                    )
                )

        logger.info(f"User {username} started fishing in pond {pond_id}")

    except Exception as e:
        logger.error(f"Error in _start_cast_for_pond for user {user_id}: {e}")
        from src.bot.ui.view_controller import get_view_controller
        from src.bot.ui.blocks import BlockData, ErrorBlock

        view = get_view_controller(context, user_id)
        await view.show_cta_block(
            chat_id=user_id,
            block_type=ErrorBlock,
            data=BlockData(
                header="❌ Something Went Wrong",
                body="An unexpected error occurred while starting your fishing session. Please try again!",
                buttons=[("🎣 Try Again", "quick_cast")],
                    web_app_buttons=get_miniapp_button()
            )
        )


async def pond_selection_callback(update, context):
    """Handle pond selection callback from private chat"""
    try:
        query = update.callback_query
        await query.answer()

        if not query.data.startswith("select_pond_"):
            return

        pond_id = int(query.data.split("_")[-1])
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name

        # ViewController will automatically clear the old CTA before showing new ones
        # Just start the cast process
        await _start_cast_for_pond(user_id, username, pond_id, context)

    except Exception as e:
        logger.error(f"Error in pond selection callback: {e}")
        if update.callback_query:
            user_id = update.effective_user.id
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ Error Selecting Pond",
                    body="Something went wrong while selecting your fishing pond. Please try again!",
                    buttons=[("🎣 Cast Again", "quick_cast")],
                    web_app_buttons=get_miniapp_button()
                )
            )
