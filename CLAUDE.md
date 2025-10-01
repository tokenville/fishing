# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot for a virtual fishing game with cryptocurrency trading mechanics. The bot simulates fishing where catches translate to profit/loss based on real-time crypto prices. Features include flexible fish system with database-driven conditions, multi-currency support, different rods with varying leverage, user progression system, animated fishing sequences, **HTML formatting support**, and **Telegram Mini App interface**.

## 🎯 Key Features

- **🎪 Absurd Fish Collection**: 87 unique fish with trash-style, absurd concepts and personalities
- **🐟 Dynamic Fish Variety**: Weighted rarity system with multiple fish per PnL range
- **💰 Multi-Currency Trading**: Support for 8 cryptocurrency pairs with automatic pond-based currency selection
- **🎣 Active Rod Selection**: Choose between Long/Short trading rods with visual character representation
- **🎨 Crude Art Style**: MS Paint-style intentionally low-quality fish images with absurd elements
- **📖 Personalized Stories**: Template-based fish catch stories stored in database
- **📊 Dynamic Help System**: Help content generated from database, always up-to-date
- **🎯 Special Fish**: Crypto-themed fish (NFT-Обезьяна, Скам-Лягушка, etc.) with meme culture references
- **⚡ Parallel Processing**: Image generation runs simultaneously with hook animation for instant results
- **🎨 HTML Formatting**: Rich text formatting with bold headers, colored P&L indicators, and structured messages
- **📱 Telegram Mini App**: RPG-style web interface for viewing fish collection, rods, and trading history
- **🚀 Bunny CDN Integration**: Global content delivery network for lightning-fast image loading with automatic optimization
- **💫 Smart Skeleton Loaders**: Animated loading placeholders that maintain layout and improve UX
- **⏰ Quick Fishing Prevention**: Anti-spam system with funny messages to encourage patience and market movement
- **🎁 Interactive Onboarding**: Story-driven inheritance system that teaches game mechanics through engaging narrative

## Architecture

The bot uses:
- **python-telegram-bot** (v20.7) for async Telegram integration with HTML parse mode
- **PostgreSQL** database for comprehensive game data (users, rods, ponds, positions)
- **asyncpg** for async PostgreSQL operations with connection pooling
- **aiohttp** for web server and API endpoints for Mini App
- **PIL (Pillow)** for generating fish card images
- **CoinGecko API** for real-time crypto prices across multiple pairs
- **OpenRouter API** for AI-powered fish image generation with database-stored prompts
- **Bunny CDN** for global image delivery with automatic optimization and edge caching
- **HTML formatting** for rich text display in all messages
- **Telegram Mini App** with responsive gaming UI and skeleton loading states

### Project Structure:
```
src/
├── bot/                          # Telegram bot components (refactored into smaller modules)
│   ├── telegram_bot.py           # Main bot module (13 lines)
│   ├── command_handlers.py       # Command handler imports and registration (17 lines)
│   ├── fishing_commands.py       # Core fishing commands: cast, hook, status (404 lines)
│   ├── user_commands.py          # User commands: start, help, pnl (173 lines)
│   ├── leaderboard_commands.py   # Leaderboard and test commands (163 lines)
│   ├── group_commands.py         # Group commands and callbacks (280 lines)
│   ├── private_fishing_helpers.py # Helper functions for private fishing (318 lines)
│   ├── payment_commands.py       # Telegram Stars payment handlers (320 lines)
│   ├── group_handlers.py         # Group management handlers (121 lines)
│   ├── animations.py             # Fishing animations and status updates (220 lines)
│   └── message_templates.py      # Dynamic message templates from database (440 lines)
├── database/
│   └── db_manager.py             # PostgreSQL database operations with fish system
├── utils/
│   ├── crypto_price.py           # Multi-currency price fetching and P&L calculations
│   └── bunny_cdn.py             # Bunny CDN integration for image delivery
├── generators/
│   └── fish_card_generator.py    # AI-powered fish card generation with CDN upload
└── webapp/                       # Telegram Mini App components
    └── web_server.py             # aiohttp web server with API endpoints and CDN fallback
webapp/
├── templates/
│   └── index.html                # Main Mini App interface
└── static/
    ├── css/
    │   ├── game.css             # Gaming-style CSS with RPG aesthetics
    │   └── skeleton.css         # Skeleton loading animations and states
    ├── js/app.js                # Mini App JavaScript with CDN integration and lazy loading
    └── images/
        ├── fisherman.svg        # Player avatar image
        ├── long-rod.svg         # Long trading rod asset
        └── short-rod.svg        # Short trading rod asset
```

