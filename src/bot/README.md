# Bot Structure

## 📁 Folder Organization

```
src/bot/
├── core/                      # System components
│   └── handlers_registry.py  # Centralized handler registration
│
├── utils/                     # Reusable utilities
│   ├── telegram_utils.py     # safe_reply, safe_send_message
│   └── validators.py         # BAIT checks, rate limits
│
├── ui/                        # UI components
│   ├── animations.py         # Cast/hook animations
│   ├── messages.py           # Message templates
│   └── formatters.py         # Data formatting
│
├── commands/                  # Bot commands
│   ├── cast.py               # /cast command
│   ├── hook.py               # /hook command
│   ├── status.py             # /status command
│   ├── start.py              # /start, /help, /pnl, /skip
│   ├── leaderboard.py        # /leaderboard
│   ├── payments.py           # /buy, /transactions
│   └── dev.py                # /test_card (development)
│
├── features/                  # Feature modules
│   ├── onboarding.py         # Onboarding system + callbacks
│   └── group_management.py   # Group pond management + gofishing
│
└── random_messages.py         # Random flavor text helpers
```

## 🎯 Design Principles

1. **Separation of Concerns**: Each module has one responsibility
2. **No Duplication**: Shared code in utils/ or features/
3. **Easy to Extend**: New command = new file
4. **Clear Dependencies**: commands → features → ui → utils
5. **Centralized Registration**: All handlers in core/handlers_registry.py

## 📝 Adding a New Command

1. Create file in `commands/your_command.py`
2. Import in `core/handlers_registry.py`
3. Add handler: `application.add_handler(CommandHandler("your_cmd", your_command))`

Done!

## 🗂️ Module Responsibilities

**core/** - System infrastructure
- Handler registration
- Application setup

**utils/** - Reusable helpers (no business logic)
- Telegram API wrappers
- Validation functions

**ui/** - Presentation layer
- Animations
- Message templates
- Data formatting

**commands/** - Business logic (one command per file)
- Command handlers
- User-facing functionality

**features/** - Complex feature modules
- Multi-step flows (onboarding)
- Domain logic (group management)
- Callback handlers related to features
