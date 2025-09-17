"""
Command handlers registration for the fishing bot.
This module imports all command handlers from separate modules and provides registration functions.
"""

# Import all command handlers from refactored modules
from src.bot.fishing_commands import cast, hook, status
from src.bot.user_commands import start_command, help_command, pnl
from src.bot.leaderboard_commands import leaderboard, test_card
from src.bot.group_commands import gofishing, pond_selection_callback, join_fishing_callback

# Re-export all handlers for backward compatibility
__all__ = [
    'cast', 'hook', 'status',
    'start_command', 'help_command', 'pnl',
    'leaderboard', 'test_card',
    'gofishing', 'pond_selection_callback', 'join_fishing_callback'
]