### 🏗️ Bot Command Architecture (Refactored)

**Key files:**
- `main.py` - Entry point with bot initialization, conflict handling, HTML parse mode, and web server
- `src/bot/command_handlers.py` - **NEW**: Centralized imports and command registration (17 lines)
- `src/bot/fishing_commands.py` - **NEW**: Core fishing functionality (cast, hook, status) (404 lines)
- `src/bot/user_commands.py` - **NEW**: User-oriented commands (start, help, pnl) (173 lines)  
- `src/bot/leaderboard_commands.py` - **NEW**: Rankings and test commands (163 lines)
- `src/bot/group_commands.py` - **NEW**: Group commands and callbacks (gofishing, pond selection) (280 lines)
- `src/bot/private_fishing_helpers.py` - **NEW**: Helper functions for private fishing operations (318 lines)
- `src/bot/payment_commands.py` - **NEW**: Telegram Stars payment handlers (buy, transactions, invoice processing) (320 lines)
- `src/bot/group_handlers.py` - Group event handlers (bot addition, member changes) (121 lines)
- `src/bot/animations.py` - Fishing animations and status updates (220 lines)
- `src/bot/message_templates.py` - Dynamic message templates from database (440 lines)

**Other key files:**
- `src/database/db_manager.py` - Extended PostgreSQL database operations (users, positions, fish, AI prompts, CDN URLs)
- `src/webapp/web_server.py` - aiohttp server with REST API endpoints and smart CDN fallback system
- `src/utils/bunny_cdn.py` - Bunny CDN integration with image optimization and upload capabilities
- `webapp/templates/index.html` - Single-page Mini App with lobby, collection, and rods screens
- `webapp/static/js/app.js` - Mini App JavaScript with CDN integration, lazy loading, and skeleton states
- `webapp/static/css/game.css` - RPG-style CSS with gaming aesthetics and proper aspect ratios
- `webapp/static/css/skeleton.css` - Animated skeleton loaders with shimmer effects
- `migrate_images_to_cdn.py` - Background script for migrating existing images to CDN

## Development Commands

### Running the bot locally:
```bash
# Set token and run with async architecture
export TELEGRAM_BOT_TOKEN="your_token_here"
python3 main.py

# Or use the async script
./start_async_bot.sh
```

### Dependencies:
```bash
pip install -r requirements.txt
```

## Database Schema

PostgreSQL database is configured via `DATABASE_URL` environment variable with:

### Core Tables:
- **`users`** - Player profiles with level/experience system
  - `telegram_id`, `username`, `bait_tokens`, `level`, `experience`, `created_at`
- **`user_settings`** - Player preferences and active selections
  - `user_id`, `active_rod_id`, `created_at`, `updated_at`
- **`ponds`** - Available fishing locations with different trading pairs
  - `name`, `trading_pair`, `base_currency`, `quote_currency`, `required_level`, `is_active`
- **`rods`** - Fishing equipment with varying leverage and rarity
  - `name`, `leverage`, `price`, `rarity`, `is_starter`, `rod_type`, `visual_id`
- **`positions`** - Active/completed fishing sessions
  - `user_id`, `pond_id`, `rod_id`, `entry_price`, `exit_price`, `pnl_percent`, `fish_caught_id`
- **`user_rods`** - Player inventory (many-to-many user-rod relationship)

