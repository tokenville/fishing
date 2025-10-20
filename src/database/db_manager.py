import asyncpg
import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
import json
from datetime import datetime
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

# Database connection settings
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/fishing_bot')

# Connection pool
_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()

# Rate limiting
_user_rate_limits: Dict[int, float] = defaultdict(float)
_rate_limit_lock = asyncio.Lock()
RATE_LIMIT_COMMANDS = 10  # Max commands per minute
RATE_LIMIT_WINDOW = 60  # Window in seconds

# Hook-specific rate limiting (more restrictive)
HOOK_RATE_LIMIT_COMMANDS = 3  # Max 3 hook attempts per minute  
HOOK_RATE_LIMIT_WINDOW = 60  # Window in seconds
_hook_rate_limits = {}  # user_id -> list of timestamps
_hook_rate_limit_lock = asyncio.Lock()

async def get_pool() -> asyncpg.Pool:
    """Get or create connection pool optimized for high load with thread safety"""
    global _pool
    if _pool is None:
        async with _pool_lock:
            # Double-check pattern for thread safety
            if _pool is None:
                _pool = await asyncpg.create_pool(
                    DATABASE_URL,
                    min_size=10,  # Higher minimum for always-ready connections
                    max_size=50,  # Higher maximum for hundreds of concurrent users
                    max_queries=50000,  # High query limit per connection
                    max_inactive_connection_lifetime=300.0,  # 5 minutes
                    command_timeout=30,  # Reduced timeout for faster failure detection
                    server_settings={
                        'jit': 'off',  # Disable JIT for consistent performance
                        'application_name': 'fishing_bot'
                    }
                )
    return _pool

async def close_pool():
    """Close connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def retry_db_operation(operation, max_retries=3, delay=0.1):
    """Retry database operations with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await operation()
        except (asyncpg.ConnectionError, asyncpg.InterfaceError, asyncio.TimeoutError) as e:
            if attempt == max_retries - 1:
                logger.error(f"Database operation failed after {max_retries} attempts: {e}")
                raise
            wait_time = delay * (2 ** attempt)
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)

async def check_rate_limit(user_id: int) -> bool:
    """Check if user has exceeded rate limit
    
    Returns:
        True if user can proceed, False if rate limited
    """
    async with _rate_limit_lock:
        now = time.time()
        user_history = _user_rate_limits.get(user_id, [])
        
        # Clean old entries outside the window
        if isinstance(user_history, list):
            user_history = [t for t in user_history if now - t < RATE_LIMIT_WINDOW]
        else:
            # Handle legacy format
            user_history = []
        
        # Check if exceeds limit
        if len(user_history) >= RATE_LIMIT_COMMANDS:
            return False
        
        # Add current request
        user_history.append(now)
        _user_rate_limits[user_id] = user_history
        
        return True

async def check_hook_rate_limit(user_id: int) -> bool:
    """Check if user has exceeded hook-specific rate limit
    
    Hook commands are more resource-intensive (animation + API calls)
    so they have stricter limits than regular commands.
    
    Returns:
        True if user can proceed, False if rate limited
    """
    async with _hook_rate_limit_lock:
        now = time.time()
        user_history = _hook_rate_limits.get(user_id, [])
        
        # Clean old entries outside the window
        user_history = [t for t in user_history if now - t < HOOK_RATE_LIMIT_WINDOW]
        
        # Check if exceeds hook-specific limit (more restrictive)
        if len(user_history) >= HOOK_RATE_LIMIT_COMMANDS:
            return False
        
        # Add current request
        user_history.append(now)
        _hook_rate_limits[user_id] = user_history
        
        return True

async def cleanup_hook_rate_limits():
    """Cleanup old hook rate limit entries (run periodically)"""
    async with _hook_rate_limit_lock:
        now = time.time()
        for user_id in list(_hook_rate_limits.keys()):
            history = _hook_rate_limits[user_id]
            cleaned = [t for t in history if now - t < HOOK_RATE_LIMIT_WINDOW]
            if cleaned:
                _hook_rate_limits[user_id] = cleaned
            else:
                del _hook_rate_limits[user_id]

async def cleanup_rate_limits():
    """Cleanup old rate limit entries (run periodically)"""
    async with _rate_limit_lock:
        now = time.time()
        to_remove = []
        
        for user_id, history in _user_rate_limits.items():
            if isinstance(history, list):
                cleaned = [t for t in history if now - t < RATE_LIMIT_WINDOW]
                if not cleaned:
                    to_remove.append(user_id)
                else:
                    _user_rate_limits[user_id] = cleaned
        
        for user_id in to_remove:
            del _user_rate_limits[user_id]

