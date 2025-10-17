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
from src.utils.crypto_price import get_crypto_price, get_price_error_message
from src.utils.fishing_calculations import (
    calculate_pnl_percent,
    format_fishing_duration_from_entry
)
from src.bot.ui.formatters import format_fishing_complete_caption
from src.bot.ui.messages import get_catch_story_from_db
from src.bot.utils.telegram_utils import safe_reply
from src.bot.utils.validators import check_quick_fishing
from src.bot.ui.animations import animate_hook_sequence, send_fish_card_or_fallback
from src.generators.fish_card_generator import generate_fish_card_from_db
from src.bot.features.onboarding import handle_onboarding_command
from src.bot.ui.blocks import get_miniapp_button

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
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock

            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="❌ Not Fishing!",
                    body=f"{username}, you don't have an active fishing session. Cast your rod first!",
                    buttons=[("🎣 Start Fishing", "quick_cast")],
                    web_app_buttons=get_miniapp_button()
                )
            )
            return

        # Get pond and rod data for the position
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None

        # Get base currency for price fetching
        base_currency = pond['base_currency'] if pond else 'TAC'
        leverage = rod['leverage'] if rod else 1.5
        entry_price = position['entry_price']
        entry_time = position['entry_time']

        # Calculate fishing time for later use (centralized UTC-aware calculation)
        time_fishing = format_fishing_duration_from_entry(entry_time)

        logger.info(
            f"Hook initiated: user={user_id}, position_id={position['id']}, "
            f"entry_price={entry_price:.2f}, entry_time={entry_time}, "
            f"time_fishing={time_fishing}, leverage={leverage}x, currency={base_currency}"
        )

        # QUICK FISHING CHECK - show ErrorBlock to avoid breaking UI
        should_block, quick_message_html = await check_quick_fishing(position, base_currency, entry_price, leverage)
        if should_block:
            # Show ErrorBlock with action buttons (consistent with UI system)
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, ErrorBlock
            from src.utils.crypto_price import get_fishing_time_seconds

            view = get_view_controller(context, user_id)
            fishing_time_seconds = get_fishing_time_seconds(entry_time)

            # Get the funny message
            from src.bot.ui.messages import get_quick_fishing_message
            funny_message = get_quick_fishing_message(fishing_time_seconds)

            # For callback queries, acknowledge the click first
            if update.callback_query:
                await update.callback_query.answer()

            # Show ErrorBlock with helpful actions
            await view.show_cta_block(
                chat_id=user_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="⏰ Too Quick!",
                    body=f"{funny_message}\n\n⏱ Time: {time_fishing}\n\nWait at least 1 minute for the market to move!",
                    buttons=[
                        ("📊 Check Status", "show_status"),
                        ("🔄 Try Again", "quick_hook")
                    ],
                    footer="Patience is key in fishing 🎣"
                )
            )
            return

        # Get user level
        user = await get_user(user_id)
        user_level = user['level'] if user else 1

        # Acknowledge callback query if called from button (prevents "loading..." state)
        if update.callback_query:
            await update.callback_query.answer()

        # Transition to HOOKING state
        from src.bot.ui.state_machine import get_state_machine, UserState
        state_machine = get_state_machine(user_id)
        await state_machine.transition_to(UserState.HOOKING, context.user_data)

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
                # Use centralized PnL calculation with proper leverage handling
                pnl_percent = calculate_pnl_percent(entry_price, current_price, leverage)

                logger.info(
                    f"Price fetched: user={user_id}, current_price={current_price:.2f}, "
                    f"entry_price={entry_price:.2f}, leverage={leverage}x, "
                    f"calculated_pnl={pnl_percent:.4f}%"
                )

                return current_price, pnl_percent
            except Exception as e:
                logger.error(f"Price fetch failed in hook for user {user_id}: {e}", exc_info=True)
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
            original_pnl = pnl_percent
            pnl_percent = random.uniform(2.0, 5.0)
            await mark_onboarding_action(user_id, 'first_hook')
            logger.info(
                f"Guaranteed good catch for user {user_id}: "
                f"original_pnl={original_pnl:.4f}% → guaranteed_pnl={pnl_percent:.4f}%"
            )

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
                pond_pair=pond['trading_pair'] if pond else 'TAC/USDT',
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

            # Close position with fish ID (log before saving to DB)
            logger.info(
                f"Closing position: position_id={position['id']}, user={user_id}, "
                f"fish={fish_data['name']}, entry={entry_price:.2f}, exit={current_price:.2f}, "
                f"pnl_percent={pnl_percent:.4f}%, leverage={leverage}x, time={time_fishing}"
            )
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

            # Use ViewController to show CTA block
            from src.bot.ui.view_controller import get_view_controller
            from src.bot.ui.blocks import BlockData, CTABlock

            view = get_view_controller(context, user_id)

            # Store hook data for sharing (if group pond)
            if pond and pond.get('pond_type') == 'group' and pond.get('chat_id') and update.effective_chat.type == Chat.PRIVATE:
                context.user_data['share_hook_data'] = {
                    'fish_name': fish_data['name'],
                    'fish_emoji': fish_data['emoji'],
                    'pond_name': pond['name'],
                    'pond_chat_id': pond['chat_id'],
                    'pnl_percent': pnl_percent,
                    'username': username,
                    'card_image_bytes': card_image
                }

                # Show CTA with Share + Cast Again + MiniApp buttons
                await view.show_cta_block(
                    chat_id=user_id,
                    block_type=CTABlock,
                    data=BlockData(
                        header="🎉 Great Catch!",
                        body=f"You caught {fish_data['emoji']} {fish_data['name']}!",
                        buttons=[
                            ("📢 Share in Group (🪱 +1 BAIT)", "share_hook"),
                            ("🎣 Cast Again (🪱 -1 BAIT)", "quick_cast")
                        ],
                    web_app_buttons=get_miniapp_button(),
                        footer="Share it with your group to get +1 BAIT token reward."
                    )
                )
            else:
                # Show CTA with Cast + MiniApp buttons
                await view.show_cta_block(
                    chat_id=user_id,
                    block_type=CTABlock,
                    data=BlockData(
                        header="🎉 Fish Caught!",
                        body=f"You caught {fish_data['emoji']} {fish_data['name']}! Ready for another catch?",
                        buttons=[("🎣 Cast Again (🪱 -1 BAIT)", "quick_cast")],
                    web_app_buttons=get_miniapp_button()
                    )
                )

            # Transition to CATCH_COMPLETE state (use same state_machine instance from above)
            await state_machine.transition_to(UserState.CATCH_COMPLETE, context.user_data)
        else:
            # Emergency fallback - should never happen with expanded fish database
            await hook_task  # Wait for animation to complete
            await safe_reply(update, f"🎣 {username} caught somTACing strange! P&L: {pnl_percent:+.1f}%")
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
