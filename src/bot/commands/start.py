"""
/start and /help commands
"""

import logging

from telegram import Update, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, create_user, ensure_user_has_level,
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
        else:
            # Ensure existing user has level
            await ensure_user_has_level(user_id)
            user = await get_user(user_id)  # Refresh user data

        # Check if user has completed onboarding (cache for later use)
        onboarding_completed = await is_onboarding_completed(user_id)
        logger.debug(f"User {user_id} onboarding completed: {onboarding_completed}")

        # Handle deep link for joining groups
        if context.args and len(context.args) > 0 and context.args[0].startswith('join_'):
            try:
                chat_id = int(context.args[0].replace('join_', ''))
                from src.bot.features.group_management import connect_user_to_pond
                success, message, pond_name, is_new_member = await connect_user_to_pond(user_id, username, chat_id)

                if success:
                    logger.info(f"User {user_id} joined pond {chat_id} ({pond_name}) via deep link (new_member={is_new_member})")

                    # If user is already a member and onboarding is complete, show cast CTA
                    if not is_new_member and onboarding_completed:
                        from src.bot.features.group_management import show_already_member_cta
                        await show_already_member_cta(context, user_id, pond_name)
                        return  # Exit early

                    # Only send pond welcome message if user has completed onboarding
                    # New users will see pond info in onboarding step 1
                    if onboarding_completed and is_new_member:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='HTML'
                        )
                else:
                    logger.warning(f"Failed to connect user {user_id} to pond {chat_id} via deep link")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='HTML'
                    )
            except (ValueError, Exception) as e:
                logger.error(f"Deep link error for user {user_id}: {e}")

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

        # Show start message with CTA buttons using UI system
        from src.bot.ui.view_controller import get_view_controller
        from src.bot.ui.blocks import BlockData, CTABlock, get_miniapp_button

        view = get_view_controller(context, user_id)

        # Prepare buttons
        buttons = [
            ("🎣 Start Fishing", "quick_cast")
        ]

        # Add MiniApp button if available
        web_app_buttons = []
        show_mini_app = await should_show_mini_app_button(user_id)
        if show_mini_app:
            web_app_buttons = get_miniapp_button()

        logger.debug(f"Sending start message with CTA block to user {user_id}")
        await view.show_cta_block(
            chat_id=user_id,
            block_type=CTABlock,
            data=BlockData(
                header="",  # Header is in start_message
                body=start_message,
                buttons=buttons,
                web_app_buttons=web_app_buttons,
                footer="Pro tip: Commands work too - <code>/cast</code>, <code>/hook</code>, <code>/help</code>"
            ),
            clear_previous=False
        )
        logger.debug(f"Successfully sent start message to user {user_id}")

    except Exception as e:
        logger.error(f"Error in start command for user {user_id}: {e}")
        logger.exception("Full start command error traceback:")
        await safe_reply(update, "🎣 Welcome! Use /help for guide.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show game guide with CTA buttons"""
    user_id = update.effective_user.id
    chat = update.effective_chat

    logger.debug(f"HELP command called by user {user_id}")

    # Ignore in group chats
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    try:
        # Get dynamic help text from database
        help_text = await get_help_text()

        # Show help with CTA buttons using UI system
        from src.bot.ui.view_controller import get_view_controller
        from src.bot.ui.blocks import BlockData, CTABlock, get_miniapp_button

        view = get_view_controller(context, user_id)

        # Prepare buttons
        buttons = [
            ("🎣 Start Fishing", "quick_cast")
        ]

        # Add MiniApp button if available
        web_app_buttons = get_miniapp_button()

        await view.show_cta_block(
            chat_id=user_id,
            block_type=CTABlock,
            data=BlockData(
                header="",  # Header is in help_text
                body=help_text,
                buttons=buttons,
                web_app_buttons=web_app_buttons,
                footer="Commands: <code>/cast</code>, <code>/hook</code>, <code>/status</code>, <code>/leaderboard</code>"
            ),
            clear_previous=False
        )

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
    """Handle /skip command - skip onboarding tutorial with success CTA"""
    from src.bot.features.onboarding import skip_onboarding

    user_id = update.effective_user.id
    chat = update.effective_chat

    # Ignore in group chats
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    try:
        await skip_onboarding(user_id)

        # Show success CTA block with action buttons
        from src.bot.ui.view_controller import get_view_controller
        from src.bot.ui.blocks import build_success_block, CTABlock

        view = get_view_controller(context, user_id)
        data = build_success_block(
            header="✅ Onboarding Skipped!",
            body="You're all set! Ready to start fishing?",
            primary_action=("🎣 Start Fishing", "quick_cast"),
            secondary_action=("📖 Help", "quick_help"),
            footer="Use <code>/cast</code> command anytime to start fishing"
        )

        await view.show_cta_block(
            chat_id=user_id,
            block_type=CTABlock,
            data=data,
            clear_previous=False
        )

    except Exception as e:
        logger.error(f"Error skipping onboarding: {e}")
        await safe_reply(update, "❌ Error skipping onboarding!")
