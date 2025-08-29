# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot for a virtual fishing game with ETH/USDT trading mechanics. The bot simulates fishing where catches translate to profit/loss based on real-time ETH prices with 2x leverage.

## Architecture

The bot uses:
- **python-telegram-bot** (v20.7) for async Telegram integration
- **SQLite** database for user and position tracking
- **PIL (Pillow)** for generating fish card images
- **CoinGecko API** for real-time ETH prices
- **OpenRouter API** for AI-powered fish image generation (optional)

### Project Structure:
```
src/
├── bot/                        # Telegram bot components
│   ├── telegram_bot.py         # Main bot module
│   ├── command_handlers.py     # Command handlers (/cast, /hook, etc.)
│   ├── animations.py           # Fishing animations and status updates
│   └── message_templates.py    # Message formatting and templates
├── database/
│   └── db_manager.py           # SQLite database operations
├── utils/
│   └── eth_price.py            # ETH price fetching and P&L calculations
└── generators/
    └── fish_card_generator.py  # Fish card image generation with AI
```

Key files:
- `main.py` - Entry point with bot initialization and conflict handling
- `src/bot/command_handlers.py` - All Telegram command implementations
- `src/database/db_manager.py` - Database operations for users and positions
- `src/utils/eth_price.py` - ETH price fetching and P&L calculations
- `src/generators/fish_card_generator.py` - Generates fish card images

## Development Commands

### Running the bot locally:
```bash
# Set token and run
export TELEGRAM_BOT_TOKEN="your_token_here"
python3 main.py

# Or use the provided script
./start_bot.sh
```

### Testing:
```bash
# Test files should be placed in tests/ directory
# Currently no test files are present in the project
```

### Dependencies:
```bash
pip install -r requirements.txt
```

## Deployment

The bot is deployed on Fly.io:
```bash
# Deploy to Fly.io
fly deploy

# Set the bot token secret
fly secrets set TELEGRAM_BOT_TOKEN="your_token_here"

# Optional: Set OpenRouter API key for AI image generation
fly secrets set OPENROUTER_API_KEY="your_openrouter_key_here"
```

## Database Schema

SQLite database (`fishing_bot.db`) is created automatically with:
- `users` table: user_id, username, first_interaction, bait_balance
- `positions` table: position tracking with entry/exit prices, P&L, fish caught

## Bot Commands

- `/cast` - Start fishing (costs 1 BAIT token)
- `/hook` - Catch fish and close position
- `/status` - Check active position
- `/help` - Show game rules

## Important Notes

- Bot token must be set via `TELEGRAM_BOT_TOKEN` environment variable
- OpenRouter API key (optional) via `OPENROUTER_API_KEY` for AI images
- Database file (`fishing_bot.db`) is created locally on first run
- Generated fish images are cached in `generated_fish_cache/`
- Uses async/await pattern throughout for Telegram bot handlers
- Falls back to placeholder images if OpenRouter API is unavailable