"""
Formatting functions for fishing bot UI.
Contains functions to format fishing data for display.
"""

from src.utils.fishing_calculations import (
    calculate_pnl_dollars,
    format_fishing_duration_from_entry
)


def escape_markdown(text):
    """Simply return text without escaping - we'll use plain text mode"""
    return text if text else ""


def format_price(price: float) -> str:
    """
    Format price with dynamic precision based on magnitude.

    Handles everything from BTC (~$97,000) to meme coins (~$0.00002).

    Examples:
        $97,234.56 → "$97234.56" (BTC)
        $3,645.12 → "$3645.12" (ETH)
        $1.234 → "$1.234" (ADA, MATIC)
        $0.3456 → "$0.3456" (DOGE)
        $0.00002345 → "$0.00002345" (SHIB, PEPE)
    """
    if price >= 10:
        return f"{price:.2f}"
    elif price >= 1:
        return f"{price:.3f}"
    elif price >= 0.01:
        return f"{price:.4f}"
    elif price >= 0.0001:
        return f"{price:.6f}"
    else:
        # For very small prices, show up to 8 significant digits
        return f"{price:.8f}".rstrip('0').rstrip('.')


def format_fishing_complete_caption(username, catch_story, rod_name, leverage, pond_name, pond_pair, time_fishing, entry_price, current_price, pnl_percent, user_level=1):
    """
    Format fishing complete photo caption with new structured format.

    NOTE: time_fishing should be pre-formatted string (e.g., "5мин 30с")
    For raw entry_time, use format_fishing_duration_from_entry() first.
    """
    safe_username = username if username else "Angler"
    pnl_color = "🟢" if pnl_percent >= 0 else "🔴"

    # Calculate dollar P&L based on user level using centralized helper
    stake_amount = user_level * 1000
    dollar_pnl = calculate_pnl_dollars(entry_price, current_price, leverage, stake_amount)

    # Format PnL with dynamic precision
    if abs(pnl_percent) < 0.01:
        pnl_str = f"{pnl_percent:+.4f}%"
    elif abs(pnl_percent) < 0.1:
        pnl_str = f"{pnl_percent:+.3f}%"
    elif abs(pnl_percent) < 1:
        pnl_str = f"{pnl_percent:+.2f}%"
    else:
        pnl_str = f"{pnl_percent:+.1f}%"

    # Format dollar amount with proper sign placement
    if abs(dollar_pnl) < 0.01:
        dollar_str = f"${abs(dollar_pnl):.4f}" if dollar_pnl < 0 else f"${dollar_pnl:.4f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    elif abs(dollar_pnl) < 1:
        dollar_str = f"${abs(dollar_pnl):.2f}" if dollar_pnl < 0 else f"${dollar_pnl:.2f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    else:
        dollar_str = f"${abs(dollar_pnl):.0f}" if dollar_pnl < 0 else f"${dollar_pnl:.0f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"

    return (
        f"This is {catch_story}\n\n"
        f"💰 <b>PnL: {dollar_str} ({pnl_str})</b>\n\n"
        f"Rod: {rod_name} (leverage {leverage}x, stake ${stake_amount})\n"
        f"Fishery: {pond_name} ({pond_pair})\n"
        f"Fishing time: <b>{time_fishing}</b>\n"
        f"Position: ${format_price(entry_price)} → ${format_price(current_price)}"
    )


def format_enhanced_status_message(username, pond_name, pond_pair, rod_name, leverage, entry_price, current_price, current_pnl, time_fishing, user_level=1):
    """
    Format enhanced status command message with precise PnL and dollar amounts.

    NOTE: time_fishing should be pre-formatted string (e.g., "5мин 30с")
    For raw entry_time, use format_fishing_duration_from_entry() first.
    """
    safe_username = escape_markdown(username) if username else "Angler"
    pnl_color = "🟢" if current_pnl >= 0 else "🔴"

    # Calculate dollar P&L based on user level using centralized helper
    stake_amount = user_level * 1000
    dollar_pnl = calculate_pnl_dollars(entry_price, current_price, leverage, stake_amount)

    # Format PnL with dynamic precision (more decimal places for small changes)
    if abs(current_pnl) < 0.01:
        pnl_str = f"{current_pnl:+.4f}%"
    elif abs(current_pnl) < 0.1:
        pnl_str = f"{current_pnl:+.3f}%"
    elif abs(current_pnl) < 1:
        pnl_str = f"{current_pnl:+.2f}%"
    else:
        pnl_str = f"{current_pnl:+.1f}%"

    # Format dollar amount with proper sign placement
    if abs(dollar_pnl) < 0.01:
        dollar_str = f"${abs(dollar_pnl):.4f}" if dollar_pnl < 0 else f"${dollar_pnl:.4f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    elif abs(dollar_pnl) < 1:
        dollar_str = f"${abs(dollar_pnl):.2f}" if dollar_pnl < 0 else f"${dollar_pnl:.2f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    else:
        dollar_str = f"${abs(dollar_pnl):.0f}" if dollar_pnl < 0 else f"${dollar_pnl:.0f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"

    return (
        f"🎣 <b>Fishing status {safe_username}:</b>\n\n"
        f"Rod: {rod_name} (leverage {leverage}x, stake ${stake_amount})\n"
        f"Fishery: {pond_name} ({pond_pair})\n"
        f"⏱ Fishing time: <b>{time_fishing}</b>\n"
        f"📈 Position: ${format_price(entry_price)} → <b>${format_price(current_price)}</b>\n"
        f"{pnl_color} PnL: <b>{pnl_str} ({dollar_str})</b>"
    )


