"""
Formatting functions for fishing bot UI.
Contains functions to format fishing data for display.
"""


def escape_markdown(text):
    """Simply return text without escaping - we'll use plain text mode"""
    return text if text else ""


def format_fishing_complete_caption(username, catch_story, rod_name, leverage, pond_name, pond_pair, time_fishing, entry_price, current_price, pnl_percent, user_level=1):
    """Format fishing complete photo caption with new structured format"""
    safe_username = username if username else "Angler"
    pnl_color = "🟢" if pnl_percent >= 0 else "🔴"

    # Calculate dollar P&L based on user level
    from src.utils.crypto_price import calculate_dollar_pnl
    stake_amount = user_level * 1000
    dollar_pnl = calculate_dollar_pnl(entry_price, current_price, leverage, stake_amount)

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
        f"Position: ${entry_price:.2f} → ${current_price:.2f}\n\n"
        f"🚀 Use /cast to start fishing!"
    )


def format_enhanced_status_message(username, pond_name, pond_pair, rod_name, leverage, entry_price, current_price, current_pnl, time_fishing, user_level=1):
    """Format enhanced status command message with precise PnL and dollar amounts"""
    safe_username = escape_markdown(username) if username else "Angler"
    pnl_color = "🟢" if current_pnl >= 0 else "🔴"

    # Calculate dollar P&L based on user level
    from src.utils.crypto_price import calculate_dollar_pnl
    stake_amount = user_level * 1000
    dollar_pnl = calculate_dollar_pnl(entry_price, current_price, leverage, stake_amount)

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
        f"📈 Position: ${entry_price:.2f} → <b>${current_price:.2f}</b>\n"
        f"{pnl_color} PnL: <b>{pnl_str} ({dollar_str})</b>\n\n"
        f"🪝 Use /hook to pull in your catch!"
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

        return base_info + stats_text + "\n🚀 Use /cast to start fishing!"

    return base_info + "\n🚀 Use /cast to start fishing!"


def format_new_user_status(username):
    """Format status for new users"""
    safe_username = escape_markdown(username) if username else "Angler"

    return (
        f"🎣 <b>Fishing status {safe_username}:</b>\n\n"
        f"🆕 Status: <b>New player</b>\n"
        f"🪱 BAIT tokens: <b>10</b> (starter bonus)\n\n"
        f"🚀 Use /cast to start fishing!"
    )


async def get_full_start_message(user_id: int, username: str) -> str:
    """Build the complete start message for users who have claimed inheritance"""
    from src.database.db_manager import (
        get_user, get_active_position, get_user_rods, get_user_group_ponds
    )

    try:
        # Get user statistics
        user = await get_user(user_id)
        user_level = user['level'] if user else 1
        bait_tokens = user['bait_tokens'] if user else 10
        experience = user['experience'] if user else 0

        # Check if user is currently fishing
        active_position = await get_active_position(user_id)

        # Get user's available equipment count
        user_rods = await get_user_rods(user_id)
        user_group_ponds = await get_user_group_ponds(user_id)
        rods_count = len(user_rods) if user_rods else 0
        ponds_count = len(user_group_ponds) if user_group_ponds else 0

        # Create personalized start message
        status_emoji = "🎣" if active_position else "🌊"
        fishing_status = "Currently fishing!" if active_position else "Ready to fish"

        start_message = f"""<b>🎣 Welcome to Hooked Crypto, {username}!</b>
Make leveraged trades and catch fish based on your performance - from trash catches to legendary sea monsters!

<b>🎮 How it works:</b>
- Add bot to any group to create fishing pond
- Cast line = open real trading position
- Watch prices like waiting for fish bite
- Close trade = discover your catch!

<b>🎣 Quick Commands:</b>
- /cast - Start fishing (make trade)
- /hook - Close position & see catch
- /leaderboard - Top fishermen
- /help - This guide

<i>Each cast costs 1 $BAIT token!</i>"""

        return start_message

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error building full start message for user {user_id}: {e}")
        return f"<b>🎣 Welcome to Hooked Crypto, {username}!</b>\n\nUse /help for game guide."
