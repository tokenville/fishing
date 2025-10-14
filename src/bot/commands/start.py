"""
/start and /help commands
"""

import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, ensure_user_has_level, give_starter_rod,
    is_onboarding_completed
)
from src.bot.ui.formatters import get_full_start_message
from src.bot.ui.messages import get_help_text
from src.bot.utils.telegram_utils import safe_reply
from src.bot.features.onboarding import (
    get_current_onboarding_step, send_onboarding_message, should_show_mini_app_button
)
from src.bot.ui.blocks import get_miniapp_button

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - show onboarding for new users, full guide for completed users"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat

    logger.debug(f"START command called by user {user_id} ({username})")

    # Ignore in group chats
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        return

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

        # Check if user has completed onboarding
        onboarding_completed = await is_onboarding_completed(user_id)
        logger.debug(f"User {user_id} onboarding completed: {onboarding_completed}")

        if onboarding_completed:
            # Show full game guide for users who completed onboarding
            start_message = await get_full_start_message(user_id, username)
        else:
            # Handle onboarding flow for new users
            logger.info(f"Starting onboarding flow for user {user_id}")
            try:
                current_step = await get_current_onboarding_step(user_id)
                logger.debug(f"Current onboarding step for user {user_id}: {current_step}")
                await send_onboarding_message(update, context, user_id, current_step)
                return  # Exit early since onboarding handler sent the message
            except Exception as onboarding_error:
                logger.error(f"Onboarding error for user {user_id}: {onboarding_error}")
                logger.exception("Full onboarding error traceback:")
                # Fallback to regular start message
                start_message = await get_full_start_message(user_id, username)

        # Create web app button only if user should see it
        webapp_url = os.environ.get('WEBAPP_URL')
        show_mini_app = await should_show_mini_app_button(user_id)

        if not webapp_url or not show_mini_app:
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
    chat = update.effective_chat

    logger.debug(f"HELP command called by user {user_id} ({username})")

    # Ignore in group chats
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    try:
        # Get dynamic help text from database
        help_text = await get_help_text()
        await safe_reply(update, help_text)

    except Exception as e:
        logger.error(f"Error in help command for user {user_id}: {e}")
        await safe_reply(update, "🎣 Error loading help! Try again.")


async def pnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pnl command - show user virtual balance and leaderboard position"""
    from src.database.db_manager import get_user_virtual_balance, get_flexible_leaderboard

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat

    # Ignore in group chats
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    try:
        # Get user virtual balance
        balance = await get_user_virtual_balance(user_id)

        # Get user position in leaderboard
        leaderboard_data = await get_flexible_leaderboard(
            pond_id=None,
            time_period='all',
            user_id=user_id,
            limit=10
        )

        # Format balance with color
        balance_color = "🟢" if balance >= 10000 else "🔴"
        balance_change = balance - 10000
        balance_change_str = f"{balance_change:+.2f}"

        message = f"""💰 <b>Your Trading Balance</b>

{balance_color} <b>${balance:,.2f}</b> ({balance_change_str})
<i>Starting capital: $10,000</i>

"""

        # Add leaderboard position if available
        if leaderboard_data and leaderboard_data.get('user_position'):
            pos = leaderboard_data['user_position']
            total = leaderboard_data.get('total_players', 0)
            message += f"""<b>📊 Your Rank:</b>
<b>#{pos['rank']}</b> of {total} players (top {pos['percentile']:.0f}%)

"""

        # Show balance with CTA button
        from src.bot.ui.view_controller import get_view_controller
        from src.bot.ui.blocks import BlockData, CTABlock

        view = get_view_controller(context, user_id)
        await view.show_cta_block(
            chat_id=user_id,
            block_type=CTABlock,
            data=BlockData(
                header="",  # Header is in message
                body=message,
                buttons=[("🎣 Start Fishing", "quick_cast")],
                web_app_buttons=get_miniapp_button(),
                footer="Grow your balance with smart fishing!"
            ),
            clear_previous=False
        )

    except Exception as e:
        logger.error(f"Error in pnl command: {e}")
        await safe_reply(update, "💰 Error loading balance! Try again.")


async def skip_onboarding_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /skip command - skip onboarding tutorial"""
    from src.bot.features.onboarding import skip_onboarding

    user_id = update.effective_user.id
    chat = update.effective_chat

    # Ignore in group chats
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    try:
        await skip_onboarding(user_id)
        await safe_reply(update, "✅ Onboarding skipped! Use /start to see full game guide.")
    except Exception as e:
        logger.error(f"Error skipping onboarding: {e}")
        await safe_reply(update, "❌ Error skipping onboarding!")