async def reset_database():
    """Drop all tables and recreate them - USE WITH CAUTION"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Drop all tables in correct order (reverse dependency)
        tables_to_drop = [
            'group_memberships',
            'fish_images', 
            'user_rods', 
            'positions', 
            'user_settings',
            'fish', 
            'rods', 
            'ponds', 
            'users'
        ]
        
        for table in tables_to_drop:
            await conn.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
            logger.info(f"Dropped table: {table}")
        
        logger.info("Database reset completed - all tables dropped")

async def init_database():
    """Initialize the database with required tables"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Create users table with level system
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                bait_tokens INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create ponds table (enhanced for group support)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS ponds (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                trading_pair TEXT NOT NULL,
                base_currency TEXT NOT NULL,
                quote_currency TEXT NOT NULL,
                image_url TEXT,
                required_level INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT true,
                chat_id BIGINT, 
                chat_type TEXT,
                member_count INTEGER DEFAULT 0,
                pond_type TEXT DEFAULT 'static',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add new columns for group support if they don't exist (migration)
        await conn.execute('''
            ALTER TABLE ponds 
            ADD COLUMN IF NOT EXISTS chat_id BIGINT,
            ADD COLUMN IF NOT EXISTS chat_type TEXT,
            ADD COLUMN IF NOT EXISTS member_count INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS pond_type TEXT DEFAULT 'static'
        ''')
        
        # Create rods table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rods (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                leverage REAL NOT NULL,
                price INTEGER DEFAULT 0,
                image_url TEXT,
                rarity TEXT DEFAULT 'common',
                is_starter BOOLEAN DEFAULT false,
                rod_type TEXT DEFAULT 'neutral',
                visual_id TEXT DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add new columns if they don't exist (migration)
        await conn.execute('''
            ALTER TABLE rods 
            ADD COLUMN IF NOT EXISTS rod_type TEXT DEFAULT 'neutral',
            ADD COLUMN IF NOT EXISTS visual_id TEXT DEFAULT 'default'
        ''')
        
        # Create user_rods table (many-to-many relationship)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_rods (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                rod_id INTEGER,
                acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (rod_id) REFERENCES rods (id),
                UNIQUE(user_id, rod_id)
            )
        ''')
        
        # Create user_settings table for active rod selection
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE,
                active_rod_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (active_rod_id) REFERENCES rods (id)
            )
        ''')

        # Create user_balances table for static balance storage
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_balances (
                user_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
                balance NUMERIC(18, 2) DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create fish table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS fish (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                emoji TEXT,
                description TEXT,
                min_pnl REAL,
                max_pnl REAL,
                min_user_level INTEGER DEFAULT 1,
                required_ponds TEXT,
                required_rods TEXT,
                rarity TEXT DEFAULT 'common',
                story_template TEXT,
                ai_prompt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create positions table (matching SQLite schema)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                pond_id INTEGER,
                rod_id INTEGER,
                entry_price REAL,
                entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                exit_price REAL,
                exit_time TIMESTAMP,
                pnl_percent REAL,
                fish_caught_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (pond_id) REFERENCES ponds (id),
                FOREIGN KEY (rod_id) REFERENCES rods (id),
                FOREIGN KEY (fish_caught_id) REFERENCES fish (id)
            )
        ''')
        
        # Create fish_images table for caching generated images
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS fish_images (
                id SERIAL PRIMARY KEY,
                fish_id INTEGER NOT NULL,
                rarity TEXT NOT NULL,
                image_path TEXT NOT NULL,
                cache_key TEXT NOT NULL UNIQUE,
                cdn_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fish_id) REFERENCES fish (id)
            )
        ''')
        
        # Add cdn_url column if it doesn't exist (migration)
        await conn.execute('''
            ALTER TABLE fish_images 
            ADD COLUMN IF NOT EXISTS cdn_url TEXT
        ''')
        
        # Create group_memberships table for tracking user access to group ponds
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS group_memberships (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                chat_id BIGINT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                UNIQUE(user_id, chat_id)
            )
        ''')
        
        # Create products table for BAIT packages
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                bait_amount INTEGER NOT NULL,
                stars_price INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create transactions table for payment tracking
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                stars_amount INTEGER NOT NULL,
                bait_amount INTEGER NOT NULL,
                payment_charge_id TEXT UNIQUE,
                telegram_payment_charge_id TEXT,
                provider_payment_charge_id TEXT,
                status TEXT DEFAULT 'pending',
                payload TEXT,
                invoice_payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products (id)
            );

            CREATE TABLE IF NOT EXISTS onboarding_progress (
                user_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
                current_step VARCHAR(50) DEFAULT 'welcome',
                completed BOOLEAN DEFAULT FALSE,
                first_cast_used BOOLEAN DEFAULT FALSE,
                first_hook_used BOOLEAN DEFAULT FALSE,
                group_bonus_claimed BOOLEAN DEFAULT FALSE,
                first_cast_reward_claimed BOOLEAN DEFAULT FALSE,
                first_catch_reward_claimed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Backfill new onboarding flags for existing installations
        try:
            await conn.execute(
                "ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS group_bonus_claimed BOOLEAN DEFAULT FALSE"
            )
        except Exception:
            pass

        try:
            await conn.execute(
                "ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS first_catch_reward_claimed BOOLEAN DEFAULT FALSE"
            )
        except Exception:
            pass

        try:
            await conn.execute(
                "ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS first_cast_reward_claimed BOOLEAN DEFAULT FALSE"
            )
        except Exception:
            pass

        # Insert default data
        # Note: Ponds are now created dynamically when bot is added to groups
        await _insert_default_rods(conn)
        await _insert_default_fish(conn)
        await _insert_default_products(conn)

    print("Database initialized successfully!")

async def get_user(telegram_id: int) -> Optional[asyncpg.Record]:
    """Get user by telegram_id"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            'SELECT * FROM users WHERE telegram_id = $1', 
            telegram_id
        )

async def create_user(telegram_id: int, username: str):
    """Create new user with 0 BAIT tokens, 0 balance, and 1 Long starter rod"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Create user with 0 BAIT
        await conn.execute('''
            INSERT INTO users (telegram_id, username, bait_tokens, level, experience)
            VALUES ($1, $2, 0, 1, 0)
            ON CONFLICT (telegram_id) DO NOTHING
        ''', telegram_id, username)

        # Create balance entry with starting $0
        await conn.execute('''
            INSERT INTO user_balances (user_id, balance)
            VALUES ($1, 0)
            ON CONFLICT (user_id) DO NOTHING
        ''', telegram_id)

    # Give only 1 Long starter rod (Short rod will be given on first cast)
    await give_single_starter_rod(telegram_id, rod_type='long')
    print(f"Created user: {username} ({telegram_id}) with $0 balance, 0 BAIT, 1 Long rod")

async def get_active_position(telegram_id: int) -> Optional[asyncpg.Record]:
    """Get user's active fishing position"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT * FROM positions 
            WHERE user_id = $1 AND status = 'active'
            ORDER BY entry_time DESC LIMIT 1
        ''', telegram_id)

async def create_position(telegram_id: int, entry_price: float):
    """Create new fishing position"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO positions (user_id, entry_price, entry_time)
            VALUES ($1, $2, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
        ''', telegram_id, entry_price)
    print(f"Created position for user {telegram_id} at price {entry_price}")

async def close_position(position_id: int, exit_price: float, pnl_percent: float, fish_caught_id: int):
    """Close fishing position and record results"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE positions
            SET status = 'closed', exit_price = $1, exit_time = CURRENT_TIMESTAMP AT TIME ZONE 'UTC',
                pnl_percent = $2, fish_caught_id = $3
            WHERE id = $4
        ''', exit_price, pnl_percent, fish_caught_id, position_id)

async def use_bait(telegram_id: int) -> bool:
    """Use 1 BAIT token for fishing"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute('''
            UPDATE users
            SET bait_tokens = bait_tokens - 1
            WHERE telegram_id = $1 AND bait_tokens > 0
        ''', telegram_id)
        return result.split()[-1] != '0'

async def add_bait_tokens(telegram_id: int, amount: int) -> bool:
    """Add BAIT tokens to user's balance"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute('''
            UPDATE users
            SET bait_tokens = bait_tokens + $1
            WHERE telegram_id = $2
        ''', amount, telegram_id)
        return result.split()[-1] != '0'

async def get_user_balance(user_id: int) -> float:
    """Get user's current balance from user_balances table"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            'SELECT balance FROM user_balances WHERE user_id = $1',
            user_id
        )
        return float(result) if result else 0.0

async def update_user_balance_after_hook(user_id: int, pnl_percent: float) -> None:
    """Update user balance after hook based on P&L
    Each position uses $1000 stake
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Calculate balance change: $1000 stake * pnl_percent / 100
        delta = 1000 * pnl_percent / 100

        await conn.execute('''
            UPDATE user_balances
            SET balance = balance + $1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $2
        ''', delta, user_id)

        logger.info(f"Updated balance for user {user_id}: delta={delta:.2f}, pnl={pnl_percent:.2f}%")

async def add_balance_bonus(user_id: int, amount: float) -> None:
    """Add bonus to user balance (e.g., first catch reward)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE user_balances
            SET balance = balance + $1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $2
        ''', amount, user_id)

        logger.info(f"Added balance bonus for user {user_id}: +${amount}")

# Note: Static ponds removed - all ponds are now created dynamically when bot is added to groups

