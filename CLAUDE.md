# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot for a virtual fishing game with cryptocurrency trading mechanics. The bot simulates fishing where catches translate to profit/loss based on real-time crypto prices. Features include flexible fish system with database-driven conditions, multi-currency support, different rods with varying leverage, user progression system, animated fishing sequences, **HTML formatting support**, and **Telegram Mini App interface**.

## 🎯 Key Features (Absurd Fish System)

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

### 📦 Refactoring Benefits

**Before:** Single `command_handlers.py` file with 1,298 lines
**After:** Modular structure with 6 focused files, each under 404 lines

- **🎯 Clear separation of concerns** - Each module has a specific responsibility
- **📖 Better readability** - Smaller files are easier to understand and navigate
- **🔧 Easier maintenance** - Changes are localized to relevant modules
- **🧪 Better testability** - Individual modules can be tested independently
- **👥 Parallel development** - Multiple developers can work on different command types simultaneously
- **📈 Backward compatibility** - All existing imports continue to work unchanged

## Development Commands

### Running the bot locally:
```bash
# Set token and run with async architecture
export TELEGRAM_BOT_TOKEN="your_token_here"
python3 main.py

# Or use the async script
./start_async_bot.sh
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

# Set Bunny CDN configuration for fast image delivery
fly secrets set BUNNYCDN_API_KEY="your_bunnycdn_api_key"
fly secrets set BUNNYCDN_STORAGE_ZONE="your_storage_zone"
fly secrets set BUNNYCDN_HOSTNAME="your_hostname"
fly secrets set BUNNYCDN_PUBLIC_URL="https://your-zone.b-cdn.net"
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

### Game Mechanics:
- **8 Trading Pairs**: ETH, BTC, SOL, ADA, MATIC, AVAX, LINK, DOT (all vs USDT)
- **Virtual Balance System**: $10,000 starting balance, $1,000 stake per cast
- **Rod System**: Long/Short trading rods with positive/negative leverage (2.0x to 6x range)
- **Active Rod Selection**: Players choose their preferred rod for all fishing operations
- **Character Visualization**: Active rod appears in player's hands on Mini App lobby screen
- **87 Fish Types**: Absurd fish with trash aesthetics, crypto memes, and unexpected personalities
- **Special Fish**: Crypto-themed fish like NFT-Обезьяна, Скам-Лягушка, Деген-Русалка
- **Level System**: Unlock new ponds as players progress
- **Leaderboard System**: Global, weekly, and daily rankings by virtual balance
- **Smart Matching**: Fish selection algorithm considers all conditions for realistic catches
- **Quick Fishing Prevention**: Anti-spam system prevents fishing in under 60 seconds with minimal P&L (<0.1%)

## Bot Commands

- `/start` - Welcome message with player stats and **🎮 Открыть игру** button for Mini App
- `/cast` - Start animated fishing sequence using player's active selected rod (costs 1 BAIT token)
- `/hook` - Catch fish using new database-driven system with personalized stories (includes anti-spam protection)
- `/status` - Check active position with multi-currency P&L updates
- `/pnl` - Show virtual balance, P&L statistics, and leaderboard position
- `/leaderboard` - Display top 10 players by virtual balance with trading stats
  - **In group chats**: Shows only trades from that specific group's pond (public data)
  - **In private chats**: Shows global leaderboard with personal user stats and ranking
- `/leaderboard week` - Weekly leaderboard rankings (group-specific in groups, global in private)
- `/help` - Show dynamic game rules generated from database (always up-to-date)
- `/buy` - **NEW**: Purchase BAIT tokens with Telegram Stars (shows interactive product selection)
- `/transactions` - **NEW**: View purchase history and transaction status
- `/test_card` - Generate test fish cards (development only)

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

### Technical Implementation

#### Database Schema
```sql
-- Users table includes inheritance tracking
ALTER TABLE users ADD COLUMN inheritance_claimed BOOLEAN DEFAULT FALSE;
```

#### Key Functions
- `claim_inheritance(user_id)` - Process inheritance claim (db_manager.py:1515)
- `check_inheritance_status(user_id)` - Check if claimed (db_manager.py:1544)
- `send_telegram_notification(user_id, message)` - Send success notification (animations.py:223)

#### API Endpoints
- `POST /api/user/{user_id}/claim-inheritance` - Claim inheritance
- `GET /api/user/{user_id}/inheritance-status` - Check status

#### Frontend Components
- **inheritance-screen**: Full inheritance UI (index.html:209-253)
- **Aged paper styling**: CSS with gradients, aged effects, wax seal (game.css:1985-2201)
- **JavaScript logic**: Auto-show for new users, claim processing (app.js:1177-1249)

### Virtual Balance Logic
The system uses existing balance calculation:
```sql
balance = 10000 + COALESCE(SUM(1000 * pnl_percent / 100), 0)
```

New users with no trading positions automatically get $10,000 base balance without needing artificial positions.

### Benefits
- **Educational**: Explains fishing = trading concept through story
- **Engaging**: Interactive narrative vs boring tutorial
- **Memorable**: Unique grandfather story creates emotional connection
- **Smooth**: Seamless integration with existing game systems
- **Clean**: No artificial database entries, uses existing balance formula

## Important Notes

### Environment Variables:
- `TELEGRAM_BOT_TOKEN` - Required bot token from @BotFather
- `DATABASE_URL` - PostgreSQL connection string (automatically set by Fly.io)
- `OPENROUTER_API_KEY` - Optional for AI-generated fish images
- `WEBAPP_URL` - URL for Mini App (e.g., https://your-app.fly.dev/webapp)
- `PORT` - Web server port (default: 8080, set automatically by Fly.io)

#### Bunny CDN Configuration (Optional but Recommended):
- `BUNNYCDN_API_KEY` - Bunny CDN API key for image uploads
- `BUNNYCDN_STORAGE_ZONE` - Storage zone name (e.g., "miniapps")
- `BUNNYCDN_HOSTNAME` - Upload hostname (e.g., "se.storage.bunnycdn.com")
- `BUNNYCDN_PUBLIC_URL` - Public CDN URL (e.g., "https://miniapps.b-cdn.net")

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
- **Payment System**: Secure Telegram Stars integration with transaction tracking

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

### Payment Flow
1. **Purchase Trigger**: User selects package via `/buy` command or WebApp
2. **Invoice Creation**: System generates Telegram invoice with secure payload
3. **Pre-Checkout Validation**: Bot validates order details and user status
4. **Payment Processing**: Telegram handles secure Stars payment
5. **Token Delivery**: BAIT tokens added immediately to user account
6. **Confirmation**: Success message with updated balance

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

### WebApp Integration
- **Clickable BAIT Balance**: Users can click their BAIT balance in lobby to open purchase modal
- **Interactive Purchase Modal**: Beautiful UI with product selection and pricing
- **Telegram WebApp Payment**: Seamless integration with Telegram's payment interface
- **Real-time Updates**: BAIT balance updates immediately after purchase

### Security Features
- **Payload Validation**: Unique transaction payloads prevent replay attacks
- **Amount Verification**: Pre-checkout validation ensures price integrity
- **User Authentication**: All purchases tied to authenticated Telegram users
- **Transaction Logging**: Comprehensive audit trail for all payment operations
- **Refund Support**: Built-in refund functionality for dispute resolution

### Commands & Usage
- `/buy` - Opens purchase interface with product selection
- `/transactions` - Shows purchase history and transaction status
- **No BAIT Scenario**: Automatic purchase offer when user tries to fish without BAIT
- **WebApp Purchase**: Click BAIT balance in Mini App for instant purchase modal

### Enhanced Fish System Features:
- **Massive Fish Variety**: 87 unique absurd fish across all PnL ranges
- **Weighted Rarity Selection**: trash (100%) → common (80%) → rare (40%) → epic (15%) → legendary (5%)
- **Multiple Fish per Range**: Each PnL range has multiple fish options with different personalities
- **Absurd Concepts**: Fish wearing costumes, having jobs, showing emotions, using craft store materials
- **Crypto Meme Fish**: Special crypto-themed fish reflecting DeFi culture (APY promises, rug pulls, FOMO)
- **Story Templates**: Personalized catch stories using database templates with variable substitution
- **Scalable Design**: Easy to add new fish via `absurd_fish_data.py` and sync script
- **AI Image Generation**: Crude MS Paint style prompts for intentionally low-quality absurd artwork
- **CDN Integration**: Automatic upload to Bunny CDN with global edge caching and optimization
- **Smart Fallback System**: On-demand CDN migration for existing images with database updates

### Social Features:
- Group chat friendly with visible casting announcements
- **Active Rod System**: Players select preferred rod for consistent trading strategy
- **Privacy-Aware Leaderboards**: Group-specific leaderboards in groups (public data only), global leaderboards with personal stats in private chats
- Dynamic fish card generation with database-driven stories
- Progressive difficulty through level-locked content
- **HTML Formatting**: Rich text with bold headers, colored indicators, and structured display

### Performance & Error Handling:
- **Parallel Image Generation**: Hook animation (12.5s) runs simultaneously with image generation (~12s) for 44% faster experience
- **CDN-Powered Loading**: Lightning-fast image delivery through global edge servers with automatic optimization
- **Progressive Enhancement**: Smart skeleton loaders with maintained aspect ratios during image loading
- **Lazy Loading**: Fish collection loads only when accessed, with skeleton states for better UX
- Graceful fallbacks for missing video files and database errors
- Retry logic for all Telegram API calls and external APIs
- Automatic starter equipment provisioning with migration support
- Robust async/await patterns with comprehensive error handling
- Backward compatibility for existing user data and positions
- **Timezone-safe time formatting**: Proper handling of both naive and aware datetimes

## 🎣 Rod Selection System

### Overview
The rod selection system allows players to choose between different trading rods with Long/Short positions. The active rod is visually represented on the character in the Mini App lobby and used automatically for all fishing operations.

### Rod Types
- **🚀 Long Rod**: Positive leverage (+2.0x) for bullish trades
- **🔻 Short Rod**: Negative leverage (-2.0x) for bearish trades
- Additional rods available with varying leverage (up to 6x)

### Database Schema
```sql
-- Enhanced rods table with trading types
ALTER TABLE rods ADD COLUMN rod_type VARCHAR(10);  -- 'long' or 'short'
ALTER TABLE rods ADD COLUMN visual_id VARCHAR(50); -- Asset identifier for visualization

