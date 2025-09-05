import asyncpg
import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Database connection settings
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/fishing_bot')

# Connection pool
_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    """Get or create connection pool optimized for high load"""
    global _pool
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
        except Exception as e:
            # Don't retry non-connection errors
            logger.error(f"Database operation failed with non-retriable error: {e}")
            raise

async def init_database():
    """Initialize the database with required tables"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Create users table with level system
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                bait_tokens INTEGER DEFAULT 10,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create ponds table
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create user_rods table (many-to-many relationship)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_rods (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                rod_id INTEGER,
                acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                FOREIGN KEY (rod_id) REFERENCES rods (id),
                UNIQUE(user_id, rod_id)
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
                FOREIGN KEY (user_id) REFERENCES users (telegram_id),
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fish_id) REFERENCES fish (id)
            )
        ''')
        
        # Insert default data
        await _insert_default_ponds(conn)
        await _insert_default_rods(conn)
        await _insert_default_fish(conn)
        
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
    """Create new user with default BAIT tokens and starter rod"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (telegram_id, username, bait_tokens, level, experience)
            VALUES ($1, $2, 10, 1, 0)
            ON CONFLICT (telegram_id) DO NOTHING
        ''', telegram_id, username)
    
    # Give starter rod
    await give_starter_rod(telegram_id)
    print(f"Created user: {username} ({telegram_id}) with starter rod")

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
            INSERT INTO positions (user_id, entry_price)
            VALUES ($1, $2)
        ''', telegram_id, entry_price)
    print(f"Created position for user {telegram_id} at price {entry_price}")

async def close_position(position_id: int, exit_price: float, pnl_percent: float, fish_caught_id: int):
    """Close fishing position and record results"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE positions 
            SET status = 'closed', exit_price = $1, exit_time = CURRENT_TIMESTAMP,
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

async def _insert_default_ponds(conn: asyncpg.Connection):
    """Insert default ponds if they don't exist"""
    count = await conn.fetchval('SELECT COUNT(*) FROM ponds')
    if count == 0:
        ponds_data = [
            ('🌊 Криптовые Воды', 'ETH/USDT', 'ETH', 'USDT', None, 1, True),
            ('💰 Озеро Профита', 'BTC/USDT', 'BTC', 'USDT', None, 2, True),
            ('⚡ Море Волатильности', 'SOL/USDT', 'SOL', 'USDT', None, 3, True),
            ('🌙 Лунные Пруды', 'ADA/USDT', 'ADA', 'USDT', None, 4, True),
            ('🔥 Вулканические Источники', 'MATIC/USDT', 'MATIC', 'USDT', None, 5, True),
            ('❄️ Ледяные Глубины', 'AVAX/USDT', 'AVAX', 'USDT', None, 6, True),
            ('🌈 Радужные Заводи', 'LINK/USDT', 'LINK', 'USDT', None, 7, True),
            ('🏔️ Горные Озёра', 'DOT/USDT', 'DOT', 'USDT', None, 8, True)
        ]
        
        await conn.executemany('''
            INSERT INTO ponds (name, trading_pair, base_currency, quote_currency, image_url, required_level, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        ''', ponds_data)

async def _insert_default_rods(conn: asyncpg.Connection):
    """Insert default rods if they don't exist"""
    count = await conn.fetchval('SELECT COUNT(*) FROM rods')
    if count == 0:
        rods_data = [
            ('🎣 Стартовая удочка', 1.5, 0, None, 'common', True),
            ('🌊 Морская удочка', 2.0, 50, None, 'common', False),
            ('⚡ Электрическая удочка', 2.5, 100, None, 'rare', False),
            ('🔥 Огненная удочка', 3.0, 200, None, 'rare', False),
            ('💎 Алмазная удочка', 3.5, 500, None, 'epic', False),
            ('🌙 Лунная удочка', 4.0, 1000, None, 'epic', False),
            ('☀️ Солнечная удочка', 5.0, 2000, None, 'legendary', False),
            ('🎯 Мастерская удочка', 6.0, 5000, None, 'legendary', False)
        ]
        
        await conn.executemany('''
            INSERT INTO rods (name, leverage, price, image_url, rarity, is_starter)
            VALUES ($1, $2, $3, $4, $5, $6)
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

async def get_available_ponds(user_level: int) -> List[asyncpg.Record]:
    """Get ponds available for user level"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch('''
            SELECT * FROM ponds 
            WHERE required_level <= $1 AND is_active = true
            ORDER BY required_level
        ''', user_level)

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

async def give_starter_rod(telegram_id: int):
    """Give starter rod to user if they don't have any"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if user already has rods
        has_rods = await conn.fetchval(
            'SELECT COUNT(*) FROM user_rods WHERE user_id = $1', 
            telegram_id
        )
        
        if not has_rods:
            # Get starter rod ID
            starter_rod_id = await conn.fetchval(
                'SELECT id FROM rods WHERE is_starter = true LIMIT 1'
            )
            
            if starter_rod_id:
                await conn.execute('''
                    INSERT INTO user_rods (user_id, rod_id)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id, rod_id) DO NOTHING
                ''', telegram_id, starter_rod_id)
                print(f"Gave starter rod to user {telegram_id}")

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
            INSERT INTO positions (user_id, pond_id, rod_id, entry_price)
            VALUES ($1, $2, $3, $4)
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

async def get_fish_image_cache(fish_id: int, rarity: str) -> Optional[str]:
    """Get cached image for fish"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT image_path FROM fish_images 
            WHERE fish_id = $1 AND rarity = $2
        ''', fish_id, rarity)
        return result

async def save_fish_image_cache(fish_id: int, rarity: str, image_path: str, cache_key: str):
    """Save generated image to cache"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO fish_images (fish_id, rarity, image_path, cache_key)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (cache_key) DO UPDATE SET image_path = $3
        ''', fish_id, rarity, image_path, cache_key)

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