async def _insert_default_rods(conn: asyncpg.Connection):
    """Insert default rods if they don't exist"""
    count = await conn.fetchval('SELECT COUNT(*) FROM rods')
    if count == 0:
        rods_data = [
            # Long/Short стартовые удочки для трейдинга
            ('🚀 Long удочка', 2.0, 0, None, 'common', True, 'long', 'long'),
            ('🔻 Short удочка', -2.0, 0, None, 'common', True, 'short', 'short'),
            # Дополнительные удочки для разнообразия
            ('🌊 Морская удочка', 2.5, 100, None, 'rare', False, 'long', 'long'),
            ('⚡ Электрическая удочка', -2.5, 100, None, 'rare', False, 'short', 'short'),
            ('💎 Алмазная удочка', 3.0, 500, None, 'epic', False, 'long', 'long'),
            ('🌙 Лунная удочка', -3.0, 500, None, 'epic', False, 'short', 'short'),
            ('☀️ Солнечная удочка', 4.0, 2000, None, 'legendary', False, 'long', 'long'),
            ('🎯 Мастерская удочка', -4.0, 2000, None, 'legendary', False, 'short', 'short')
        ]
        
        await conn.executemany('''
            INSERT INTO rods (name, leverage, price, image_url, rarity, is_starter, rod_type, visual_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''', rods_data)

async def _insert_default_fish(conn: asyncpg.Connection):
    """Insert default fish if they don't exist"""
    count = await conn.fetchval('SELECT COUNT(*) FROM fish')
    if count == 0:
        # Import from existing absurd_fish_data.py
        try:
            from absurd_fish_data import ABSURD_FISH_DATA
            fish_data = []
            for fish in ABSURD_FISH_DATA:
                fish_data.append((
                    fish['name'],
                    fish['emoji'],
                    fish['description'],
                    fish['min_pnl'],
                    fish['max_pnl'],
                    fish.get('min_user_level', 1),
                    fish.get('required_ponds', ''),
                    fish.get('required_rods', ''),
                    fish['rarity'],
                    fish.get('story_template', ''),
                    fish.get('ai_prompt', '')
                ))
            
            await conn.executemany('''
                INSERT INTO fish (name, emoji, description, min_pnl, max_pnl, min_user_level, 
                                required_ponds, required_rods, rarity, story_template, ai_prompt)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ''', fish_data)
            print(f"Inserted {len(fish_data)} fish from absurd_fish_data.py")
        except ImportError:
            # Fallback to basic fish if absurd_fish_data.py not available
            fish_data = [
                ('Старый Сапог', '🦐', 'Мусор со дна водоема', -100, -20, 1, '', '', 'trash', 
                 'Вы чувствуете груз разочарования... {emoji} {name}... серьезно?', ''),
                ('Счастливая Плотва', '🐟', 'Маленькая, но приносящая удачу', 0, 10, 1, '', '', 'common',
                 'Маленький, но счастливый улов появляется! {emoji} {name}!', ''),
            ]
            await conn.executemany('''
                INSERT INTO fish (name, emoji, description, min_pnl, max_pnl, min_user_level, 
                                required_ponds, required_rods, rarity, story_template, ai_prompt)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ''', fish_data)

async def _insert_default_products(conn: asyncpg.Connection):
    """Insert default BAIT products if they don't exist"""
    count = await conn.fetchval('SELECT COUNT(*) FROM products')
    if count == 0:
        products_data = [
            ('BAIT Pack Small', '10 BAIT tokens for fishing', 10, 100, True),
            ('BAIT Pack Medium', '50 BAIT tokens for fishing', 50, 450, True),
            ('BAIT Pack Large', '100 BAIT tokens for fishing', 100, 800, True)
        ]
        
        await conn.executemany('''
            INSERT INTO products (name, description, bait_amount, stars_price, is_active)
            VALUES ($1, $2, $3, $4, $5)
        ''', products_data)

async def get_available_ponds(user_id: int) -> List[asyncpg.Record]:
    """Get ponds available for user (group ponds only)

    Note: This function now returns only group ponds that the user has access to.
    Static ponds have been removed from the system.
    """
    return await get_user_group_ponds(user_id)

async def get_user_rods(telegram_id: int) -> List[asyncpg.Record]:
    """Get all rods owned by user"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch('''
            SELECT r.* FROM rods r
            JOIN user_rods ur ON r.id = ur.rod_id
            WHERE ur.user_id = $1
            ORDER BY r.leverage
        ''', telegram_id)

async def give_single_starter_rod(telegram_id: int, rod_type: str = 'long', conn: Optional[asyncpg.Connection] = None):
    """Give a single starter rod (Long or Short) to user"""

    async def _assign(connection: asyncpg.Connection):
        # Get the specific starter rod
        starter_rod = await connection.fetchrow(
            'SELECT id FROM rods WHERE is_starter = true AND rod_type = $1 LIMIT 1',
            rod_type
        )

        if not starter_rod:
            logger.warning(f"No starter rod found for type {rod_type}")
            return

        # Check if user already has this rod
        has_rod = await connection.fetchval(
            'SELECT 1 FROM user_rods WHERE user_id = $1 AND rod_id = $2',
            telegram_id,
            starter_rod['id']
        )

        if has_rod:
            logger.info(f"User {telegram_id} already has {rod_type} rod")
            return

        # Give the rod
        await connection.execute(
            '''
            INSERT INTO user_rods (user_id, rod_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id, rod_id) DO NOTHING
            ''',
            telegram_id,
            starter_rod['id'],
        )

        # Set as active rod if user has no active rod
        has_active = await connection.fetchval(
            'SELECT 1 FROM user_settings WHERE user_id = $1',
            telegram_id
        )

        if not has_active:
            await connection.execute(
                '''
                INSERT INTO user_settings (user_id, active_rod_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET active_rod_id = EXCLUDED.active_rod_id
                ''',
                telegram_id,
                starter_rod['id'],
            )

        logger.info(f"Gave {rod_type} starter rod to user {telegram_id}")

    if conn is not None:
        await _assign(conn)
        return

    pool = await get_pool()
    async with pool.acquire() as pooled_conn:
        await _assign(pooled_conn)

async def give_starter_rod(telegram_id: int, conn: Optional[asyncpg.Connection] = None):
    """Give both starter rods (Long & Short) to user if they don't have any."""

    async def _assign(connection: asyncpg.Connection):
        has_rods = await connection.fetchval(
            'SELECT COUNT(*) FROM user_rods WHERE user_id = $1',
            telegram_id,
        )

        if has_rods:
            return

        starter_rods = await connection.fetch(
            'SELECT id FROM rods WHERE is_starter = true ORDER BY rod_type'
        )

        for starter_rod in starter_rods:
            await connection.execute(
                '''
                INSERT INTO user_rods (user_id, rod_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id, rod_id) DO NOTHING
                ''',
                telegram_id,
                starter_rod['id'],
            )

        if starter_rods:
            print(f"Gave {len(starter_rods)} starter rods to user {telegram_id}")

        long_rod = await connection.fetchrow(
            "SELECT id FROM rods WHERE is_starter = true AND rod_type = 'long' LIMIT 1"
        )
        if long_rod:
            await connection.execute(
                '''
                INSERT INTO user_settings (user_id, active_rod_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET active_rod_id = EXCLUDED.active_rod_id
                ''',
                telegram_id,
                long_rod['id'],
            )

        logger.info(f"Assigned starter rods to user {telegram_id}")

    if conn is not None:
        await _assign(conn)
        return

    pool = await get_pool()
    async with pool.acquire() as pooled_conn:
        await _assign(pooled_conn)

