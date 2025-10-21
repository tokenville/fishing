"""
Centralized handler registration for the fishing bot.
Registers all commands, callbacks, and event handlers.
"""

from telegram.ext import Application, CommandHandler, ChatMemberHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters


def register_all_handlers(application: Application) -> None:
    """Register all bot handlers in one place"""

    # Import commands
    from src.bot.commands.cast import cast
    from src.bot.commands.hook import hook
    from src.bot.commands.status import status
    from src.bot.commands.start import start_command, help_command, pnl, skip_onboarding_command
    from src.bot.commands.leaderboard import leaderboard
    from src.bot.commands.dev import test_card, chatinfo
    from src.bot.commands.payments import (
        handle_pre_checkout_query, handle_successful_payment,
        buy_bait_command, buy_bait_callback, transactions_command
    )
    from src.bot.features.group_management import (
        my_chat_member_handler, chat_member_handler,
        gofishing, join_fishing_callback
    )
    from src.bot.commands.cast import pond_selection_callback
    from src.bot.features.share_handlers import share_cast_callback, share_hook_callback
    from src.bot.features.onboarding import (
        onboarding_start_callback, onboarding_skip_callback, onboarding_claim_bonus_callback,
        claim_gear_reward_callback, onboarding_claim_reward_callback, onboarding_continue_cast_callback,
        onboarding_send_cast_callback, onboarding_send_hook_callback, restart_onboarding_callback
    )
    from src.bot.features.quick_actions import (
        quick_cast_callback, quick_hook_callback, show_status_callback,
        quick_buy_callback, cancel_action_callback, update_status_callback,
        quick_pnl_callback, quick_help_callback
    )

    # Command handlers
    application.add_handler(CommandHandler("cast", cast))
    application.add_handler(CommandHandler("hook", hook))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("test_card", test_card))
    application.add_handler(CommandHandler("chatinfo", chatinfo))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("pnl", pnl))
    application.add_handler(CommandHandler("gofishing", gofishing))
    application.add_handler(CommandHandler("buy", buy_bait_command))
    application.add_handler(CommandHandler("transactions", transactions_command))
    application.add_handler(CommandHandler("skip", skip_onboarding_command))

    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout_query))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))

    # WebApp data handler
    from main import handle_webapp_data
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    # Group management handlers
    application.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(chat_member_handler, ChatMemberHandler.CHAT_MEMBER))

    # Callback handlers
    application.add_handler(CallbackQueryHandler(pond_selection_callback, pattern=r"^select_pond_"))
    application.add_handler(CallbackQueryHandler(join_fishing_callback, pattern=r"^join_fishing_"))
    application.add_handler(CallbackQueryHandler(buy_bait_callback, pattern=r"^buy_bait_"))
    application.add_handler(CallbackQueryHandler(share_cast_callback, pattern=r"^share_cast$"))
    application.add_handler(CallbackQueryHandler(share_hook_callback, pattern=r"^share_hook$"))

    # Quick action callback handlers
    application.add_handler(CallbackQueryHandler(quick_cast_callback, pattern=r"^quick_cast$"))
    application.add_handler(CallbackQueryHandler(quick_hook_callback, pattern=r"^quick_hook$"))
    application.add_handler(CallbackQueryHandler(show_status_callback, pattern=r"^show_status$"))
    application.add_handler(CallbackQueryHandler(update_status_callback, pattern=r"^update_status$"))
    application.add_handler(CallbackQueryHandler(quick_buy_callback, pattern=r"^quick_buy$"))
    application.add_handler(CallbackQueryHandler(quick_pnl_callback, pattern=r"^quick_pnl$"))
    application.add_handler(CallbackQueryHandler(quick_help_callback, pattern=r"^quick_help$"))
    application.add_handler(CallbackQueryHandler(cancel_action_callback, pattern=r"^cancel_action$"))

    # Onboarding callback handlers
    application.add_handler(CallbackQueryHandler(onboarding_start_callback, pattern=r"^ob_start$"))
    application.add_handler(CallbackQueryHandler(onboarding_skip_callback, pattern=r"^ob_skip$"))
    application.add_handler(CallbackQueryHandler(onboarding_claim_bonus_callback, pattern=r"^ob_claim_bonus$"))
    application.add_handler(CallbackQueryHandler(claim_gear_reward_callback, pattern=r"^claim_gear_reward$"))
    application.add_handler(CallbackQueryHandler(onboarding_claim_reward_callback, pattern=r"^ob_claim_reward$"))
    application.add_handler(CallbackQueryHandler(onboarding_continue_cast_callback, pattern=r"^ob_continue_cast$"))
    application.add_handler(CallbackQueryHandler(onboarding_send_cast_callback, pattern=r"^ob_send_cast$"))
    application.add_handler(CallbackQueryHandler(onboarding_send_hook_callback, pattern=r"^ob_send_hook$"))
    application.add_handler(CallbackQueryHandler(restart_onboarding_callback, pattern=r"^restart_onboarding$"))
