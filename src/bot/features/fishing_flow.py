"""
Fishing flow helpers for the fishing bot.
Contains reusable fishing logic for private chat operations triggered from groups.
"""

import asyncio
import logging
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_user, get_active_position, use_bait, create_position_with_gear, close_position,
    ensure_user_has_level, give_starter_rod, get_pond_by_id, get_rod_by_id,
    get_suitable_fish, check_hook_rate_limit, ensure_user_has_active_rod,
    can_use_free_cast, mark_onboarding_action, can_use_guaranteed_hook, should_get_special_catch,
    award_first_cast_reward
)
from src.utils.crypto_price import get_crypto_price, calculate_pnl, format_time_fishing, get_fishing_time_seconds, get_price_error_message
from src.bot.ui.messages import get_catch_story_from_db, get_quick_fishing_message
from src.bot.ui.formatters import format_fishing_complete_caption
from src.generators.fish_card_generator import generate_fish_card_from_db
from src.bot.random_messages import get_random_cast_appendix, get_random_hook_appendix
from src.bot.features.onboarding import handle_onboarding_command

logger = logging.getLogger(__name__)

async def start_private_fishing_from_group(user_id: int, username: str, pond_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start fishing process in private chat from group command"""
    try:
        # Ensure user has level and starter rod
        await ensure_user_has_level(user_id)
        await give_starter_rod(user_id)
        user = await get_user(user_id)

        # Check if user has enough BAIT
        if user['bait_tokens'] <= 0:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎣 No $BAIT tokens! Use /buy command to purchase more 🪱"
            )
            return

        # Check if user is already fishing
        active_position = await get_active_position(user_id)
        if active_position:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎣 {username} already has a fishing rod in the water! Use /hook to pull out the catch or /status to check progress."
            )
            return

        # Check if user can use free tutorial cast
        can_use_free = await can_use_free_cast(user_id)

        # Use bait (skip for free tutorial cast)
        if can_use_free:
            # Mark that user used their free cast
            await mark_onboarding_action(user_id, 'first_cast')
        else:
            # Normal bait usage
            if not await use_bait(user_id):
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🎣 Failed to use bait. Try again!"
                )
                return

        # Get user's active rod
        active_rod = await ensure_user_has_active_rod(user_id)

        if not active_rod:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎣 Failed to find active fishing rod! Try again."
            )
            return

        # Get pond info
        pond = await get_pond_by_id(pond_id)
        if not pond:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎣 Pond not found! Try again."
            )
            return

        # Get current price and create position
        base_currency = pond['base_currency']
        current_price = await get_crypto_price(base_currency)

        # Create position
        await create_position_with_gear(user_id, pond_id, active_rod['id'], current_price)

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
            await animate_casting_sequence(
                dummy_message,
                username,
                user['level'] if user else 1,
                current_price,
                pond_id=pond['id'],
                rod_id=active_rod['id']
            )
        except Exception as anim_err:
            logger.warning(f"Cast animation failed for user {user_id}: {anim_err}")

        # Check if user gets first cast reward (gear unlock)
        cast_reward_message = await award_first_cast_reward(user_id)

        # Handle onboarding progression if applicable
        onboarding_result = await handle_onboarding_command(user_id, '/cast')
        if isinstance(onboarding_result, dict) and onboarding_result.get('send_message'):
            # In onboarding - show gear claim button if applicable
            if cast_reward_message:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                # Store reward message for later display
                context.user_data['pending_gear_reward'] = cast_reward_message
                # Store onboarding result to show after gear claim
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
                # No gear reward - show tutorial message directly
                await asyncio.sleep(3)
                sent_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=onboarding_result['send_message'],
                    reply_markup=onboarding_result.get('reply_markup'),
                    parse_mode='HTML'
                )
                # Store message ID for later deletion
                context.user_data['tutorial_message_id'] = sent_message.message_id
        else:
            # Not in onboarding - show regular rewards/messages
            if cast_reward_message:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                # Store reward message for later display
                context.user_data['pending_gear_reward'] = cast_reward_message

                gear_keyboard = [[InlineKeyboardButton("🎣 Claim gear", callback_data="claim_gear_reward")]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🎁 <b>New gear unlocked!</b>\n\nClaim your starter rods now.",
                    reply_markup=InlineKeyboardMarkup(gear_keyboard),
                    parse_mode='HTML'
                )
            elif can_use_free:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✨ First cast is free. Wait for the right moment and use /hook when ready!",
                    parse_mode='HTML'
                )

        # Send group notification if pond is a group pond
        if pond.get('pond_type') == 'group' and pond.get('chat_id'):
            try:
                cast_appendix = get_random_cast_appendix()
                group_message = f"🎣 <b>{username}</b> cast their rod into <b>{pond['name']}</b>.{cast_appendix}"
                await context.bot.send_message(
                    chat_id=pond['chat_id'],
                    text=group_message,
                    parse_mode='HTML',
                    disable_notification=True
                )
            except Exception as e:
                logger.warning(f"Could not send group cast notification: {e}")

        logger.info(f"User {username} started fishing from group in private chat, pond {pond_id}")

    except Exception as e:
        logger.error(f"Error in start_private_fishing_from_group for user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="🎣 Something went wrong! Try /cast again."
        )

async def complete_private_hook_from_group(user_id: int, username: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Complete hook process in private chat from group command"""
    try:
        # Get active position
        position = await get_active_position(user_id)
        if not position:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎣 {username} is not fishing! Use /cast to throw the fishing rod."
            )
            return

        # Check hook rate limit
        if not await check_hook_rate_limit(user_id):
            await context.bot.send_message(
                chat_id=user_id,
                text="🎣 Easy there, fisherman! Hook attempts are limited to prevent spam.\n\n<i>Max 3 hook attempts per minute. Give the fish a chance to bite! 🐟</i>",
                parse_mode='HTML'
            )
            return

        # Get pond and rod data for the position
        pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
        rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None

        # Get base currency for price fetching
        base_currency = pond['base_currency'] if pond else 'ETH'
        leverage = rod['leverage'] if rod else 1.5
        entry_price = position['entry_price']

        # Pre-calculate time for quick fishing check
        time_fishing = format_time_fishing(position['entry_time'])
        fishing_time_seconds = get_fishing_time_seconds(position['entry_time'])

        # QUICK FISHING CHECK - must be done BEFORE animation starts!
        if fishing_time_seconds < 60:
            try:
                quick_price = await get_crypto_price(base_currency)
                quick_pnl = calculate_pnl(entry_price, quick_price, leverage)

                if abs(quick_pnl) < 0.1:
                    quick_message = get_quick_fishing_message(fishing_time_seconds)
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"{quick_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n📈 <b>P&L:</b> {quick_pnl:+.4f}%\n\n<i>Wait at least 1 minute for the market to move!</i>",
                        parse_mode='HTML'
                    )
                    return
            except Exception as e:
                logger.warning(f"Quick fishing check failed, allowing hook anyway: {e}")

        # Get user level
        user = await get_user(user_id)
        user_level = user['level'] if user else 1

        # Start PARALLEL tasks immediately - no blocking!
        # 1. Hook animation (simplified for private chat)
        hook_task = asyncio.create_task(
            private_hook_animation(context, user_id, username)
        )

        # 2. Price fetching with retry
        async def fetch_price_and_calculate():
            try:
                current_price = await get_crypto_price(base_currency)
                pnl_percent = calculate_pnl(entry_price, current_price, leverage)
                return current_price, pnl_percent
            except Exception as e:
                logger.error(f"Price fetch failed in private hook: {e}")
                return "ERROR", None

        price_task = asyncio.create_task(fetch_price_and_calculate())

        # Wait for price calculation to complete (runs in parallel with animation)
        current_price, pnl_percent = await price_task

        # Handle price fetch failure
        if current_price == "ERROR":
            await hook_task  # Wait for animation to complete
            error_message = get_price_error_message()
            await context.bot.send_message(
                chat_id=user_id,
                text=f"{error_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n\n<i>Try pulling the hook again!</i>",
                parse_mode='HTML'
            )
            return

        # Check for special catch (like secret letter during onboarding)
        special_catch_item = await should_get_special_catch(user_id)
        if special_catch_item:
            logger.info(f"User {user_id} should get special catch: {special_catch_item}")

            # Wait for animation to complete
            await hook_task

            # Send special catch message instead of fish card
            special_message = f"📜 <b>You caught a {special_catch_item}!</b>\n\n<i>This is a special catch from your onboarding journey.</i>"
            await context.bot.send_message(
                chat_id=user_id,
                text=special_message,
                parse_mode='HTML'
            )

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
        fish_data = await get_suitable_fish(
            pnl_percent,
            user_level,
            position['pond_id'] if position['pond_id'] else 1,
            position['rod_id'] if position['rod_id'] else 1
        )

        if not fish_data:
            logger.warning(f"No suitable fish found for PnL {pnl_percent}%, using fallback")
            fish_data = await get_suitable_fish(pnl_percent, 1, 1, 1)

        if fish_data:
            # Generate the catch story from database
            catch_story = get_catch_story_from_db(fish_data)

            # Create complete caption using structured format
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
            await hook_task
            card_image = await card_task

            # Send the fish card to private chat
            if card_image:
                try:
                    from io import BytesIO
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=BytesIO(card_image),
                        caption=complete_story,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Failed to send fish card to private chat: {e}")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=complete_story,
                        parse_mode='HTML'
                    )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=complete_story,
                    parse_mode='HTML'
                )

            # Send group notification if this was a group pond
            if pond and pond.get('pond_type') == 'group' and pond.get('chat_id'):
                try:
                    pnl_color = "🟢" if pnl_percent > 0 else "🔴" if pnl_percent < 0 else "⚪"
                    hook_appendix = get_random_hook_appendix()
                    group_notification = f"🎣 <b>{username}</b> caught {fish_data['emoji']} {fish_data['name']} from <b>{pond['name']}</b>! {pnl_color} P&L: {pnl_percent:+.1f}%{hook_appendix}"

                    await context.bot.send_message(
                        chat_id=pond['chat_id'],
                        text=group_notification,
                        parse_mode='HTML',
                        disable_notification=True
                    )
                except Exception as e:
                    logger.warning(f"Could not send group hook notification: {e}")
        else:
            # Emergency fallback
            await hook_task
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎣 {username} caught something strange! P&L: {pnl_percent:+.1f}%"
            )
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

        logger.info(f"User {username} completed hook from group in private chat")

    except Exception as e:
        logger.error(f"Error in complete_private_hook_from_group for user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="🎣 Error pulling out fish! Try /hook again."
        )

