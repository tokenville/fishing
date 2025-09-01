# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot for a virtual fishing game with cryptocurrency trading mechanics. The bot simulates fishing where catches translate to profit/loss based on real-time crypto prices. Features include flexible fish system with database-driven conditions, multi-currency support, different rods with varying leverage, user progression system, animated fishing sequences, and **HTML formatting support**.

## 🎯 Key Features (Absurd Fish System)

- **🎪 Absurd Fish Collection**: 87 unique fish with trash-style, absurd concepts and personalities
- **🐟 Dynamic Fish Variety**: Weighted rarity system with multiple fish per PnL range
- **💰 Multi-Currency Trading**: Support for 8 cryptocurrency pairs with automatic pond-based currency selection
- **🎨 Crude Art Style**: MS Paint-style intentionally low-quality fish images with absurd elements
- **📖 Personalized Stories**: Template-based fish catch stories stored in database
- **📊 Dynamic Help System**: Help content generated from database, always up-to-date
- **🎯 Special Fish**: Crypto-themed fish (NFT-Обезьяна, Скам-Лягушка, etc.) with meme culture references
- **⚡ Parallel Processing**: Image generation runs simultaneously with hook animation for instant results
- **🎨 HTML Formatting**: Rich text formatting with bold headers, colored P&L indicators, and structured messages

## Architecture

The bot uses:
- **python-telegram-bot** (v20.7) for async Telegram integration with HTML parse mode
- **PostgreSQL** database for comprehensive game data (users, rods, ponds, positions)
- **asyncpg** for async PostgreSQL operations with connection pooling
- **PIL (Pillow)** for generating fish card images
- **CoinGecko API** for real-time crypto prices across multiple pairs
- **OpenRouter API** for AI-powered fish image generation with database-stored prompts
- **HTML formatting** for rich text display in all messages

### Project Structure:
```
src/
├── bot/                        # Telegram bot components
│   ├── telegram_bot.py         # Main bot module
│   ├── command_handlers.py     # Command handlers (/cast, /hook, etc.)
│   ├── animations.py           # Fishing animations and status updates
│   └── message_templates.py    # Dynamic message templates from database
├── database/
│   └── db_manager.py           # PostgreSQL database operations with fish system
├── utils/
│   └── crypto_price.py         # Multi-currency price fetching and P&L calculations
└── generators/
    └── fish_card_generator.py  # AI-powered fish card generation with database caching
```

Key files:
- `main.py` - Entry point with bot initialization, conflict handling, and HTML parse mode setup
- `src/bot/command_handlers.py` - All Telegram command implementations with new fish system
- `src/database/db_manager.py` - Extended PostgreSQL database operations (users, positions, fish, AI prompts, image caching)
- `src/utils/crypto_price.py` - Multi-currency price fetching and timezone-safe time formatting
- `src/generators/fish_card_generator.py` - AI-powered fish card generation with database-stored prompts
- `src/bot/message_templates.py` - HTML-formatted dynamic templates with database-driven help system

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

PostgreSQL database is configured via `DATABASE_URL` environment variable with:

### Core Tables:
- **`users`** - Player profiles with level/experience system
  - `telegram_id`, `username`, `bait_tokens`, `level`, `experience`, `created_at`
- **`ponds`** - Available fishing locations with different trading pairs
  - `name`, `trading_pair`, `base_currency`, `quote_currency`, `required_level`, `is_active`
- **`rods`** - Fishing equipment with varying leverage and rarity
  - `name`, `leverage`, `price`, `rarity`, `is_starter`
- **`positions`** - Active/completed fishing sessions
  - `user_id`, `pond_id`, `rod_id`, `entry_price`, `exit_price`, `pnl_percent`, `fish_caught_id`
- **`user_rods`** - Player inventory (many-to-many user-rod relationship)

### New Fish System Tables:
- **`fish`** - Complete fish database with conditions, stories, and AI prompts
  - `name`, `emoji`, `description`, `min_pnl`, `max_pnl`, `min_user_level`, `required_ponds`, `required_rods`, `rarity`, `story_template`, `created_at`, `ai_prompt`
- **`fish_images`** - Image cache management
  - `fish_id`, `rarity`, `image_path`, `cache_key`, `created_at`

### Game Mechanics:
- **8 Trading Pairs**: ETH, BTC, SOL, ADA, MATIC, AVAX, LINK, DOT (all vs USDT)
- **8 Rod Types**: 1.5x to 6x leverage, from starter to legendary rarity  
- **87 Fish Types**: Absurd fish with trash aesthetics, crypto memes, and unexpected personalities
- **Special Fish**: Crypto-themed fish like NFT-Обезьяна, Скам-Лягушка, Деген-Русалка
- **Level System**: Unlock new ponds as players progress
- **Smart Matching**: Fish selection algorithm considers all conditions for realistic catches

## Bot Commands