async def ensure_user_has_level(telegram_id: int):
    """Ensure user has level and experience columns set"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if user has level set
        level = await conn.fetchval(
            'SELECT level FROM users WHERE telegram_id = $1', 
            telegram_id
        )
        
        if level is None:
            await conn.execute('''
                UPDATE users 
                SET level = 1, experience = 0 
                WHERE telegram_id = $1
            ''', telegram_id)
            print(f"Set default level for user {telegram_id}")

async def create_position_with_gear(telegram_id: int, pond_id: int, rod_id: int, entry_price: float):
    """Create new fishing position with specific pond and rod"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO positions (user_id, pond_id, rod_id, entry_price, entry_time)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
        ''', telegram_id, pond_id, rod_id, entry_price)
    print(f"Created position for user {telegram_id} with pond {pond_id} and rod {rod_id}")

async def get_pond_by_id(pond_id: int) -> Optional[asyncpg.Record]:
    """Get pond by ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM ponds WHERE id = $1', pond_id)

async def get_rod_by_id(rod_id: int) -> Optional[asyncpg.Record]:
    """Get rod by ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM rods WHERE id = $1', rod_id)

async def get_suitable_fish(pnl_percent: float, user_level: int, pond_id: int, rod_id: int) -> Optional[asyncpg.Record]:
    """Get fish that can be caught based on conditions with rarity weighting"""
    import random
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get all fish that match basic conditions
        all_matching_fish = await conn.fetch('''
            SELECT * FROM fish 
            WHERE min_pnl <= $1 AND max_pnl >= $1 AND min_user_level <= $2
        ''', pnl_percent, user_level)
    
    if not all_matching_fish:
        return None
    
    # Filter fish based on pond and rod requirements
    suitable_fish = []
    
    for fish in all_matching_fish:
        # Check pond requirement
        pond_ok = True
        if fish['required_ponds'] and fish['required_ponds'].strip():
            pond_list = [p.strip() for p in fish['required_ponds'].split(',')]
            pond_ok = str(pond_id) in pond_list
        
        # Check rod requirement  
        rod_ok = True
        if fish['required_rods'] and fish['required_rods'].strip():
            rod_list = [r.strip() for r in fish['required_rods'].split(',')]
            rod_ok = str(rod_id) in rod_list
        
        if pond_ok and rod_ok:
            suitable_fish.append(fish)
    
    if not suitable_fish:
        return None
    
    # Apply rarity-based weighting for selection
    rarity_weights = {
        'trash': 1.0,
        'common': 0.8,
        'rare': 0.4,
        'epic': 0.15,
        'legendary': 0.05
    }
    
    # Create weighted list for random selection
    weighted_fish = []
    for fish in suitable_fish:
        rarity = fish['rarity']
        weight = rarity_weights.get(rarity, 0.5)
        copies = max(1, int(weight * 20))
        weighted_fish.extend([fish] * copies)
    
    # Randomly select from weighted list
    return random.choice(weighted_fish)

async def get_fish_by_id(fish_id: int) -> Optional[asyncpg.Record]:
    """Get fish by ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM fish WHERE id = $1', fish_id)

async def get_fish_image_cache(fish_id: int, rarity: str) -> Optional[Dict[str, str]]:
    """Get cached image for fish - returns dict with image_path and cdn_url"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow('''
            SELECT image_path, cdn_url FROM fish_images 
            WHERE fish_id = $1 AND rarity = $2
        ''', fish_id, rarity)
        if result:
            return dict(result)
        return None

async def save_fish_image_cache(fish_id: int, rarity: str, image_path: str, cache_key: str, cdn_url: str = None):
    """Save generated image to cache with optional CDN URL"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO fish_images (fish_id, rarity, image_path, cache_key, cdn_url)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (cache_key) DO UPDATE 
            SET image_path = $3, cdn_url = $5
        ''', fish_id, rarity, image_path, cache_key, cdn_url)

async def get_total_fish_count() -> int:
    """Get total number of fish in database"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval('SELECT COUNT(*) FROM fish')
        return result or 0

async def get_user_unique_fish_count(telegram_id: int) -> int:
    """Get count of unique fish caught by user"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT COUNT(DISTINCT fish_caught_id) 
            FROM positions 
            WHERE user_id = $1 AND fish_caught_id IS NOT NULL
        ''', telegram_id)
        return result or 0

async def get_user_stats(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Get comprehensive user statistics"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get basic user info
        user_data = await conn.fetchrow('''
            SELECT username, bait_tokens, level, experience, created_at
            FROM users WHERE telegram_id = $1
        ''', telegram_id)
        
        if not user_data:
            return None
        
        # Get fishing statistics
        fishing_stats = await conn.fetchrow('''
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(CASE WHEN status = 'closed' THEN 1 END) as completed_sessions,
                AVG(CASE WHEN status = 'closed' AND pnl_percent IS NOT NULL THEN pnl_percent END) as avg_pnl,
                MAX(CASE WHEN status = 'closed' AND pnl_percent IS NOT NULL THEN pnl_percent END) as best_pnl,
                MIN(CASE WHEN status = 'closed' AND pnl_percent IS NOT NULL THEN pnl_percent END) as worst_pnl
            FROM positions WHERE user_id = $1
        ''', telegram_id)
        
        # Get fish collection stats
        fish_collection = await conn.fetch('''
            SELECT f.name, f.emoji, f.rarity, COUNT(*) as catch_count
            FROM positions p
            JOIN fish f ON p.fish_caught_id = f.id
            WHERE p.user_id = $1 AND p.status = 'closed'
            GROUP BY f.id, f.name, f.emoji, f.rarity
            ORDER BY catch_count DESC, f.min_pnl DESC
        ''', telegram_id)
        
        # Get owned rods
        owned_rods = await conn.fetch('''
            SELECT r.name, r.leverage, r.rarity
            FROM user_rods ur
            JOIN rods r ON ur.rod_id = r.id
            WHERE ur.user_id = $1
            ORDER BY r.leverage DESC
        ''', telegram_id)
        
        return {
            'user': user_data,
            'fishing': fishing_stats,
            'fish_collection': fish_collection,
            'rods': owned_rods
        }

# AI Prompt Management Functions
async def get_fish_ai_prompt(fish_id: int) -> Optional[str]:
    """Get AI prompt for specific fish"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval('SELECT ai_prompt FROM fish WHERE id = $1', fish_id)

async def update_fish_ai_prompt(fish_id: int, ai_prompt: str) -> bool:
    """Update AI prompt for specific fish"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            'UPDATE fish SET ai_prompt = $1 WHERE id = $2', 
            ai_prompt, fish_id
        )
        return result.split()[-1] != '0'

async def get_all_fish_prompts() -> List[asyncpg.Record]:
    """Get all fish with their AI prompts for bulk management"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch('''
            SELECT id, name, emoji, rarity, ai_prompt 
            FROM fish 
            ORDER BY rarity, name
        ''')

async def update_fish_prompts_bulk(prompts_data: List[tuple]) -> int:
    """Update multiple fish prompts at once"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # PostgreSQL doesn't support executemany for UPDATE efficiently
        # Use a transaction with multiple updates
        updated_count = 0
        async with conn.transaction():
            for fish_id, prompt in prompts_data:
                result = await conn.execute(
                    'UPDATE fish SET ai_prompt = $1 WHERE id = $2',
                    prompt, fish_id
                )
                if result.split()[-1] != '0':
                    updated_count += 1
        return updated_count

async def get_fish_by_name(fish_name: str) -> Optional[asyncpg.Record]:
    """Get fish by name for easier prompt management"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM fish WHERE name = $1', fish_name)

# Legacy compatibility function
async def get_suitable_fish_old(pnl_percent: float, user_level: int, pond_id: int, rod_id: int) -> Optional[asyncpg.Record]:
    """Legacy fish selection - kept for compatibility"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT * FROM fish 
            WHERE min_pnl <= $1 AND max_pnl >= $1 AND min_user_level <= $2
            ORDER BY 
                CASE 
                    WHEN required_ponds = '' THEN 1 
                    WHEN position('%s' in required_ponds) > 0 THEN 0
                    ELSE 2
                END,
                CASE 
                    WHEN required_rods = '' THEN 1 
                    WHEN position('%s' in required_rods) > 0 THEN 0
                    ELSE 2
                END,
                RANDOM()
            LIMIT 1
        ''' % (str(pond_id), str(rod_id)), pnl_percent, user_level)