-- User settings for active rod selection
CREATE TABLE user_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(telegram_id),
    active_rod_id INTEGER REFERENCES rods(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Key Functions
- `get_user_active_rod(user_id)` → Get user's currently selected rod
- `set_user_active_rod(user_id, rod_id)` → Set user's active rod preference
- `ensure_user_has_active_rod(user_id)` → Ensure user has an active rod (auto-assign if needed)

### Character Visualization
- Rod assets stored in `/webapp/static/images/`: `long-rod.svg`, `short-rod.svg`
- Character position: CSS positioned behind fisherman avatar with proper rotation
- Fallback system: Emoji display (🚀 for Long, 🔻 for Short) if SVG fails to load
- Parallel loading: Rod loads simultaneously with character to prevent visual delays

### API Endpoints
- `GET /api/user/{user_id}/active-rod` → Returns current active rod data
- `POST /api/user/{user_id}/active-rod` → Updates user's active rod selection
- `GET /api/products` → **NEW**: Returns available BAIT products for purchase
- `GET /api/user/{user_id}/transactions` → **NEW**: Returns user's transaction history
- `POST /api/user/{user_id}/purchase` → **NEW**: Creates purchase invoice for WebApp payment

### Frontend Implementation
```javascript
// Global state for active rod
let activeRod = null;

// Parallel loading for optimal performance
async function initializeApp() {
    await Promise.all([
        loadUserData(),
        loadActiveRod()  // Immediately updates character visual
    ]);
}

// Character visualization with fallbacks
function updateCharacterVisual() {
    const rodType = activeRod.rod_type === 'long' ? 'long' : 'short';
    // SVG loading with emoji fallback
    rodImg.src = `/static/images/${rodType}-rod.svg`;
    rodImg.onerror = () => showEmojiRod(rodType);
}
```

### Usage in Fishing Operations
The `/cast` command now uses the player's active rod instead of random selection, ensuring consistent trading strategy across all fishing sessions.

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
- `get_fishing_time_seconds(entry_time)` - Calculate fishing time in seconds for quick fishing detection
- `get_quick_fishing_message(fishing_time_seconds)` - Generate random funny anti-spam messages
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

### Privacy-Aware Leaderboard System
- **Context-Aware Behavior**: `/leaderboard` command now works differently in groups vs private chats
- **Group Chat Leaderboards**: Shows only trades from that specific group's pond (public data)
  - Displays pond name and group-specific rankings
  - Removes personal user stats to protect privacy
  - Helps text: "This leaderboard shows only trades made in this group"
- **Private Chat Leaderboards**: Maintains global leaderboard with full personal stats
  - Shows user's rank, balance, and percentile position
  - Includes personal P&L statistics and trading history
- **Time Period Support**: Both group and private leaderboards support weekly/daily/monthly filters

### Quick Fishing Prevention System
- **Anti-Spam Protection**: Prevents fishing completion in under 60 seconds with minimal P&L (<0.1%)
- **10 Funny Messages**: Randomized English messages encouraging patience (e.g., "Even Flash doesn't catch fish in 46 seconds!")
- **Real-Time Feedback**: Shows exact fishing time and remaining wait time for 1-minute minimum
- **Market Education**: Explains need to wait for crypto market movement to create meaningful P&L
- **Position Preservation**: Keeps fishing position active so players can try again after waiting

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

### Telegram Mini App Features
- **RPG-Style Lobby**: Player avatar with animated border and comprehensive stats display
- **Virtual Balance Display**: Real-time balance with profit/loss color indicators
- **Character Rod Visualization**: Active rod dynamically appears in player's hands on lobby screen
- **Rod Selection Interface**: Choose between Long/Short trading rods with visual indicators
- **Fish Collection**: Grid view of all caught fish with rarity badges and best P&L indicators
- **Detailed Fish History**: Modal with complete trading history for each fish type
- **Rod Collection**: Display of all owned fishing rods with leverage and rarity info
- **Responsive Design**: Works perfectly on all mobile devices with smooth animations
- **Telegram Integration**: Uses Telegram Web App SDK for seamless user experience
- **Real-time Data**: Live API integration with PostgreSQL database
- **Gaming Aesthetics**: Dark theme with gradient backgrounds and gaming-style UI elements

## 🚀 CDN System & Performance Optimization

### Bunny CDN Integration
The system uses Bunny CDN for global image delivery with the following features:

#### Image Upload & Optimization:
- **Automatic CDN Upload**: New fish images are automatically uploaded to CDN during generation
- **Smart Fallback**: Existing local images are migrated to CDN on first access
- **Size Optimization**: Multiple optimized versions (thumbnail 200px, medium 400px, full 800px)
- **Edge Caching**: Global distribution through Bunny's edge network

#### Migration Tools:
```bash
# Migrate all existing images to CDN
python3 migrate_images_to_cdn.py

# The script will:
# - Process images in batches (5 per batch)
# - Add 2-second delays between batches
# - Update database with CDN URLs
# - Provide detailed progress logging
```

#### API Endpoints:
- `/api/user/{user_id}/stats` → Complete user statistics with fish counts (caught/total format)
- `/api/user/{user_id}/fish` → Full fish collection with trading history
- `/api/user/{user_id}/rods` → User's rod collection
- `/api/user/{user_id}/active-rod` → Get/Set user's active rod selection (GET/POST)
- `/api/user/{user_id}/balance` → Virtual balance and P&L statistics
- `/api/leaderboard` → Flexible leaderboard with query parameters (type, pond_id, rod_id, user_id)
- `/api/fish/{fish_id}/image?size=thumbnail` → Optimized 200px image
- `/api/fish/{fish_id}/image?size=medium` → Optimized 400px image  
- `/api/fish/{fish_id}/image?size=full` → Optimized 800px image

### WebApp Performance Features

#### Skeleton Loading System:
- **Smart Placeholders**: Animated skeleton loaders maintain layout during loading
- **Aspect Ratio Preservation**: Square containers (1:1) for fish images
- **Selective Loading**: Only image skeletons, names show immediately
- **Smooth Transitions**: Fade-in animations when images load

#### Lazy Loading Strategy:
- **On-Demand Collection**: Fish data loads only when collection screen is accessed
- **Immediate Statistics**: Player stats (level, bait, fish count) load instantly on lobby
- **Progressive Enhancement**: Basic data loads first, images load with skeletons
- **Memory Optimization**: Reduces initial load time and memory usage
- **Bandwidth Efficiency**: CDN thumbnails for grid, full images for detail view

### Database Schema Updates:
- **fish_images.cdn_url**: Stores CDN URL for each fish image
- **Backward Compatibility**: Existing records work with null CDN URLs
- **Auto-Migration**: Database automatically adds CDN column if missing

### Example Script
See `example_prompt_management.py` for a comprehensive example of:
- Database initialization with AI prompt migration
- Viewing and updating AI prompts
- Testing image generation
- Best practices for prompt creation

## 🔄 Recent Refactoring (2024)

### Command Handlers Modularization
The bot's command handling system has been refactored from a single large file into smaller, focused modules:

#### ✅ **Completed Refactoring:**
- **Original**: `src/bot/command_handlers.py` (1,298 lines) - too large and difficult to maintain
- **Refactored**: Split into 6 focused modules with clear separation of concerns

#### 📁 **New Module Structure:**
1. **`fishing_commands.py`** (404 lines) - Core fishing functionality
   - `cast()` - Start fishing with pond selection
   - `hook()` - Complete fishing with parallel processing  
   - `status()` - Check current fishing position

2. **`user_commands.py`** (173 lines) - User-oriented commands
   - `start_command()` - Welcome and Mini App integration
   - `help_command()` - Alias to start command
   - `pnl()` - Personal P&L statistics

3. **`leaderboard_commands.py`** (163 lines) - Rankings and testing
   - `leaderboard()` - Group/global leaderboards with privacy awareness
   - `test_card()` - Development testing command

4. **`group_commands.py`** (280 lines) - Group functionality
   - `gofishing()` - Connect group pond to user account
   - `pond_selection_callback()` - Pond selection interface
   - `join_fishing_callback()` - Join fishing via inline buttons

5. **`private_fishing_helpers.py`** (318 lines) - Helper functions
   - `start_private_fishing_from_group()` - Private fishing initiation
   - `complete_private_hook_from_group()` - Private hook completion
   - `private_hook_animation()` - Simplified animation for private chat

6. **`command_handlers.py`** (17 lines) - Import aggregation
   - Imports all commands from specialized modules
   - Maintains backward compatibility
   - Single point for command registration

#### 🎯 **Benefits Achieved:**
- **Maintainability**: Each file has a single, clear responsibility
- **Readability**: All files are under 404 lines (target was 300 lines max)
- **Testability**: Modules can be tested independently
- **Development**: Multiple developers can work on different command types
- **Navigation**: Easier to find and modify specific functionality
- **Backwards Compatibility**: All existing imports continue to work

#### 📊 **File Size Comparison:**
```
BEFORE:  command_handlers.py     1,298 lines
AFTER:   fishing_commands.py       404 lines
         user_commands.py           173 lines  
         leaderboard_commands.py    163 lines
         group_commands.py          280 lines
         private_fishing_helpers.py 318 lines
         command_handlers.py         17 lines
         ─────────────────────────────────────
         TOTAL:                   1,355 lines
```

The slight increase in total lines (57 lines) comes from:
- Module docstrings and imports (necessary for proper separation)
- Better code organization and documentation
- Enhanced maintainability worth the minimal overhead

#### 🔧 **Implementation Notes:**
- All imports updated in dependent files (`main.py`)
- Command registration remains centralized in `main.py`
- No breaking changes to existing functionality
- Code compiles without syntax errors
- Modular imports allow for lazy loading if needed in the future

#### 🧑‍💻 **Working with Refactored Code:**
When modifying bot commands, work with the appropriate specialized module:
- **Fishing logic** → `src/bot/fishing_commands.py`
- **User features** → `src/bot/user_commands.py`
- **Rankings/stats** → `src/bot/leaderboard_commands.py`
- **Group features** → `src/bot/group_commands.py`
- **Helper functions** → `src/bot/private_fishing_helpers.py`
- **Registration only** → `src/bot/command_handlers.py`

All modules follow the same import patterns and maintain the existing code style and conventions.