def format_no_fishing_status(username, bait_tokens, user_stats=None):
    """Format status when user is not fishing with rich statistics"""
    safe_username = escape_markdown(username) if username else "Angler"

    base_info = (
        f"🎣 <b>Fishing status {safe_username}:</b>\n\n"
        f"📊 Status: <i>Not fishing</i>\n"
        f"🪱 BAIT tokens: <b>{bait_tokens}</b>\n"
    )

    # Add user statistics if available
    if user_stats:
        stats_text = ""

        # Add user level and experience
        if 'user' in user_stats and user_stats['user']:
            level = user_stats['user'][2] if len(user_stats['user']) > 2 else 1
            experience = user_stats['user'][3] if len(user_stats['user']) > 3 else 0
            stats_text += f"⭐ Level: <b>{level}</b> (experience: {experience})\n"

        # Add fishing statistics
        if 'fishing' in user_stats and user_stats['fishing']:
            completed = user_stats['fishing'][1] or 0
            avg_pnl = user_stats['fishing'][2]
            best_pnl = user_stats['fishing'][3]
            worst_pnl = user_stats['fishing'][4]

            if completed > 0:
                stats_text += f"\n<b>📈 Fishing stats:</b>\n"
                stats_text += f"🎣 Total catches: <b>{completed}</b>\n"

                if avg_pnl is not None:
                    stats_text += f"📊 Average result: <b>{avg_pnl:+.2f}%</b>\n"
                if best_pnl is not None:
                    stats_text += f"🏆 Best catch: <b>{best_pnl:+.1f}%</b>\n"
                if worst_pnl is not None:
                    stats_text += f"💔 Worst catch: <b>{worst_pnl:+.1f}%</b>\n"

        # Add fish collection
        if 'fish_collection' in user_stats and user_stats['fish_collection']:
            collection = user_stats['fish_collection']
            total_fish = sum(fish[3] for fish in collection)
            unique_fish = len(collection)

            if total_fish > 0:
                stats_text += f"\n<b>🐟 Fish collection:</b>\n"
                stats_text += f"🎯 Total caught: <b>{total_fish}</b> fish\n"
                stats_text += f"🌈 Unique species: <b>{unique_fish}</b>\n"

                # Show top 3 most caught fish
                if len(collection) > 0:
                    stats_text += f"\n<b>Top-3 catches:</b>\n"
                    for i, fish in enumerate(collection[:3], 1):
                        fish_name, emoji, rarity, count = fish
                        rarity_emoji = {"trash": "🗑", "common": "⚪", "rare": "🔵",
                                      "epic": "🟣", "legendary": "🟡"}.get(rarity, "⚫")
                        stats_text += f"{i}. {emoji} {fish_name} {rarity_emoji} × {count}\n"

        # Add rod collection
        if 'rods' in user_stats and user_stats['rods']:
            rods = user_stats['rods']
            stats_text += f"\n<b>🎣 Rods in inventory:</b> {len(rods)}\n"
            best_rod = max(rods, key=lambda x: x[1]) if rods else None
            if best_rod:
                stats_text += f"💪 Best rod: <b>{best_rod[0]}</b> ({best_rod[1]}x)\n"

        return base_info + stats_text

    return base_info


def format_new_user_status(username):
    """Format status for new users"""
    safe_username = escape_markdown(username) if username else "Angler"

    return (
        f"🎣 <b>Fishing status {safe_username}:</b>\n\n"
        f"🆕 Status: <b>New player</b>\n"
        f"🪱 BAIT tokens: <b>10</b> (starter bonus)"
    )


async def get_full_start_message(user_id: int, username: str) -> str:
    """Build the complete start message for users who have claimed inheritance"""
    from src.database.db_manager import get_user

    try:
        # Get user statistics
        user = await get_user(user_id)
        bait_tokens = user['bait_tokens'] if user else 10

        # Create personalized start message (commands removed - available via buttons)
        start_message = f"""<b>🎣 Welcome to Hooked, {username}!</b>

Make leveraged trades and catch fish based on your performance - from trash catches to legendary sea monsters!

<b>🎮 How it works:</b>
• Add bot to any group to create fishing pond
• Cast line = open real trading position
• Watch prices like waiting for fish bite
• Close trade = discover your catch!

<b>💼 Your Status:</b>
🪱 BAIT tokens: <b>{bait_tokens}</b>

<i>Each cast costs 1 BAIT token!</i>"""

        return start_message

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error building full start message for user {user_id}: {e}")
        return f"<b>🎣 Welcome to Hooked, {username}!</b>\n\nReady to start fishing?"