async def private_hook_animation(context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str):
    """Simplified hook animation for private chat"""
    try:
        # Simple text-based animation for private chat
        animation_steps = [
            f"🎣 <b>{username}</b> is pulling the line...",
            f"🌊 Something's biting! <b>{username}</b> fights the catch...",
            f"⚡ The line is tense! <b>{username}</b> reels it in...",
            f"🐟 Almost got it! <b>{username}</b> pulls harder...",
            f"🎯 <b>Success!</b> <b>{username}</b> caught something!"
        ]

        for i, step in enumerate(animation_steps):
            await context.bot.send_message(
                chat_id=user_id,
                text=step,
                parse_mode='HTML'
            )
            if i < len(animation_steps) - 1:  # Don't sleep after the last step
                await asyncio.sleep(2.5)  # Match original animation timing

    except Exception as e:
        logger.warning(f"Error in private hook animation: {e}")


# ===== POND SELECTION CALLBACK =====

async def pond_selection_callback(update, context):
    """Handle pond selection callback from private chat"""
    import asyncio
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from src.database.db_manager import (
        get_user, get_active_position, use_bait, create_position_with_gear,
        get_pond_by_id, ensure_user_has_active_rod, can_use_free_cast,
        mark_onboarding_action, award_first_cast_reward
    )
    from src.utils.crypto_price import get_crypto_price
    from src.bot.ui.animations import animate_casting_sequence
    from src.bot.random_messages import get_random_cast_appendix
    from src.bot.features.onboarding import handle_onboarding_command

    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name

        # Parse callback data: "select_pond_<pond_id>"
        if not query.data.startswith("select_pond_"):
            return

        pond_id = int(query.data.split("_")[-1])

        user = await get_user(user_id)
        user_level = user['level'] if user else 1

        # Get pond info
        pond = await get_pond_by_id(pond_id)
        if not pond:
            await query.edit_message_text("❌ Pond not found!")
            return

        # Check if user has active position
        active_position = await get_active_position(user_id)
        if active_position:
            await query.edit_message_text(f"🎣 You already have a fishing rod in the water! Use /hook to pull out the catch.")
            return

        # Check if user can use free tutorial cast
        can_use_free = await can_use_free_cast(user_id)

        # Use bait (skip for free tutorial cast)
        if can_use_free:
            # Mark that user used their free cast
            await mark_onboarding_action(user_id, 'first_cast')
        else:
            # Normal bait usage
            if not await use_bait(user_id):
                await query.edit_message_text("🎣 No $BAIT tokens! Use /buy command to purchase more 🪱")
                return

        # Get user's active rod
        active_rod = await ensure_user_has_active_rod(user_id)

        if not active_rod:
            await query.edit_message_text("🎣 Failed to find active fishing rod! Try again.")
            return

        # Get current price and create position
        base_currency = pond['base_currency']
        current_price = await get_crypto_price(base_currency)

        # Create position
        await create_position_with_gear(user_id, pond_id, active_rod['id'], current_price)

        await query.edit_message_text(
            f"🎣 <b>{username}</b> cast their rod into <b>{pond['name']}!</b>\n\n"
            f"🌊 <b>Pond:</b> {pond['name']}\n"
            f"🎣 <b>Rod:</b> {active_rod['name']}\n"
            f"💰 <b>Entry Price:</b> ${current_price:,.4f}\n\n"
            f"<i>Use /hook when you're ready to catch the fish!</i>"
        )

        # Trigger casting animation in parallel
        try:
            await animate_casting_sequence(
                query.message,
                username,
                user_level,
                current_price,
                pond_id=pond['id'],
                rod_id=active_rod['id']
            )
        except Exception as anim_err:
            logger.warning(f"Cast animation failed for user {user_id}: {anim_err}")

        # If pond is a group pond, send notification to the group
        if pond.get('pond_type') == 'group' and pond.get('chat_id'):
            try:
                cast_appendix = get_random_cast_appendix()
                await context.bot.send_message(
                    chat_id=pond['chat_id'],
                    text=f"🎣 <b>{username}</b> cast their rod into <b>{pond['name']}</b>.{cast_appendix}",
                    parse_mode='HTML',
                    disable_notification=True
                )
            except Exception as e:
                logger.warning(f"Could not send group notification: {e}")

        # Check if user gets first cast reward (gear unlock)
        cast_reward_message = await award_first_cast_reward(user_id)

        # Handle onboarding progression if applicable
        onboarding_result = await handle_onboarding_command(user_id, '/cast')
        if isinstance(onboarding_result, dict) and onboarding_result.get('send_message'):
            # In onboarding - show gear claim button if applicable
            if cast_reward_message:
                # Store reward message for later display
                context.user_data['pending_gear_reward'] = cast_reward_message
                # Store onboarding result to show after gear claim
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
                # No gear reward - show tutorial message directly
                await asyncio.sleep(3)
                sent_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=onboarding_result['send_message'],
                    reply_markup=onboarding_result.get('reply_markup'),
                    parse_mode='HTML'
                )
                # Store message ID for later deletion
                context.user_data['tutorial_message_id'] = sent_message.message_id
        else:
            # Not in onboarding - show regular reward
            if cast_reward_message:
                # Store reward message for later display
                context.user_data['pending_gear_reward'] = cast_reward_message

                gear_keyboard = [[InlineKeyboardButton("🎣 Claim gear", callback_data="claim_gear_reward")]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🎁 <b>New gear unlocked!</b>\n\nClaim your starter rods now.",
                    reply_markup=InlineKeyboardMarkup(gear_keyboard),
                    parse_mode='HTML'
                )

    except Exception as e:
        logger.error(f"Error in pond selection callback: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text("🎣 Error selecting pond! Try again.")
