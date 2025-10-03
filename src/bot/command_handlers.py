"""
Command handlers registration for the fishing bot.
This module imports all command handlers from separate modules and provides registration functions.
"""

# Import all command handlers from refactored modules
from src.bot.fishing_commands import cast, hook, status
from src.bot.user_commands import start_command, help_command, pnl
from src.bot.leaderboard_commands import leaderboard, test_card
from src.bot.group_commands import (
    gofishing,
    pond_selection_callback,
    join_fishing_callback,
    onboarding_start_callback,
    onboarding_skip_callback,
    onboarding_claim_bonus_callback,
    claim_gear_reward_callback,
    onboarding_claim_reward_callback,
    onboarding_continue_cast_callback,
    onboarding_send_cast_callback,
    onboarding_send_hook_callback,
)
from src.bot.payment_commands import (
    handle_pre_checkout_query, handle_successful_payment, buy_bait_command, 
    buy_bait_callback, transactions_command, send_low_bait_purchase_offer
)

# Re-export all handlers for backward compatibility
__all__ = [
    'cast', 'hook', 'status',
    'start_command', 'help_command', 'pnl',
    'leaderboard', 'test_card',
    'gofishing', 'pond_selection_callback', 'join_fishing_callback',
    'onboarding_start_callback', 'onboarding_skip_callback', 'onboarding_claim_bonus_callback',
    'claim_gear_reward_callback', 'onboarding_claim_reward_callback', 'onboarding_continue_cast_callback',
    'onboarding_send_cast_callback', 'onboarding_send_hook_callback',
    'handle_pre_checkout_query', 'handle_successful_payment', 'buy_bait_command',
    'buy_bait_callback', 'transactions_command', 'send_low_bait_purchase_offer'
]