- `/cast` - Start animated fishing sequence with smart pond/rod selection (costs 1 BAIT token)
- `/hook` - Catch fish using new database-driven system with personalized stories
- `/status` - Check active position with multi-currency P&L updates
- `/help` - Show dynamic game rules generated from database (always up-to-date)
- `/test_card` - Generate test fish cards (development only)

## Important Notes

### Environment Variables:
- `TELEGRAM_BOT_TOKEN` - Required bot token from @BotFather
- `DATABASE_URL` - PostgreSQL connection string (automatically set by Fly.io)
- `OPENROUTER_API_KEY` - Optional for AI-generated fish images

### Animation System:
- `cast.mp4` - Video animation played during fishing cast sequence
- Casting animation has variable timing (2.5-3.0 seconds per frame) for readability
- Real-time P&L updates every 15 seconds during fishing
- Smart message editing (video captions vs text) with retry logic

### Database Features:
- **Auto-initialization**: Default ponds, rods, and fish with migration support
- **Flexible Fish System**: Easy to add new fish by inserting into database
- **Smart Image Caching**: Database-managed cache with automatic generation
- **Multi-Currency Support**: Automatic currency selection based on pond
- **Dynamic Content**: Help, stories, and fish selection all driven by database
- **Migration System**: Automatic schema updates for existing installations
- **AI Prompt Storage**: Database-stored AI prompts for each fish with management tools

### Enhanced Fish System Features:
- **Massive Fish Variety**: 87 unique absurd fish across all PnL ranges
- **Weighted Rarity Selection**: trash (100%) → common (80%) → rare (40%) → epic (15%) → legendary (5%)
- **Multiple Fish per Range**: Each PnL range has multiple fish options with different personalities
- **Absurd Concepts**: Fish wearing costumes, having jobs, showing emotions, using craft store materials
- **Crypto Meme Fish**: Special crypto-themed fish reflecting DeFi culture (APY promises, rug pulls, FOMO)
- **Story Templates**: Personalized catch stories using database templates with variable substitution
- **Scalable Design**: Easy to add new fish via `absurd_fish_data.py` and sync script
- **AI Image Generation**: Crude MS Paint style prompts for intentionally low-quality absurd artwork

### Social Features:
- Group chat friendly with visible casting announcements
- Smart rod/pond selection based on user level and inventory
- Dynamic fish card generation with database-driven stories
- Progressive difficulty through level-locked content
- **HTML Formatting**: Rich text with bold headers, colored indicators, and structured display

### Performance & Error Handling:
- **Parallel Image Generation**: Hook animation (12.5s) runs simultaneously with image generation (~12s) for 44% faster experience
- Graceful fallbacks for missing video files and database errors
- Retry logic for all Telegram API calls and external APIs
- Automatic starter equipment provisioning with migration support
- Robust async/await patterns with comprehensive error handling
- Backward compatibility for existing user data and positions
- **Timezone-safe time formatting**: Proper handling of both naive and aware datetimes

## 🐟 Working with the Fish System

### Managing Fish Database
Use the unified sync script to manage all fish:
```bash
# Sync database with absurd_fish_data.py
python3 sync_fish_database.py

# This script will:
# - Create automatic backup
# - Add new fish from data file
# - Update existing fish
# - Optionally remove orphaned fish
# - Clear image cache if needed
```

### Adding New Fish
Add fish to `absurd_fish_data.py`:
```python
{
    "name": "Вейп-Медуза",
    "emoji": "💨",
    "description": "Выдыхала облака и говорила что это органика",
    "min_pnl": -0.4,
    "max_pnl": 0.4,
    "rarity": "common",
    "ai_prompt": "Jellyfish with vape pen tentacles blowing huge clouds, smug expression"
}
```

Then run: `python3 sync_fish_database.py`

### Restoring from Backup
```bash
# View and restore from backups
python3 restore_fish_backup.py
```

### Key Functions for Enhanced Fish System
- `get_suitable_fish(pnl_percent, user_level, pond_id, rod_id)` - **Enhanced**: Weighted rarity selection from multiple suitable fish
- `get_suitable_fish_old(pnl_percent, user_level, pond_id, rod_id)` - Legacy single-fish selection (kept for compatibility)
- `get_catch_story_from_db(fish_data, pnl, time_fishing)` - Generate personalized story
- `get_help_text()` - Dynamic help generation from database
- `get_crypto_price(base_currency)` - Multi-currency price fetching
- **AI Prompt Management Functions**:
  - `get_fish_ai_prompt(fish_id)` - Get AI prompt for specific fish
  - `update_fish_ai_prompt(fish_id, ai_prompt)` - Update AI prompt for fish
  - `get_all_fish_prompts()` - Get all fish with their AI prompts
  - `update_fish_prompts_bulk(prompts_data)` - Update multiple prompts at once

