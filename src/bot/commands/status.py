"""
/status command - Check current fishing position
"""

import logging

from telegram import Update, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import get_user, get_active_position, get_pond_by_id, get_rod_by_id
from src.utils.crypto_price import get_crypto_price, calculate_pnl, get_pnl_color, format_time_fishing
from src.bot.ui.formatters import format_enhanced_status_message, format_no_fishing_status, format_new_user_status
from src.bot.utils.telegram_utils import safe_reply

logger = logging.getLogger(__name__)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show current fishing position"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat

    # Ignore in group chats
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    try:
        # Get user
        user = await get_user(user_id)
        if not user:
            await safe_reply(update, format_new_user_status(username))
            return

        # Get active position
        position = await get_active_position(user_id)

        if not position:
            # User is idle - show CTA block with cast + miniapp buttons
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, CTABlock, get_miniapp_button

            bait_tokens = user['bait_tokens'] if user else 0

            # Format status info
            status_info = format_no_fishing_status(username, bait_tokens)

            # Show status as CTA block with action buttons
            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=CTABlock,
                data=BlockData(
                    header="📊 Status",
                    body=status_info,
                    buttons=[("🎣 Start Fishing", "quick_cast")],
                    web_app_buttons=get_miniapp_button()
                ),
                clear_previous=False  # Don't clear previous CTA for status check
            )
            return

        # Get current P&L with enhanced display
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None

        base_currency = pond['base_currency'] if pond else 'ETH'
        leverage = rod['leverage'] if rod else 1.5

        current_price = await get_crypto_price(base_currency)
        entry_price = position['entry_price']

        pnl_percent = calculate_pnl(entry_price, current_price, leverage)
        pnl_color = get_pnl_color(pnl_percent)
        time_fishing = format_time_fishing(position['entry_time'])

        # Send enhanced status message as Info block (fishing in progress)
        from src.bot.ui.view_controller import get_view_controller
        from src.bot.ui.blocks import BlockData

        pond_name = pond['name'] if pond else 'Unknown Pond'
        pond_pair = pond['trading_pair'] if pond else f'{base_currency}/USDT'
        rod_name = rod['name'] if rod else 'Unknown Rod'
        user_level = user['level'] if user else 1

        status_text = format_enhanced_status_message(
            username, pond_name, pond_pair, rod_name, leverage,
            entry_price, current_price, pnl_percent, time_fishing, user_level
        )

        # Show as CTA block with hook + miniapp buttons (buttons are primary UI)
        from src.bot.ui.blocks import CTABlock, get_miniapp_button

        view = get_view_controller(context, user_id)
        await view.show_cta_block(
            chat_id=user_id,
            block_type=CTABlock,
            data=BlockData(
                header="",  # Header is included in status_text
                body=status_text,
                buttons=[("🪝 Hook Now", "quick_hook")],
                web_app_buttons=get_miniapp_button(),
                footer="Timing is everything in fishing"
            ),
            clear_previous=False  # Don't clear previous CTA for status check
        )

    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await safe_reply(update, "🎣 Error checking status! Try again.")