# === WEB APP FUNCTIONS ===

async def get_user_fish_collection(user_id: int) -> List[asyncpg.Record]:
    """Get user's fish collection with detailed information for web app"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch('''
            SELECT 
                p.id as position_id,
                p.pnl_percent,
                p.exit_time,
                f.id as fish_id,
                f.name as fish_name,
                f.emoji as fish_emoji,
                f.description as fish_description,
                f.rarity as fish_rarity,
                r.name as rod_name,
                pond.name as pond_name
            FROM positions p
            LEFT JOIN fish f ON p.fish_caught_id = f.id
            LEFT JOIN rods r ON p.rod_id = r.id
            LEFT JOIN ponds pond ON p.pond_id = pond.id
            WHERE p.user_id = $1 AND p.fish_caught_id IS NOT NULL
            ORDER BY p.exit_time DESC
        ''', user_id)

async def get_user_fish_history(user_id: int, fish_id: int) -> List[asyncpg.Record]:
    """Get all catches of a specific fish by user"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch('''
            SELECT 
                p.pnl_percent,
                p.exit_time,
                p.entry_time,
                r.name as rod_name,
                pond.name as pond_name,
                pond.trading_pair
            FROM positions p
            LEFT JOIN rods r ON p.rod_id = r.id
            LEFT JOIN ponds pond ON p.pond_id = pond.id
            WHERE p.user_id = $1 AND p.fish_caught_id = $2
            ORDER BY p.exit_time DESC
        ''', user_id, fish_id)

async def get_user_statistics(user_id: int) -> Optional[asyncpg.Record]:
    """Get comprehensive user statistics for web app"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT 
                u.telegram_id,
                u.username,
                u.level,
                u.experience,
                u.bait_tokens,
                u.created_at,
                COUNT(DISTINCT p.fish_caught_id) as unique_fish_caught,
                COUNT(p.id) as total_catches,
                AVG(p.pnl_percent) as average_pnl,
                MAX(p.pnl_percent) as best_pnl,
                MIN(p.pnl_percent) as worst_pnl
            FROM users u
            LEFT JOIN positions p ON u.telegram_id = p.user_id AND p.fish_caught_id IS NOT NULL
            WHERE u.telegram_id = $1
            GROUP BY u.telegram_id, u.username, u.level, u.experience, u.bait_tokens, u.created_at
        ''', user_id)

# === ACTIVE ROD MANAGEMENT ===

async def get_user_active_rod(user_id: int) -> Optional[asyncpg.Record]:
    """Get user's currently active rod"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT r.* FROM user_settings us
            JOIN rods r ON us.active_rod_id = r.id
            WHERE us.user_id = $1
        ''', user_id)

async def set_user_active_rod(user_id: int, rod_id: int) -> bool:
    """Set user's active rod. Returns True if successful"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verify user owns the rod
        ownership = await conn.fetchval('''
            SELECT 1 FROM user_rods WHERE user_id = $1 AND rod_id = $2
        ''', user_id, rod_id)
        
        if not ownership:
            return False
        
        # Upsert user settings
        await conn.execute('''
            INSERT INTO user_settings (user_id, active_rod_id, updated_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET active_rod_id = $2, updated_at = CURRENT_TIMESTAMP
        ''', user_id, rod_id)
        
        return True

async def ensure_user_has_active_rod(user_id: int) -> Optional[asyncpg.Record]:
    """Ensure user has an active rod set. If not, set first available Long rod as active"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if user already has active rod
        active_rod = await conn.fetchrow('''
            SELECT r.* FROM user_settings us
            JOIN rods r ON us.active_rod_id = r.id
            WHERE us.user_id = $1
        ''', user_id)
        
        if active_rod:
            return active_rod
        
        # Find first Long rod user owns (prefer starter rods)
        preferred_rod = await conn.fetchrow('''
            SELECT r.* FROM user_rods ur
            JOIN rods r ON ur.rod_id = r.id
            WHERE ur.user_id = $1 AND r.rod_type = 'long'
            ORDER BY r.is_starter DESC, r.id ASC
            LIMIT 1
        ''', user_id)
        
        if not preferred_rod:
            # Fallback to any rod user owns
            preferred_rod = await conn.fetchrow('''
                SELECT r.* FROM user_rods ur
                JOIN rods r ON ur.rod_id = r.id
                WHERE ur.user_id = $1
                ORDER BY r.is_starter DESC, r.id ASC
                LIMIT 1
            ''', user_id)
        
        if preferred_rod:
            # Set as active rod
            await conn.execute('''
                INSERT INTO user_settings (user_id, active_rod_id, updated_at)
                VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) 
                DO UPDATE SET active_rod_id = $2, updated_at = CURRENT_TIMESTAMP
            ''', user_id, preferred_rod['id'])
            
            return preferred_rod
            
        return None

# === VIRTUAL BALANCE & LEADERBOARD FUNCTIONS ===

async def get_user_virtual_balance(user_id: int) -> dict:
    """Get user's balance from user_balances table with trading stats"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get balance from user_balances
        balance = await conn.fetchval(
            'SELECT balance FROM user_balances WHERE user_id = $1',
            user_id
        )

        # Get trading stats from positions
        stats = await conn.fetchrow('''
            SELECT COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END) as winning_trades,
                   AVG(pnl_percent) as avg_pnl
            FROM positions
            WHERE user_id = $1 AND status = 'closed'
        ''', user_id)

        return {
            'balance': float(balance) if balance else 0.0,
            'total_trades': stats['total_trades'] or 0,
            'winning_trades': stats['winning_trades'] or 0,
            'avg_pnl': float(stats['avg_pnl']) if stats['avg_pnl'] else 0
        }