### Multi-Currency Trading Pairs
The system automatically selects the correct cryptocurrency based on the pond:
- 🌊 Криптовые Воды → ETH/USDT
- 💰 Озеро Профита → BTC/USDT  
- ⚡ Море Волатильности → SOL/USDT
- 🌙 Лунные Пруды → ADA/USDT
- 🔥 Вулканические Источники → MATIC/USDT
- ❄️ Ледяные Глубины → AVAX/USDT
- 🌈 Радужные Заводи → LINK/USDT
- 🏔️ Горные Озёра → DOT/USDT

### Story Template Variables
Available variables in `story_template`:
- `{emoji}` - Fish emoji
- `{name}` - Fish name  
- `{pnl}` - P&L percentage
- `{time_fishing}` - Time spent fishing

Example: `"🌊 Water EXPLODES as you pull up... {emoji} {name}! Amazing catch worth {pnl:+.1f}% after {time_fishing}!"`

## 🎨 AI Prompt Management System

### Absurd Image Generation Style
The AI image generation system uses intentionally crude, MS Paint-style aesthetics:

**Style Context Applied to All Fish Images:**
- Absurd and unexpected artwork, intentionally crude digital drawing
- MS Paint style with flat colors and rough outlines
- Naive composition with awkward proportions
- Exaggerated features, funny and playful
- Intentionally low-quality appearance
- No captions or framing, square format (1:1 aspect ratio)

**AI Prompt Structure:**
Each generated image uses: `{absurd_fish_description} + {crude_style_context}`

Example: `"A fish spray-painted gold wearing plastic dragon wings from a toy store, breathing fire from a novelty lighter, looking extremely pleased with its discount costume store transformation. Absurd and unexpected artwork, intentionally crude digital drawing, MS Paint style, flat colors, rough outlines, naive composition, awkward proportions, exaggerated features, funny and playful, intentionally low-quality, no captions, no framing, square format (1:1 aspect ratio), centered subject."`

### FishPromptManager Class
Convenient class for managing AI prompts with the following methods:

```python
from src.generators.fish_card_generator import prompt_manager

# List all fish with their current AI prompts
prompts = prompt_manager.list_all_prompts()

# Get AI prompt for specific fish by name
prompt = prompt_manager.get_prompt("Золотой Дракон")

# Update AI prompt for fish by name (style context is added automatically)
success = prompt_manager.update_prompt("Золотой Дракон", "new_ai_prompt_here")

# Bulk update multiple prompts at once
updated_count = prompt_manager.bulk_update_prompts({
    "Fish1": "prompt1",
    "Fish2": "prompt2"
})

# Generate default prompt for a fish
default_prompt = prompt_manager.generate_default_prompt("Fish Name")

# Clear image cache to force regeneration with new prompts
prompt_manager.clear_image_cache()  # Clear all
prompt_manager.clear_image_cache("Fish Name")  # Clear specific fish
```

**Important:** When updating AI prompts in the database, only include the fish-specific description. The static style context is automatically appended during image generation.

## 🚀 Recent Enhancements (Absurd Fish Update)

### Absurd Fish Database
- **Expanded to 87 Fish**: Complete redesign with absurd, trash-style concepts
- **Crypto Meme Fish**: Added 40+ new crypto-themed fish (NFT-Обезьяна, Скам-Лягушка, Деген-Русалка)
- **Unified Sync Script**: `sync_fish_database.py` manages all fish operations with automatic backups
- **Weighted Rarity System**: 
  - trash: 100% probability (most common)
  - common: 80% probability  
  - rare: 40% probability
  - epic: 15% probability
  - legendary: 5% probability (rarest)

### Absurd Design Philosophy
- **Unexpected Personalities**: Fish wearing costumes, having jobs, showing emotions
- **Craft Store Aesthetics**: Using glitter, cardboard, paper plates for "magic" effects
- **Self-Aware Humor**: Fish knowing they look ridiculous but playing along
- **Crypto Culture**: Reflecting DeFi memes, rug pulls, APY promises, FOMO

### Fish Distribution (87 total):
- **Trash tier** (losses): 11 fish - Старый Сапог, Ржавый Якорь, Пластиковая Бутылка
- **Common tier** (small range): 30 fish - Including new Кибер-Карась, Гопник Сомик, ТикТок-Карась
- **Rare tier** (medium gains): 30 fish - Including NFT-Обезьяна, Скам-Лягушка, Понзи-Краб
- **Epic tier** (great gains): 7 fish - Акула Профита, Драконья Рыба, Титановая Акула
- **Legendary tier** (huge gains): 9 fish - Золотой Дракон, Космический Кит, Феникс-Рыба

### HTML Formatting Support
The bot now uses HTML parse mode by default for rich text formatting:
- **Bold text**: `<b>text</b>`
- **Italic text**: `<i>text</i>`
- **Username display**: Shows correctly without escaping (e.g., `Ivan_Soko1ov`)
- **Colored P&L indicators**: 🟢 for positive, 🔴 for negative
- **Structured messages**: Headers, status info, and commands properly formatted

### Example Script
See `example_prompt_management.py` for a comprehensive example of:
- Database initialization with AI prompt migration
- Viewing and updating AI prompts
- Testing image generation
- Best practices for prompt creation