"""
/hook command - Complete fishing operation and catch fish
"""

import asyncio
import logging

from telegram import Update, Chat
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, get_active_position, close_position, get_pond_by_id, get_rod_by_id,
    get_suitable_fish, check_rate_limit, check_hook_rate_limit,
    can_use_guaranteed_hook, should_get_special_catch, mark_onboarding_action
)
from src.utils.crypto_price import (
    get_crypto_price, calculate_pnl, format_time_fishing,
    get_fishing_time_seconds, get_price_error_message
)
from src.bot.ui.formatters import format_fishing_complete_caption
from src.bot.ui.messages import get_catch_story_from_db, get_quick_fishing_message
from src.bot.utils.telegram_utils import safe_reply
from src.bot.ui.animations import animate_hook_sequence, send_fish_card_or_fallback
from src.generators.fish_card_generator import generate_fish_card_from_db
from src.bot.features.onboarding import handle_onboarding_command

logger = logging.getLogger(__name__)


async def hook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /hook command - pull out fish with animated sequence and rate limiting"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat = update.effective_chat
    message = update.effective_message

    logger.debug(f"HOOK command called by user {user_id} ({username})")

    try:
        # Ignore in group chats
        if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
            return

        # Check general rate limit
        if not await check_rate_limit(user_id):
            await safe_reply(update, "⏳ Too many requests! Wait a bit before the next command.")
            return

        # Check hook-specific rate limit (more restrictive)
        if not await check_hook_rate_limit(user_id):
            await safe_reply(update, "🎣 Easy there, fisherman! Hook attempts are limited to prevent spam.\n\n<i>Max 3 hook attempts per minute. Give the fish a chance to bite! 🐟</i>")
            return

        # Check if user is fishing
        position = await get_active_position(user_id)

        if not position:
            await safe_reply(update, f"🎣 {username} is not fishing! Use /cast to throw the fishing rod.")
            return

        # Get pond and rod data for the position
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None

        # Get base currency for price fetching
        base_currency = pond['base_currency'] if pond else 'ETH'
        leverage = rod['leverage'] if rod else 1.5
        entry_price = position['entry_price']

        # Pre-calculate time for quick fishing check (no API call needed)
        time_fishing = format_time_fishing(position['entry_time'])
        fishing_time_seconds = get_fishing_time_seconds(position['entry_time'])

        # QUICK FISHING CHECK - must be done BEFORE animation starts!
        if fishing_time_seconds < 60:
            # We need a quick price check to see if P&L is minimal
            try:
                quick_price = await get_crypto_price(base_currency)
                quick_pnl = calculate_pnl(entry_price, quick_price, leverage)

                if abs(quick_pnl) < 0.1:
                    quick_message = get_quick_fishing_message(fishing_time_seconds)
                    await safe_reply(update, f"{quick_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n📈 <b>P&L:</b> {quick_pnl:+.4f}%\n\n<i>Wait at least 1 minute for the market to move!</i>")
                    return
            except Exception as e:
                logger.warning(f"Quick fishing check failed, allowing hook anyway: {e}")
                # If price check fails, allow fishing to continue

        # Get user level
        user = await get_user(user_id)
        user_level = user['level'] if user else 1

        # Start PARALLEL tasks immediately - no blocking!
        # 1. Hook animation (12.5 seconds)
        anim_message = message
        if anim_message is None:
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

            anim_message = _DummyMessage(context.bot, user_id)

        hook_task = asyncio.create_task(
            animate_hook_sequence(anim_message, username)
        )

        # 2. Price fetching with retry (may take up to 9+ seconds)
        async def fetch_price_and_calculate():
            try:
                current_price = await get_crypto_price(base_currency)
                pnl_percent = calculate_pnl(entry_price, current_price, leverage)
                return current_price, pnl_percent
            except Exception as e:
                logger.error(f"Price fetch failed in hook: {e}")
                return "ERROR", None

        price_task = asyncio.create_task(fetch_price_and_calculate())

        # Wait for price calculation to complete (runs in parallel with animation)
        current_price, pnl_percent = await price_task

        # Handle price fetch failure
        if current_price == "ERROR":
            # Price fetch failed - wait for animation to complete and show game error
            animation_message = await hook_task
            error_message = get_price_error_message()
            await safe_reply(update, f"{error_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n\n<i>Try pulling the hook again!</i>")
            return

        # Check for special catch (like secret letter during onboarding)
        special_catch_item = await should_get_special_catch(user_id)
        if special_catch_item:
            logger.info(f"User {user_id} should get special catch: {special_catch_item}")

            # Send special catch message instead of fish card
            special_message = f"📜 <b>You caught a {special_catch_item}!</b>\n\n<i>This is a special catch from your onboarding journey.</i>"
            await safe_reply(update, special_message)

            # Close position with special catch
            await close_position(position['id'], current_price, pnl_percent, None)

            # Handle onboarding progression for special catch
            await handle_onboarding_command(user_id, '/hook')

            logger.info(f"User {username} caught special item: {special_catch_item}")
            return

        # Check if user should get guaranteed good catch (onboarding)
        should_guarantee = await can_use_guaranteed_hook(user_id)
        if should_guarantee:
            # Override P&L for guaranteed good catch (2-5% positive)
            import random
            pnl_percent = random.uniform(2.0, 5.0)
            await mark_onboarding_action(user_id, 'first_hook')
            logger.info(f"Guaranteed good catch for user {user_id}: {pnl_percent}%")

        # Normal fishing - proceed with fish selection and generation
        # The database-driven fish selection with weighted rarity system
        fish_data = await get_suitable_fish(
            pnl_percent,
            user_level,
            position['pond_id'] if position['pond_id'] else 1,
            position['rod_id'] if position['rod_id'] else 1
        )

        if not fish_data:
            # Fallback to any fish within range
            logger.warning(f"No suitable fish found for PnL {pnl_percent}%, using fallback")
            fish_data = await get_suitable_fish(pnl_percent, 1, 1, 1)

        if fish_data:
            # Generate the catch story from database
            catch_story = get_catch_story_from_db(fish_data)

            # Create complete caption using new structured format
            complete_story = format_fishing_complete_caption(
                username=username,
                catch_story=catch_story,
                rod_name=rod['name'] if rod else 'Starter rod',
                leverage=leverage,
                pond_name=pond['name'] if pond else '🌊 Crypto Waters',
                pond_pair=pond['trading_pair'] if pond else 'ETH/USDT',
                time_fishing=time_fishing,
                entry_price=entry_price,
                current_price=current_price,
                pnl_percent=pnl_percent,
                user_level=user_level
            )

            # Start generating the image while animation continues
            card_task = asyncio.create_task(
                generate_fish_card_from_db(fish_data)
            )

            # Close position with fish ID
            await close_position(position['id'], current_price, pnl_percent, fish_data['id'])

            # Wait for both animation and card generation to complete
            animation_message = await hook_task
            card_image = await card_task

            # Send the fish card with complete story
            await send_fish_card_or_fallback(
                animation_message,
                card_image,
                complete_story
            )

            # Add share button if this is a group pond and we're in private chat
            if pond and pond.get('pond_type') == 'group' and pond.get('chat_id') and update.effective_chat.type == Chat.PRIVATE:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                # Store hook data for sharing
                context.user_data['share_hook_data'] = {
                    'fish_name': fish_data['name'],
                    'fish_emoji': fish_data['emoji'],
                    'pond_name': pond['name'],
                    'pond_chat_id': pond['chat_id'],
                    'pnl_percent': pnl_percent,
                    'username': username,
                    'card_image_bytes': card_image
                }
                share_button = [[InlineKeyboardButton("📢 Share in group", callback_data="share_hook")]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎣 <b>Great catch!</b> Want to share it with the group?\n\n<i>You'll get your 🪱 BAIT back for sharing!</i>",
                    reply_markup=InlineKeyboardMarkup(share_button),
                    parse_mode='HTML'
                )
        else:
            # Emergency fallback - should never happen with expanded fish database
            await hook_task  # Wait for animation to complete
            await safe_reply(update, f"🎣 {username} caught something strange! P&L: {pnl_percent:+.1f}%")
            await close_position(position['id'], current_price, pnl_percent, None)

        # Handle onboarding progression if applicable
        if fish_data:
            onboarding_result = await handle_onboarding_command(
                user_id,
                '/hook',
                fish_name=fish_data['name'],
                pnl=f"{pnl_percent:+.1f}"
            )
            if isinstance(onboarding_result, dict) and onboarding_result.get("send_message"):
                # Wait 4 seconds so user can see the fish card
                await asyncio.sleep(4)
                # Show first catch congrats message
                sent_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=onboarding_result["send_message"],
                    reply_markup=onboarding_result.get("reply_markup"),
                    parse_mode='HTML'
                )
                # Store reward message in context for later display via callback
                if onboarding_result.get("reward_message"):
                    context.user_data['pending_reward'] = onboarding_result["reward_message"]
        else:
            await handle_onboarding_command(user_id, '/hook')

    except Exception as e:
        logger.error(f"Error in hook command: {e}")
        await safe_reply(update, "🎣 Error pulling out fish! Try again.")
