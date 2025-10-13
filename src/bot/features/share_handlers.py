"""
Share handlers for posting fishing activity to groups.
Handles manual sharing of cast and hook events to group chats.
"""

import logging
from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.random_messages import get_random_cast_appendix, get_random_hook_appendix
from src.database.db_manager import add_bait_tokens

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
            await query.edit_message_text(
                "❌ <b>Share expired</b>\n\n<i>Cast data not found. Please cast again to share.</i>",
                parse_mode='HTML'
            )
            return

        pond_name = share_data.get('pond_name')
        pond_chat_id = share_data.get('pond_chat_id')
        username = share_data.get('username')

        # Send notification to group
        try:
            cast_appendix = get_random_cast_appendix()
            group_message = f"🎣 <b>{username}</b> cast their rod into <b>{pond_name}</b>.{cast_appendix}"
            await context.bot.send_message(
                chat_id=pond_chat_id,
                text=group_message,
                parse_mode='HTML',
                disable_notification=True
            )

            # Update button to show success
            await query.edit_message_text(
                "✅ <b>Shared successfully!</b>\n\n<i>Your cast has been posted to the group.</i>",
                parse_mode='HTML'
            )

            # Clear stored data
            context.user_data.pop('share_cast_data', None)

        except Exception as e:
            logger.error(f"Failed to share cast to group: {e}")
            await query.edit_message_text(
                "❌ <b>Share failed</b>\n\n<i>Could not post to group. Bot might not have permissions.</i>",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error in share_cast_callback: {e}")
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "❌ <b>Error</b>\n\n<i>Something went wrong. Try again.</i>",
                    parse_mode='HTML'
                )
            except:
                pass


async def share_hook_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle share hook button click - posts catch notification to group"""
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        # Get stored hook data
        share_data = context.user_data.get('share_hook_data')
        if not share_data:
            await query.edit_message_text(
                "❌ <b>Share expired</b>\n\n<i>Catch data not found. Please hook again to share.</i>",
                parse_mode='HTML'
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
            pnl_color = "🟢" if pnl_percent > 0 else "🔴" if pnl_percent < 0 else "⚪"
            hook_appendix = get_random_hook_appendix()
            group_notification = f"🎣 <b>{username}</b> caught {fish_emoji} {fish_name} from <b>{pond_name}</b>! {pnl_color} P&L: {pnl_percent:+.1f}%{hook_appendix}"

            if image_bytes:
                await context.bot.send_photo(
                    chat_id=pond_chat_id,
                    photo=BytesIO(image_bytes),
                    caption=group_notification,
                    parse_mode='HTML',
                    disable_notification=True
                )
            elif image_path:
                with open(image_path, 'rb') as photo_file:
                    await context.bot.send_photo(
                        chat_id=pond_chat_id,
                        photo=photo_file,
                        caption=group_notification,
                        parse_mode='HTML',
                        disable_notification=True
                    )
            else:
                await context.bot.send_message(
                    chat_id=pond_chat_id,
                    text=group_notification,
                    parse_mode='HTML',
                    disable_notification=True
                )

            # Award 1 BAIT token for sharing
            await add_bait_tokens(user_id, 1)

            # Update button to show success with BAIT reward
            await query.edit_message_text(
                "✅ <b>Shared successfully!</b>\n\n<i>Your catch has been posted to the group.</i>\n\n🪱 <b>+1 BAIT</b> <i>reward for sharing!\n\nUse /cast to get more fish.</i>",
                parse_mode='HTML'
            )

            # Clear stored data
            context.user_data.pop('share_hook_data', None)

        except Exception as e:
            logger.error(f"Failed to share hook to group: {e}")
            await query.edit_message_text(
                "❌ <b>Share failed</b>\n\n<i>Could not post to group. Bot might not have permissions.</i>",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error in share_hook_callback: {e}")
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "❌ <b>Error</b>\n\n<i>Something went wrong. Try again.</i>",
                    parse_mode='HTML'
                )
            except:
                pass