async def get_flexible_leaderboard(
    pond_id: Optional[int] = None,
    rod_id: Optional[int] = None,
    time_period: Optional[str] = None,  # 'day', 'week', 'month', 'all'
    user_id: Optional[int] = None,  # for specific user position
    limit: int = 10,
    include_bottom: bool = True
) -> Dict[str, Any]:
    """
    Universal leaderboard with multiple filters
    
    Returns:
        {
            'top': [...],
            'bottom': [...],
            'user_position': {...},
            'total_players': int,
            'filters_applied': {...}
        }
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Build WHERE conditions
        where_conditions = ["p.status = 'closed'"]
        params = []
        param_counter = 1
        
        if pond_id:
            where_conditions.append(f"p.pond_id = ${param_counter}")
            params.append(pond_id)
            param_counter += 1
            
        if rod_id:
            where_conditions.append(f"p.rod_id = ${param_counter}")
            params.append(rod_id)
            param_counter += 1
        
        # Time filters
        if time_period and time_period != 'all':
            time_intervals = {
                'day': "INTERVAL '1 day'",
                'week': "INTERVAL '7 days'",
                'month': "INTERVAL '30 days'",
                'year': "INTERVAL '365 days'"
            }
            if time_period in time_intervals:
                where_conditions.append(
                    f"p.exit_time >= CURRENT_TIMESTAMP - {time_intervals[time_period]}"
                )
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Main query with ranks - using user_balances table
        query = f'''
            WITH user_stats AS (
                SELECT
                    u.telegram_id,
                    u.username,
                    u.level,
                    ub.balance,
                    COUNT(p.id) as total_trades,
                    AVG(p.pnl_percent) as avg_pnl,
                    MAX(p.pnl_percent) as best_trade,
                    MIN(p.pnl_percent) as worst_trade,
                    MAX(p.exit_time) as last_trade_time,
                    RANK() OVER (ORDER BY ub.balance DESC) as rank
                FROM users u
                LEFT JOIN user_balances ub ON u.telegram_id = ub.user_id
                LEFT JOIN positions p ON u.telegram_id = p.user_id AND {where_clause}
                GROUP BY u.telegram_id, u.username, u.level, ub.balance
                HAVING COUNT(p.id) > 0  -- Only active players
            ),
            stats AS (
                SELECT COUNT(*) as total_players FROM user_stats
            )
            SELECT
                us.*,
                s.total_players
            FROM user_stats us
            CROSS JOIN stats s
            ORDER BY us.balance DESC
        '''
        
        all_results = await conn.fetch(query, *params)
        
        if not all_results:
            return {
                'top': [],
                'bottom': [],
                'user_position': None,
                'total_players': 0,
                'filters_applied': {
                    'pond_id': pond_id,
                    'rod_id': rod_id,
                    'time_period': time_period
                }
            }
        
        # Process results
        total_players = all_results[0]['total_players'] if all_results else 0
        
        # Top players
        top_players = all_results[:limit]
        
        # Bottom players (if needed)
        bottom_players = []
        if include_bottom and len(all_results) > limit:
            bottom_players = all_results[-limit:]
            bottom_players.reverse()  # From worst to better
        
        # Specific user position
        user_position = None
        if user_id:
            user_data = next((r for r in all_results if r['telegram_id'] == user_id), None)
            if user_data:
                user_position = {
                    'rank': user_data['rank'],
                    'balance': float(user_data['balance']),
                    'total_trades': user_data['total_trades'],
                    'avg_pnl': float(user_data['avg_pnl']) if user_data['avg_pnl'] else 0,
                    'percentile': round((1 - user_data['rank'] / total_players) * 100, 1) if total_players > 0 else 100
                }
        
        return {
            'top': [dict(r) for r in top_players],
            'bottom': [dict(r) for r in bottom_players],
            'user_position': user_position,
            'total_players': total_players,
            'filters_applied': {
                'pond_id': pond_id,
                'rod_id': rod_id,
                'time_period': time_period
            }
        }

async def get_weekly_leaderboard(user_id: Optional[int] = None):
    """Weekly leaderboard"""
    return await get_flexible_leaderboard(
        time_period='week',
        user_id=user_id
    )

async def get_daily_leaderboard(user_id: Optional[int] = None):
    """Daily leaderboard"""
    return await get_flexible_leaderboard(
        time_period='day',
        user_id=user_id
    )

# === GROUP POND MANAGEMENT ===

def get_pond_name_and_type(group_name: str, member_count: int) -> tuple:
    """Generate pond name and available trading pair count

    Currently returns just group name with 1 trading pair.
    Future: scale trading pairs based on group size.
    """
    # For now, all ponds have 1 trading pair regardless of size
    # Future expansion: unlock more pairs as groups grow
    return group_name, 1

def get_available_trading_pairs(pair_count: int) -> List[tuple]:
    """Get available trading pairs based on pond size"""
    all_pairs = [
        ('TAC/USDT', 'TAC', 'USDT'),
        ('BTC/USDT', 'BTC', 'USDT'),
        ('SOL/USDT', 'SOL', 'USDT'),
        ('ADA/USDT', 'ADA', 'USDT'),
        ('MATIC/USDT', 'MATIC', 'USDT'),
        ('AVAX/USDT', 'AVAX', 'USDT'),
        ('LINK/USDT', 'LINK', 'USDT'),
        ('DOT/USDT', 'DOT', 'USDT')
    ]
    return all_pairs[:pair_count]

async def create_or_update_group_pond(chat_id: int, chat_title: str, chat_type: str, member_count: int):
    """Create or update a group pond based on current group stats"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Generate pond name and get trading pairs
        pond_name, pair_count = get_pond_name_and_type(chat_title, member_count)
        trading_pairs = get_available_trading_pairs(pair_count)
        
        # Check if group pond already exists
        existing_pond = await conn.fetchrow(
            'SELECT * FROM ponds WHERE chat_id = $1 AND pond_type = $2',
            chat_id, 'group'
        )
        
        if existing_pond:
            # Update existing pond
            await conn.execute('''
                UPDATE ponds 
                SET name = $1, member_count = $2, is_active = true
                WHERE chat_id = $3 AND pond_type = 'group'
            ''', pond_name, member_count, chat_id)
            
            logger.info(f"Updated group pond: {pond_name} ({member_count} members)")
            return existing_pond['id']
        else:
            # Create new pond with primary trading pair (first one)
            primary_pair = trading_pairs[0] if trading_pairs else ('TAC/USDT', 'TAC', 'USDT')
            
            result = await conn.fetchrow('''
                INSERT INTO ponds (name, trading_pair, base_currency, quote_currency, 
                                 required_level, is_active, chat_id, chat_type, member_count, pond_type)
                VALUES ($1, $2, $3, $4, 1, true, $5, $6, $7, 'group')
                RETURNING id
            ''', pond_name, primary_pair[0], primary_pair[1], primary_pair[2], 
                 chat_id, chat_type, member_count)
            
            logger.info(f"Created new group pond: {pond_name} ({member_count} members)")
            return result['id']