### New Fish System Tables:
- **`fish`** - Complete fish database with conditions, stories, and AI prompts
  - `name`, `emoji`, `description`, `min_pnl`, `max_pnl`, `min_user_level`, `required_ponds`, `required_rods`, `rarity`, `story_template`, `created_at`, `ai_prompt`
- **`fish_images`** - Image cache management
  - `fish_id`, `rarity`, `image_path`, `cache_key`, `created_at`


## 🎁 Interactive Onboarding System

### Overview
New users experience a story-driven onboarding through their grandfather's inheritance letter, explaining game mechanics via engaging narrative.

### Crypto Anarchist Grandfather Lore
**Backstory**: In 2009, the grandfather lost Bitcoin keys in a pond while fishing. Instead of finding them, he discovered that fishing teaches perfect trading psychology - patience, timing, and intuition. He built this game where fishing equals real crypto trades.

### Onboarding Flow
1. **First Mini App Launch**: New users see inheritance screen instead of lobby
2. **Letter Display**: Beautifully styled inheritance letter with aged paper, wax seal (₿), and grandfather's story
3. **Inheritance Items**:
   - 🎣 Grandfather's magical fishing rod
   - 💰 $10,000 starting capital
   - 🪱 10 BAIT tokens
4. **Accept Inheritance**: Single button interaction claims inheritance
5. **Automatic Benefits**: 
   - `inheritance_claimed = TRUE`
   - `bait_tokens += 10` (was 5, updated to 10 per UI)
   - Virtual balance = $10,000 (automatic via existing formula)
6. **Telegram Notification**: Success message sent to user's chat
7. **Transition**: Automatic redirect to normal lobby experience


### Virtual Balance Logic
The system uses existing balance calculation:
```sql
balance = 10000 + COALESCE(SUM(1000 * pnl_percent / 100), 0)
```

New users with no trading positions automatically get $10,000 base balance without needing artificial positions.

## 💰 Payment System (Telegram Stars)

### Overview
The bot now supports purchasing BAIT tokens using Telegram Stars, providing a secure, integrated payment solution directly within Telegram.

### Key Features
- **Secure Payments**: Uses Telegram's native Stars payment system for digital goods
- **Three Package Options**: 10, 50, or 100 BAIT tokens with competitive pricing
- **Dual Purchase Entry Points**: 
  1. When user runs out of BAIT (automatic offer with purchase buttons)
  2. WebApp interface (click on BAIT balance in lobby screen)
- **Complete Transaction Tracking**: All purchases recorded in database with status management
- **Automatic Token Delivery**: BAIT tokens added instantly upon successful payment
- **Purchase History**: `/transactions` command shows detailed purchase history

### Product Packages
```
🪱 BAIT Pack Small:  10 tokens for ⭐100 Stars
🪱 BAIT Pack Medium: 50 tokens for ⭐450 Stars (🔥 BEST VALUE)
🪱 BAIT Pack Large:  100 tokens for ⭐800 Stars (Save 20%)
```
### Database Schema (Payment Tables)
```sql
-- Products table for BAIT packages
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    bait_amount INTEGER NOT NULL,
    stars_price INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT true
);

-- Transactions table for payment tracking
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER DEFAULT 1,
    stars_amount INTEGER NOT NULL,
    bait_amount INTEGER NOT NULL,
    payment_charge_id TEXT UNIQUE,
    telegram_payment_charge_id TEXT,
    provider_payment_charge_id TEXT,
    status TEXT DEFAULT 'pending',
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Social Features:
- Group chat friendly with visible casting announcements
- **Active Rod System**: Players select preferred rod for consistent trading strategy
- **Privacy-Aware Leaderboards**: Group-specific leaderboards in groups (public data only), global leaderboards with personal stats in private chats
- Dynamic fish card generation with database-driven stories
- Progressive difficulty through level-locked content
- **HTML Formatting**: Rich text with bold headers, colored indicators, and structured display
