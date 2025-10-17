"""
Centralized fishing calculations module.
All PnL and time calculations happen here with proper UTC timezone handling.
"""

import logging
from datetime import datetime, timezone
from typing import Union

logger = logging.getLogger(__name__)


# ==================== PNL CALCULATIONS ====================

def calculate_pnl_percent(entry_price: float, exit_price: float, leverage: float = 2.0) -> float:
    """
    Calculate P&L percentage with leverage.

    Args:
        entry_price: Entry price for the position
        exit_price: Exit price for the position
        leverage: Leverage multiplier (positive for long, negative for short)

    Returns:
        P&L percentage (e.g., 5.0 for +5%, -3.2 for -3.2%)
    """
    if entry_price <= 0:
        logger.error(f"Invalid entry_price: {entry_price}")
        return 0.0

    price_change_percent = ((exit_price - entry_price) / entry_price) * 100
    leveraged_pnl = price_change_percent * abs(leverage)  # Use abs to handle negative leverage

    # If leverage is negative (short position), invert the PnL
    if leverage < 0:
        leveraged_pnl = -leveraged_pnl

    logger.debug(
        f"PnL calculation: entry={entry_price:.2f}, exit={exit_price:.2f}, "
        f"leverage={leverage}x, price_change={price_change_percent:.4f}%, "
        f"leveraged_pnl={leveraged_pnl:.4f}%"
    )

    return leveraged_pnl


def calculate_pnl_dollars(
    entry_price: float,
    exit_price: float,
    leverage: float = 2.0,
    stake_usd: float = 1000.0
) -> float:
    """
    Calculate P&L in dollars based on stake amount.

    Args:
        entry_price: Entry price for the position
        exit_price: Exit price for the position
        leverage: Leverage multiplier
        stake_usd: Stake amount in USD

    Returns:
        P&L in dollars (e.g., 50.0 for +$50, -32.5 for -$32.5)
    """
    if entry_price <= 0:
        logger.error(f"Invalid entry_price: {entry_price}")
        return 0.0

    price_change_fraction = (exit_price - entry_price) / entry_price
    leveraged_change = price_change_fraction * abs(leverage)

    # If leverage is negative (short position), invert the change
    if leverage < 0:
        leveraged_change = -leveraged_change

    dollar_pnl = stake_usd * leveraged_change

    logger.debug(
        f"Dollar PnL calculation: entry={entry_price:.2f}, exit={exit_price:.2f}, "
        f"leverage={leverage}x, stake=${stake_usd:.0f}, dollar_pnl=${dollar_pnl:.2f}"
    )

    return dollar_pnl


def get_pnl_color(pnl_percent: float) -> str:
    """Get color indicator emoji for P&L"""
    if pnl_percent > 0:
        return "🟢"
    elif pnl_percent < 0:
        return "🔴"
    else:
        return "⚪"


# ==================== TIME CALCULATIONS ====================

def normalize_to_utc(dt: Union[datetime, str]) -> datetime:
    """
    Normalize datetime to UTC timezone-aware datetime.

    Args:
        dt: datetime object or ISO format string

    Returns:
        UTC timezone-aware datetime
    """
    if isinstance(dt, str):
        # Parse ISO format string
        if 'T' in dt:
            # ISO format with potential timezone
            dt_obj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        else:
            # SQLite/PostgreSQL format (YYYY-MM-DD HH:MM:SS)
            # Assume UTC if no timezone info
            dt_obj = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    else:
        dt_obj = dt

    # Ensure timezone-aware in UTC
    if dt_obj.tzinfo is None:
        # Naive datetime - assume UTC
        logger.debug(f"Converting naive datetime to UTC: {dt_obj}")
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    elif dt_obj.tzinfo != timezone.utc:
        # Convert to UTC (handles PostgreSQL timestamps with local timezone)
        original_tz = dt_obj.tzinfo
        dt_obj = dt_obj.astimezone(timezone.utc)
        logger.debug(f"Converted {original_tz} to UTC: {dt_obj}")

    return dt_obj


def get_fishing_duration_seconds(entry_time: Union[datetime, str]) -> int:
    """
    Get fishing duration in seconds from entry time to now (UTC).

    Args:
        entry_time: Entry timestamp (datetime or string)

    Returns:
        Duration in seconds (always >= 0)
    """
    try:
        entry_dt = normalize_to_utc(entry_time)
        now_utc = datetime.now(timezone.utc)

        diff = now_utc - entry_dt
        total_seconds = int(diff.total_seconds())

        # Ensure non-negative (clock skew protection)
        if total_seconds < 0:
            logger.warning(
                f"Negative fishing time detected: entry={entry_dt.isoformat()}, "
                f"now={now_utc.isoformat()}, diff={total_seconds}s. Returning 0."
            )
            return 0

        logger.debug(
            f"Fishing duration: entry={entry_dt.isoformat()}, "
            f"now={now_utc.isoformat()}, duration={total_seconds}s"
        )

        return total_seconds

    except Exception as e:
        logger.error(f"Error calculating fishing duration: {e}", exc_info=True)
        return 0


def format_fishing_duration(total_seconds: int) -> str:
    """
    Format fishing duration in seconds to human-readable string (Russian).

    Args:
        total_seconds: Duration in seconds

    Returns:
        Formatted string like "45с", "5мин 30с", "2ч 15мин"
    """
    if total_seconds < 0:
        total_seconds = 0

    if total_seconds < 60:
        return f"{total_seconds}с"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}мин {seconds}с"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}ч {minutes}мин"


def format_fishing_duration_from_entry(entry_time: Union[datetime, str]) -> str:
    """
    Calculate and format fishing duration from entry time.
    Convenience function combining get_fishing_duration_seconds and format_fishing_duration.

    Args:
        entry_time: Entry timestamp (datetime or string)

    Returns:
        Formatted duration string
    """
    total_seconds = get_fishing_duration_seconds(entry_time)
    return format_fishing_duration(total_seconds)


# ==================== LEGACY COMPATIBILITY ====================
# Keep these for backward compatibility during migration

def calculate_pnl(entry_price: float, exit_price: float, leverage: float = 2.0) -> float:
    """Legacy alias for calculate_pnl_percent"""
    return calculate_pnl_percent(entry_price, exit_price, leverage)


def calculate_dollar_pnl(
    entry_price: float,
    exit_price: float,
    leverage: float = 2.0,
    stake_usd: float = 1000.0
) -> float:
    """Legacy alias for calculate_pnl_dollars"""
    return calculate_pnl_dollars(entry_price, exit_price, leverage, stake_usd)


def get_fishing_time_seconds(entry_time: Union[datetime, str]) -> int:
    """Legacy alias for get_fishing_duration_seconds"""
    return get_fishing_duration_seconds(entry_time)


def format_time_fishing(entry_time: Union[datetime, str]) -> str:
    """Legacy alias for format_fishing_duration_from_entry"""
    return format_fishing_duration_from_entry(entry_time)