async def deactivate_group_pond(chat_id: int):
    """Deactivate group pond when bot is removed from group"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE ponds 
            SET is_active = false
            WHERE chat_id = $1 AND pond_type = 'group'
        ''', chat_id)
        logger.info(f"Deactivated group pond for chat {chat_id}")

async def add_user_to_group(user_id: int, chat_id: int):
    """Add user to group membership"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO group_memberships (user_id, chat_id, is_active)
            VALUES ($1, $2, true)
            ON CONFLICT (user_id, chat_id) 
            DO UPDATE SET is_active = true, joined_at = CURRENT_TIMESTAMP
        ''', user_id, chat_id)

async def remove_user_from_group(user_id: int, chat_id: int):
    """Remove user from group membership"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE group_memberships
            SET is_active = false
            WHERE user_id = $1 AND chat_id = $2
        ''', user_id, chat_id)

async def is_user_in_group_pond(user_id: int, chat_id: int) -> bool:
    """Check if user is already a member of a group pond"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT EXISTS(
                SELECT 1 FROM group_memberships
                WHERE user_id = $1 AND chat_id = $2 AND is_active = true
            )
        ''', user_id, chat_id)
        return result

async def get_user_group_ponds(user_id: int) -> List[asyncpg.Record]:
    """Get all active group ponds that user has access to"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch('''
            SELECT p.* FROM ponds p
            JOIN group_memberships gm ON p.chat_id = gm.chat_id
            WHERE gm.user_id = $1 AND gm.is_active = true 
            AND p.is_active = true AND p.pond_type = 'group'
            ORDER BY p.member_count DESC, p.name
        ''', user_id)

async def get_group_pond_by_chat_id(chat_id: int) -> Optional[asyncpg.Record]:
    """Get group pond by chat ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT * FROM ponds 
            WHERE chat_id = $1 AND pond_type = 'group' AND is_active = true
        ''', chat_id)

async def update_group_member_count(chat_id: int, member_count: int):
    """Update member count for a group pond"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get current pond info
        pond = await conn.fetchrow('''
            SELECT * FROM ponds WHERE chat_id = $1 AND pond_type = 'group'
        ''', chat_id)
        
        if pond:
            # Pond name stays the same (just the group name), only update member count
            await conn.execute('''
                UPDATE ponds
                SET member_count = $1
                WHERE chat_id = $2 AND pond_type = 'group'
            ''', member_count, chat_id)

            logger.info(f"Updated group pond member count: {pond['name']} ({member_count} members)")

# === PAYMENTS & TRANSACTIONS SYSTEM ===

async def get_available_products() -> List[asyncpg.Record]:
    """Get all available BAIT products"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch('''
            SELECT * FROM products 
            WHERE is_active = true
            ORDER BY stars_price ASC
        ''')

async def get_product_by_id(product_id: int) -> Optional[asyncpg.Record]:
    """Get product by ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT * FROM products WHERE id = $1 AND is_active = true
        ''', product_id)

async def create_transaction(user_id: int, product_id: int, quantity: int, 
                           stars_amount: int, bait_amount: int, payload: str) -> str:
    """Create new transaction and return unique transaction ID"""
    import uuid
    transaction_id = str(uuid.uuid4())
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO transactions 
            (user_id, product_id, quantity, stars_amount, bait_amount, payload, status)
            VALUES ($1, $2, $3, $4, $5, $6, 'pending')
        ''', user_id, product_id, quantity, stars_amount, bait_amount, payload)
    
    return transaction_id

async def get_transaction_by_payload(payload: str) -> Optional[asyncpg.Record]:
    """Get transaction by payload"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT * FROM transactions WHERE payload = $1
        ''', payload)

async def complete_transaction(transaction_id: int, payment_charge_id: str, 
                             telegram_payment_charge_id: str, provider_payment_charge_id: str) -> bool:
    """Complete transaction and add BAIT tokens to user"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Get transaction info
            transaction = await conn.fetchrow('''
                SELECT * FROM transactions WHERE id = $1 AND status = 'pending'
            ''', transaction_id)
            
            if not transaction:
                return False
            
            # Update transaction status
            await conn.execute('''
                UPDATE transactions 
                SET status = 'completed', 
                    payment_charge_id = $1,
                    telegram_payment_charge_id = $2,
                    provider_payment_charge_id = $3,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = $4
            ''', payment_charge_id, telegram_payment_charge_id, provider_payment_charge_id, transaction_id)
            
            # Add BAIT tokens to user
            bait_to_add = transaction['bait_amount'] * transaction['quantity']
            await conn.execute('''
                UPDATE users 
                SET bait_tokens = bait_tokens + $1
                WHERE telegram_id = $2
            ''', bait_to_add, transaction['user_id'])
            
            logger.info(f"Transaction {transaction_id} completed: added {bait_to_add} BAIT to user {transaction['user_id']}")
            return True

async def fail_transaction(transaction_id: int, error_message: str = None) -> bool:
    """Mark transaction as failed"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute('''
            UPDATE transactions 
            SET status = 'failed'
            WHERE id = $1 AND status = 'pending'
        ''', transaction_id)
        return result.split()[-1] != '0'

async def get_user_transactions(user_id: int, limit: int = 10) -> List[asyncpg.Record]:
    """Get user's transaction history"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch('''
            SELECT t.*, p.name as product_name, p.description as product_description
            FROM transactions t
            LEFT JOIN products p ON t.product_id = p.id
            WHERE t.user_id = $1
            ORDER BY t.created_at DESC
            LIMIT $2
        ''', user_id, limit)

async def refund_transaction(transaction_id: int) -> bool:
    """Refund a completed transaction (subtract BAIT tokens)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Get transaction info
            transaction = await conn.fetchrow('''
                SELECT * FROM transactions WHERE id = $1 AND status = 'completed'
            ''', transaction_id)
            
            if not transaction:
                return False
            
            # Check if user has enough BAIT tokens
            user = await conn.fetchrow('''
                SELECT bait_tokens FROM users WHERE telegram_id = $1
            ''', transaction['user_id'])
            
            bait_to_subtract = transaction['bait_amount'] * transaction['quantity']
            if user['bait_tokens'] < bait_to_subtract:
                logger.warning(f"Cannot refund transaction {transaction_id}: user has insufficient BAIT tokens")
                return False
            
            # Update transaction status
            await conn.execute('''
                UPDATE transactions 
                SET status = 'refunded'
                WHERE id = $1
            ''', transaction_id)
            
            # Subtract BAIT tokens from user
            await conn.execute('''
                UPDATE users 
                SET bait_tokens = bait_tokens - $1
                WHERE telegram_id = $2
            ''', bait_to_subtract, transaction['user_id'])
            
            logger.info(f"Transaction {transaction_id} refunded: subtracted {bait_to_subtract} BAIT from user {transaction['user_id']}")
            return True


# Onboarding system functions
async def get_onboarding_progress(user_id: int) -> Optional[asyncpg.Record]:
    """Get user's onboarding progress"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            SELECT * FROM onboarding_progress WHERE user_id = $1
        ''', user_id)

