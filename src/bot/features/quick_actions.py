"""
Quick Actions - Callback handlers for CTA block buttons.

This module provides button callback handlers that wrap existing commands,
making them accessible through inline keyboards instead of text commands.

Design Philosophy:
- Buttons are primary UI (for all users)
- Text commands are secondary (for pro users)
- Quick actions are wrappers around existing command logic
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def quick_cast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'quick_cast' button press.

    Wrapper for /cast command that works with inline buttons.
    Used in CTA blocks after hook, share, etc.

    Button text: "🎣 Cast Again" or "🎣 Start Fishing"
    """
    try:
        query = update.callback_query
        await query.answer()

        # Import cast command
        from src.bot.commands.cast import cast

        # Call existing cast logic directly
        # Update object already has effective_message from callback_query.message
        await cast(update, context)

        logger.info(f"Quick cast triggered by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in quick_cast_callback: {e}")
        logger.exception("Full quick_cast error:")
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "❌ <b>Error</b>\n\nCould not start fishing. Try <code>/cast</code> command.",
                    parse_mode='HTML'
                )
            except Exception:
                pass


async def quick_hook_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'quick_hook' button press.

    Wrapper for /hook command that works with inline buttons.
    Used in error blocks when user tries to cast while already fishing.

    Button text: "🪝 Hook Now"
    """
    try:
        query = update.callback_query
        # NOTE: Don't call query.answer() here - hook() will handle it
        # This allows hook() to show custom messages (e.g., quick fishing error)

        # Import hook command
        from src.bot.commands.hook import hook

        # Call existing hook logic directly
        await hook(update, context)

        logger.info(f"Quick hook triggered by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in quick_hook_callback: {e}")
        logger.exception("Full quick_hook error:")
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "❌ <b>Error</b>\n\nCould not hook. Try <code>/hook</code> command.",
                    parse_mode='HTML'
                )
            except Exception:
                pass


async def show_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'show_status' button press.

    Wrapper for /status command that works with inline buttons.
    Used in error blocks and CTA blocks for checking current state.

    Button text: "📊 Check Status" or "📊 Status"
    """
    try:
        query = update.callback_query
        await query.answer()

        # Import status command
        from src.bot.commands.status import status

        # Call existing status logic directly
        await status(update, context)

        logger.info(f"Quick status triggered by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in show_status_callback: {e}")
        logger.exception("Full show_status error:")
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "❌ <b>Error</b>\n\nCould not show status. Try <code>/status</code> command.",
                    parse_mode='HTML'
                )
            except Exception:
                pass


async def quick_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle quick buy button press.

    Shows purchase options when user clicks buy from NO_BAIT state.

    Button text: "💰 Buy BAIT"
    """
    try:
        query = update.callback_query
        await query.answer()

        # Import buy command
        from src.bot.commands.payments import buy_bait_command

        # Call existing buy logic directly
        await buy_bait_command(update, context)

        logger.info(f"Quick buy triggered by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in quick_buy_callback: {e}")
        logger.exception("Full quick_buy error:")
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "❌ <b>Error</b>\n\nCould not show store. Try <code>/buy</code> command.",
                    parse_mode='HTML'
                )
            except Exception:
                pass


async def update_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'update_status' button press.

    Refreshes the current status by calling /status command and updating the message.
    Used for real-time P&L monitoring without creating new messages.

    Button text: "🔄 Update Status"
    """
    try:
        query = update.callback_query
        await query.answer("Updating...")

        # Import status command
        from src.bot.commands.status import status

        # Call existing status logic directly - it will handle message editing
        await status(update, context)

        logger.info(f"Status update triggered by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in update_status_callback: {e}")
        logger.exception("Full update_status error:")
        if update.callback_query:
            try:
                await update.callback_query.answer("❌ Update failed. Try /status")
            except Exception:
                pass


async def quick_pnl_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'quick_pnl' button press.

    Wrapper for /pnl command that works with inline buttons.
    Shows user's virtual balance and leaderboard position.

    Button text: "💰 My Balance" or "💰 Balance"
    """
    try:
        query = update.callback_query
        await query.answer()

        # Import pnl command
        from src.bot.commands.start import pnl

        # Call existing pnl logic directly
        await pnl(update, context)

        logger.info(f"Quick PnL triggered by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in quick_pnl_callback: {e}")
        logger.exception("Full quick_pnl error:")
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "❌ <b>Error</b>\n\nCould not show balance. Try <code>/pnl</code> command.",
                    parse_mode='HTML'
                )
            except Exception:
                pass


async def quick_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'quick_help' button press.

    Wrapper for /help command that works with inline buttons.
    Shows game help and guide.

    Button text: "📖 Help" or "❓ How to Play"
    """
    try:
        query = update.callback_query
        await query.answer()

        # Import help command
        from src.bot.commands.start import help_command

        # Call existing help logic directly
        await help_command(update, context)

        logger.info(f"Quick help triggered by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in quick_help_callback: {e}")
        logger.exception("Full quick_help error:")
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "❌ <b>Error</b>\n\nCould not show help. Try <code>/help</code> command.",
                    parse_mode='HTML'
                )
            except Exception:
                pass


async def cancel_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle 'cancel' button press.

    Generic cancel action that clears the CTA and returns to idle state.

    Button text: "❌ Cancel" or "⬅️ Back"
    """
    try:
        query = update.callback_query
        await query.answer("Cancelled")

        # Clear the CTA message
        try:
            await query.delete_message()
        except Exception:
            try:
                await query.edit_message_text(
                    "❌ <b>Cancelled</b>",
                    parse_mode='HTML'
                )
            except Exception:
                pass

        logger.info(f"Action cancelled by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in cancel_action_callback: {e}")
