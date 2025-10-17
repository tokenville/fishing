"""
/status command - Check current fishing position
"""

import logging

from telegram import Update, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import get_user, get_active_position, get_pond_by_id, get_rod_by_id
from src.utils.crypto_price import get_crypto_price
from src.utils.fishing_calculations import (
    calculate_pnl_percent,
    get_pnl_color,
    format_fishing_duration_from_entry
)
from src.bot.ui.formatters import format_enhanced_status_message, format_no_fishing_status, format_new_user_status
from src.bot.utils.telegram_utils import safe_reply

logger = logging.getLogger(__name__)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show current fishing position"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat

    # Check if this is a callback query (button press) for message editing
    is_update_request = bool(update.callback_query)
    message_to_edit = update.callback_query.message if is_update_request else None

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
            # User is idle - show CTA block with cast button
            from src.bot.ui.blocks import BlockData, CTABlock

            bait_tokens = user['bait_tokens'] if user else 0

            # Format status info
            status_info = format_no_fishing_status(username, bait_tokens)

            # Prepare block data
            block_data = BlockData(
                header="📊 Status",
                body=status_info,
                buttons=[("🎣 Start Fishing", "quick_cast")]
            )

            # Edit existing message or send new one
            if is_update_request and message_to_edit:
                from src.bot.ui.blocks import CTABlock
                text, markup = CTABlock.render(block_data)
                try:
                    await message_to_edit.edit_text(
                        text=text,
                        reply_markup=markup,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Could not edit message: {e}")
            else:
                # Send new message
                from src.bot.ui.view_controller import get_view_controller
                view = get_view_controller(context, user_id)
                await view.show_cta_block(
                    chat_id=user_id,
                    block_type=CTABlock,
                    data=block_data,
                    clear_previous=False  # Don't clear previous CTA for status check
                )
            return

        # Get current P&L with enhanced display
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None

        base_currency = pond['base_currency'] if pond else 'TAC'
        leverage = rod['leverage'] if rod else 1.5

        current_price = await get_crypto_price(base_currency)
        entry_price = position['entry_price']
        entry_time = position['entry_time']

        # Use centralized PnL calculation with proper UTC time handling
        pnl_percent = calculate_pnl_percent(entry_price, current_price, leverage)
        pnl_color = get_pnl_color(pnl_percent)
        time_fishing = format_fishing_duration_from_entry(entry_time)

        logger.debug(
            f"Status check: user={user_id}, position_id={position['id']}, "
            f"entry_price={entry_price:.2f}, current_price={current_price:.2f}, "
            f"leverage={leverage}x, pnl={pnl_percent:.4f}%, time={time_fishing}"
        )

        # Send enhanced status message as CTA block (fishing in progress)
        from src.bot.ui.blocks import BlockData, CTABlock

        pond_name = pond['name'] if pond else 'Unknown Pond'
        pond_pair = pond['trading_pair'] if pond else f'{base_currency}/USDT'
        rod_name = rod['name'] if rod else 'Unknown Rod'
        user_level = user['level'] if user else 1

        status_text = format_enhanced_status_message(
            username, pond_name, pond_pair, rod_name, leverage,
            entry_price, current_price, pnl_percent, time_fishing, user_level
        )

        # Prepare block data with hook and update buttons
        block_data = BlockData(
            header="",  # Header is included in status_text
            body=status_text,
            buttons=[
                ("🪝 Hook Now", "quick_hook"),
                ("🔄 Update Status", "update_status")
            ],
            footer="Timing is everything in fishing"
        )

        # Edit existing message or send new one
        if is_update_request and message_to_edit:
            text, markup = CTABlock.render(block_data)
            try:
                await message_to_edit.edit_text(
                    text=text,
                    reply_markup=markup,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Could not edit message: {e}")
        else:
            # Send new message
            from src.bot.ui.view_controller import get_view_controller
            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=CTABlock,
                data=block_data,
                clear_previous=False  # Don't clear previous CTA for status check
            )

    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await safe_reply(update, "🎣 Error checking status! Try again.")