async def create_onboarding_progress(user_id: int, step: str = 'intro'):
    """Create initial onboarding progress for new user"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO onboarding_progress (
                user_id,
                current_step,
                completed,
                first_cast_used,
                first_hook_used,
                group_bonus_claimed,
                first_catch_reward_claimed
            )
            VALUES ($1, $2, FALSE, FALSE, FALSE, FALSE, FALSE)
            ON CONFLICT (user_id) DO NOTHING
        ''', user_id, step)
        logger.info(f"Created onboarding progress for user {user_id} at step {step}")

async def update_onboarding_step(user_id: int, step: str):
    """Update user's current onboarding step"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE onboarding_progress 
            SET current_step = $2, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
        ''', user_id, step)
        logger.info(f"Updated onboarding step for user {user_id} to {step}")

async def mark_onboarding_action(user_id: int, action: str):
    """Mark specific onboarding action as completed (first_cast_used, first_hook_used)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if action == 'first_cast':
            await conn.execute('''
                UPDATE onboarding_progress 
                SET first_cast_used = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            ''', user_id)
        elif action == 'first_hook':
            await conn.execute('''
                UPDATE onboarding_progress 
                SET first_hook_used = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            ''', user_id)
        logger.info(f"Marked onboarding action {action} for user {user_id}")

async def award_group_bonus(user_id: int, bait_reward: int = 10) -> str:
    """Grant BAIT bonus for joining the primary group if not yet claimed."""
    progress = await get_onboarding_progress(user_id)
    if not progress:
        await create_onboarding_progress(user_id)
        progress = await get_onboarding_progress(user_id)

    progress_map = dict(progress) if progress else {}

    if progress_map.get('group_bonus_claimed'):
        logger.info("Group bonus already claimed by user %s", user_id)
        return "You already claimed this bonus."

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''
                UPDATE onboarding_progress
                SET group_bonus_claimed = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
                ''',
                user_id,
            )
            await conn.execute(
                '''
                UPDATE users
                SET bait_tokens = bait_tokens + $1
                WHERE telegram_id = $2
                ''',
                bait_reward,
                user_id,
            )

    logger.info("Granted %s BAIT group bonus to user %s", bait_reward, user_id)
    return f"🪱 +{bait_reward} BAIT for connecting a new pond!"

async def award_first_catch_reward(user_id: int, balance_reward: int = 10000) -> str:
    """Grant first-catch reward by adding to user balance"""
    progress = await get_onboarding_progress(user_id)
    if not progress:
        await create_onboarding_progress(user_id)
        progress = await get_onboarding_progress(user_id)

    progress_map = dict(progress) if progress else {}

    if progress_map.get('first_catch_reward_claimed'):
        logger.info("First catch reward already claimed by user %s", user_id)
        return "🏆 First catch reward already claimed."

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                'UPDATE onboarding_progress SET first_catch_reward_claimed = TRUE, updated_at = CURRENT_TIMESTAMP WHERE user_id = $1',
                user_id,
            )
            # Add bonus to user_balances - use INSERT ON CONFLICT to create record if it doesn't exist
            await conn.execute('''
                INSERT INTO user_balances (user_id, balance)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET balance = user_balances.balance + $2, updated_at = CURRENT_TIMESTAMP
            ''', user_id, balance_reward)

    logger.info("Granted $%s balance bonus first-catch reward to user %s", balance_reward, user_id)
    return f"🏆 +${balance_reward} virtual balance for your first catch!\n🐟 Keep fishing — rare fish bring even more rewards."


async def award_first_cast_reward(user_id: int) -> Optional[str]:
    """Grant Short rod reward for the first cast if not yet claimed"""
    progress = await get_onboarding_progress(user_id)
    if not progress:
        await create_onboarding_progress(user_id)
        progress = await get_onboarding_progress(user_id)

    progress_map = dict(progress) if progress else {}

    if progress_map.get('first_cast_reward_claimed'):
        return None

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''
                UPDATE onboarding_progress
                SET first_cast_reward_claimed = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
                ''',
                user_id,
            )
            # Give Short rod (user already has Long from registration)
            await give_single_starter_rod(user_id, rod_type='short', conn=conn)

    logger.info("Granted Short rod to user %s after first cast", user_id)
    return (
        "🎣 New rod unlocked!\n\n"
        "You got the Short rod with negative leverage for bearish positions. "
        "Now you have both Long & Short rods!"
    )

async def complete_onboarding(user_id: int):
    """Mark onboarding as completed for user"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE onboarding_progress 
            SET completed = TRUE, current_step = 'completed', updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
        ''', user_id)
        logger.info(f"Completed onboarding for user {user_id}")

async def is_onboarding_completed(user_id: int) -> bool:
    """Check if user has completed onboarding"""
    progress = await get_onboarding_progress(user_id)
    if not progress:
        return False
    return progress['completed']

async def can_use_free_cast(user_id: int) -> bool:
    """Check if user can use their free tutorial cast"""
    progress = await get_onboarding_progress(user_id)
    if not progress:
        return False
    return not progress['first_cast_used'] and not progress['completed']

async def can_use_guaranteed_hook(user_id: int) -> bool:
    """Check if user should get guaranteed good catch on hook"""
    progress = await get_onboarding_progress(user_id)
    if not progress:
        return False
    return not progress['first_hook_used'] and not progress['completed']

async def should_get_special_catch(user_id: int) -> Optional[str]:
    """Check if user should get special catch item (like secret letter)"""
    progress = await get_onboarding_progress(user_id)
    if not progress or progress['completed']:
        return None

    return None

async def has_skipped_onboarding_without_rewards(user_id: int) -> bool:
    """Check if user skipped onboarding without receiving group bonus (10 BAIT)

    Returns:
        True if user completed onboarding but never claimed group bonus
    """
    progress = await get_onboarding_progress(user_id)
    if not progress:
        return False

    # User completed onboarding but never claimed the group bonus (10 BAIT)
    return progress['completed'] and not progress['group_bonus_claimed']

async def restart_onboarding_for_rewards(user_id: int):
    """Restart onboarding at JOIN_GROUP step to allow claiming rewards

    This allows users who skipped onboarding to go back and get their 10 BAIT tokens.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE onboarding_progress
            SET completed = FALSE,
                current_step = 'join_group',
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
        ''', user_id)
        logger.info(f"Restarted onboarding for user {user_id} at join_group step")

async def migrate_user_balances() -> int:
    """Migrate existing users to new balance system
    Calculate balance from positions PnL and save to user_balances
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get all users
        users = await conn.fetch('SELECT telegram_id FROM users')
        migrated_count = 0

        for user in users:
            user_id = user['telegram_id']

            # Calculate balance from closed positions only
            result = await conn.fetchrow('''
                SELECT COALESCE(SUM(1000 * pnl_percent / 100), 0) as balance
                FROM positions
                WHERE user_id = $1 AND status = 'closed'
            ''', user_id)

            balance = float(result['balance']) if result else 0.0

            # Insert/update in user_balances
            await conn.execute('''
                INSERT INTO user_balances (user_id, balance)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET balance = $2, updated_at = CURRENT_TIMESTAMP
            ''', user_id, balance)

            migrated_count += 1

        logger.info(f"Migrated {migrated_count} user balances to new system")
        return migrated_count
