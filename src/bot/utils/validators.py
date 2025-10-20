"""
Validation functions for fishing bot.
Contains reusable validation logic for BAIT, positions, rate limits, etc.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def validate_fishing_preconditions(user_id: int, username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate all preconditions before starting fishing.
    Returns (is_valid, error_message)
    """
    from src.database.db_manager import (
        get_user, get_active_position, check_rate_limit,
        can_use_free_cast, ensure_user_has_level, give_starter_rod
    )

    # Check rate limit
    if not await check_rate_limit(user_id):
        return False, "⏳ Too many requests! Wait a bit before the next command."

    # Ensure user has level and starter rod
    await ensure_user_has_level(user_id)
    await give_starter_rod(user_id)
    user = await get_user(user_id)

    if not user:
        return False, "🎣 User not found. Please try /start again."

    # Check if user can use free tutorial cast
    can_use_free = await can_use_free_cast(user_id)

    # Check if user has enough BAIT (skip check for free tutorial cast)
    if not can_use_free and user['bait_tokens'] <= 0:
        return False, "NO_BAIT"  # Special marker for low bait offer

    # Check if user is already fishing
    active_position = await get_active_position(user_id)
    if active_position:
        return False, f"🎣 {username} already has a fishing rod in the water! Use /hook to pull out the catch or /status to check progress."

    return True, None


async def validate_hook_preconditions(user_id: int, username: str) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Validate all preconditions before hooking.
    Returns (is_valid, error_message, position)
    """
    from src.database.db_manager import (
        get_active_position, check_rate_limit, check_hook_rate_limit
    )

    # Check general rate limit
    if not await check_rate_limit(user_id):
        return False, "⏳ Too many requests! Wait a bit before the next command.", None

    # Check hook-specific rate limit (more restrictive)
    if not await check_hook_rate_limit(user_id):
        return False, "🎣 Easy there, fisherman! Hook attempts are limited to prevent spam.\n\n<i>Max 3 hook attempts per minute. Give the fish a chance to bite! 🐟</i>", None

    # Check if user is fishing
    position = await get_active_position(user_id)
    if not position:
        return False, f"🎣 {username} is not fishing! Use /cast to throw the fishing rod.", None

    return True, None, position


async def check_quick_fishing(position: dict, base_currency: str, entry_price: float, leverage: float) -> Tuple[bool, Optional[str]]:
    """
    Check if user is trying to fish too quickly (< 1 minute with minimal P&L change).
    Returns (should_block, message)
    """
    from src.utils.crypto_price import get_crypto_price
    from src.utils.fishing_calculations import calculate_pnl, format_time_fishing, get_fishing_time_seconds
    from src.bot.ui.messages import get_quick_fishing_message

    time_fishing = format_time_fishing(position['entry_time'])
    fishing_time_seconds = get_fishing_time_seconds(position['entry_time'])

    # Only check if fishing time is less than 60 seconds
    if fishing_time_seconds >= 60:
        return False, None

    try:
        quick_price = await get_crypto_price(base_currency)
        quick_pnl = calculate_pnl(entry_price, quick_price, leverage)

        # Block if P&L change is minimal
        if abs(quick_pnl) < 0.1:
            quick_message = get_quick_fishing_message(fishing_time_seconds)
            message = f"{quick_message}\n\n⏰ <b>Fishing Time:</b> {time_fishing}\n📈 <b>P&L:</b> {quick_pnl:+.4f}%\n\n<i>Wait at least 1 minute for the market to move!</i>"
            return True, message
    except Exception as e:
        logger.warning(f"Quick fishing check failed, allowing hook anyway: {e}")

    return False, None


async def ensure_user_exists(user_id: int, username: str) -> dict:
    """
    Ensure user exists in database, create if not exists.
    Returns user dict.
    """
    from src.database.db_manager import get_user, create_user, ensure_user_has_level, give_starter_rod

    user = await get_user(user_id)
    if not user:
        await create_user(user_id, username)
        user = await get_user(user_id)
    else:
        # Ensure existing user has level and starter rod
        await ensure_user_has_level(user_id)
        await give_starter_rod(user_id)
        user = await get_user(user_id)  # Refresh user data

    return user
