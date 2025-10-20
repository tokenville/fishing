"""
Share handlers for posting fishing activity to groups.
Handles manual sharing of cast and hook events to group chats.
"""

import logging
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.bot.random_messages import get_random_cast_appendix, get_random_hook_appendix
from src.database.db_manager import add_bait_tokens
from src.bot.ui.formatters import format_pnl_percent

logger = logging.getLogger(__name__)


async def share_cast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle share cast button click - posts cast notification to group"""
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        # Get stored cast data
        share_data = context.user_data.get('share_cast_data')
        if not share_data:
            # Delete old message and show error CTA
            try:
                await query.delete_message()
            except Exception:
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass

            # Show error CTA with Cast Again button
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ Share Expired",
                    body="Cast data not found. Please cast again to share.",
                    buttons=[("🎣 Cast Again", "quick_cast")],
                    footer="Share expires after some time for security"
                )
            )
            return

        pond_name = share_data.get('pond_name')
        pond_chat_id = share_data.get('pond_chat_id')
        username = share_data.get('username')

        # Send notification to group
        try:
            # Get bot username for deep link
            bot_username = (await context.bot.get_me()).username

            # Create keyboard with Join Fishing button
            keyboard = [[
                InlineKeyboardButton(
                    "🎣 Join Fishing",
                    url=f"https://t.me/{bot_username}?start=join_{pond_chat_id}"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            cast_appendix = get_random_cast_appendix()
            group_message = f"🎣 <b>{username}</b> cast their rod into <b>{pond_name}</b>.{cast_appendix}"
            await context.bot.send_message(
                chat_id=pond_chat_id,
                text=group_message,
                parse_mode='HTML',
                disable_notification=True,
                reply_markup=reply_markup
            )

            # Delete old message and show success CTA
            try:
                await query.delete_message()
            except Exception:
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass

            # Show success CTA with Cast Again button
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, CTABlock, get_miniapp_button

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=CTABlock,
                data=BlockData(
                    header="✅ Shared Successfully!",
                    body="Your cast has been posted to the group!",
                    buttons=[("🎣 Cast Again", "quick_cast")],
                    web_app_buttons=get_miniapp_button(),
                    footer="Keep fishing to catch more!"
                )
            )

            # Clear stored data
            context.user_data.pop('share_cast_data', None)

        except Exception as e:
            logger.error(f"Failed to share cast to group: {e}")

            # Delete old message and show error CTA
            try:
                await query.delete_message()
            except Exception:
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass

            # Show error CTA with Cast Again button
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ Share Failed",
                    body="Could not post to group. Bot might not have permissions.",
                    buttons=[("🎣 Cast Again", "quick_cast")],
                    footer="Check that bot is admin in the group"
                )
            )

    except Exception as e:
        logger.error(f"Error in share_cast_callback: {e}")
        if update.callback_query:
            # Delete old message and show error CTA
            try:
                await update.callback_query.delete_message()
            except Exception:
                try:
                    await update.callback_query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass

            # Show error CTA with Cast Again button
            try:
                from src.bot.ui.view_controller import get_view_controller
                from src.bot.ui.blocks import BlockData, ErrorBlock

                view = get_view_controller(context, user_id)
                await view.show_cta_block(
                    chat_id=user_id,
                    block_type=ErrorBlock,
                    data=BlockData(
                        header="❌ Error",
                        body="Something went wrong. Please try again.",
                        buttons=[("🎣 Cast Again", "quick_cast")],
                        footer="If error persists, contact support"
                    )
                )
            except Exception as inner_e:
                logger.error(f"Failed to show error CTA: {inner_e}")


async def share_hook_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle share hook button click - posts catch notification to group"""
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        # Get stored hook data
        share_data = context.user_data.get('share_hook_data')
        if not share_data:
            # Delete old message and show error CTA
            try:
                await query.delete_message()
            except Exception:
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass

            # Show error CTA with Cast Again button
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ Share Expired",
                    body="Catch data not found. Please catch a fish again to share.",
                    buttons=[("🎣 Cast Again", "quick_cast")],
                    footer="Share expires after some time for security"
                )
            )
            return

        fish_name = share_data.get('fish_name')
        fish_emoji = share_data.get('fish_emoji')
        pond_name = share_data.get('pond_name')
        pond_chat_id = share_data.get('pond_chat_id')
        pnl_percent = share_data.get('pnl_percent')
        username = share_data.get('username')
        image_bytes = share_data.get('card_image_bytes')
        image_path = share_data.get('image_path')

        # Send notification to group
        try:
            # Get bot username for deep link
            bot_username = (await context.bot.get_me()).username

            # Create keyboard with Join Fishing button
            keyboard = [[
                InlineKeyboardButton(
                    "🎣 Join Fishing",
                    url=f"https://t.me/{bot_username}?start=join_{pond_chat_id}"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            pnl_color = "🟢" if pnl_percent > 0 else "🔴" if pnl_percent < 0 else "⚪"
            hook_appendix = get_random_hook_appendix()
            pnl_str = format_pnl_percent(pnl_percent)
            group_notification = f"🎣 <b>{username}</b> caught {fish_emoji} <b>{fish_name}</b> from {pond_name}! {pnl_color} P&L: <b>{pnl_str}</b>{hook_appendix}"

            if image_bytes:
                await context.bot.send_photo(
                    chat_id=pond_chat_id,
                    photo=BytesIO(image_bytes),
                    caption=group_notification,
                    parse_mode='HTML',
                    disable_notification=True,
                    reply_markup=reply_markup
                )
            elif image_path:
                with open(image_path, 'rb') as photo_file:
                    await context.bot.send_photo(
                        chat_id=pond_chat_id,
                        photo=photo_file,
                        caption=group_notification,
                        parse_mode='HTML',
                        disable_notification=True,
                        reply_markup=reply_markup
                    )
            else:
                await context.bot.send_message(
                    chat_id=pond_chat_id,
                    text=group_notification,
                    parse_mode='HTML',
                    disable_notification=True,
                    reply_markup=reply_markup
                )

            # Award 1 BAIT token for sharing
            await add_bait_tokens(user_id, 1)

            # Use ViewController to show success CTA
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, CTABlock, get_miniapp_button

            # Clear the old message first
            try:
                await query.delete_message()
            except Exception:
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass

            # Show CTA with Cast Again + MiniApp buttons
            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=CTABlock,
                data=BlockData(
                    header="✅ Shared Successfully!",
                    body="Your catch has been posted to the group!\n\n🪱 +1 BAIT token reward for sharing!",
                    buttons=[("🎣 Cast Again", "quick_cast")],
                    web_app_buttons=get_miniapp_button(),
                    footer="Keep fishing to catch more!"
                )
            )

            # Clear stored data
            context.user_data.pop('share_hook_data', None)

        except Exception as e:
            logger.error(f"Failed to share hook to group: {e}")

            # Delete old message and show error CTA
            try:
                await query.delete_message()
            except Exception:
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass

            # Show error CTA with Cast Again button
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ Share Failed",
                    body="Could not post to group. Bot might not have permissions.",
                    buttons=[("🎣 Cast Again", "quick_cast")],
                    footer="Check that bot is admin in the group"
                )
            )

    except Exception as e:
        logger.error(f"Error in share_hook_callback: {e}")
        if update.callback_query:
            # Delete old message and show error CTA
            try:
                await update.callback_query.delete_message()
            except Exception:
                try:
                    await update.callback_query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass

            # Show error CTA with Cast Again button
            try:
                from src.bot.ui.view_controller import get_view_controller
                from src.bot.ui.blocks import BlockData, ErrorBlock

                user_id = update.effective_user.id
                view = get_view_controller(context, user_id)
                await view.show_cta_block(
                    chat_id=user_id,
                    block_type=ErrorBlock,
                    data=BlockData(
                        header="❌ Error",
                        body="Something went wrong. Please try again.",
                        buttons=[("🎣 Cast Again", "quick_cast")],
                        footer="If error persists, contact support"
                    )
                )
            except Exception as inner_e:
                logger.error(f"Failed to show error CTA: {inner_e}")
