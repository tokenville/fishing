import asyncpg
import os
from datetime import datetime
import asyncio

# PostgreSQL connection URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/fishing_bot')

async def init_database():
    """Initialize the database with required tables"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
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
        
        # Create updated positions table
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
        
        # Insert default ponds
        await _insert_default_ponds(conn)
        # Insert default rods  
        await _insert_default_rods(conn)
        # Insert default fish
        await _insert_default_fish(conn)
        
        print("Database initialized successfully!")
    finally:
        await conn.close()

async def get_user(telegram_id):
    """Get user by telegram_id"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        user = await conn.fetchrow('SELECT * FROM users WHERE telegram_id = $1', telegram_id)
        return dict(user) if user else None
    finally:
        await conn.close()

async def create_user(telegram_id, username):
    """Create new user with default BAIT tokens and starter rod"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            INSERT INTO users (telegram_id, username, bait_tokens, level, experience)
            VALUES ($1, $2, 10, 1, 0)
        ''', telegram_id, username)
        
        # Give starter rod
        await give_starter_rod(telegram_id)
        print(f"Created user: {username} ({telegram_id}) with starter rod")
    finally:
        await conn.close()

async def get_active_position(telegram_id):
    """Get user's active fishing position"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        position = await conn.fetchrow('''
            SELECT * FROM positions 
            WHERE user_id = $1 AND status = 'active'
            ORDER BY entry_time DESC LIMIT 1
        ''', telegram_id)
        return dict(position) if position else None
    finally:
        await conn.close()

async def create_position(telegram_id, entry_price):
    """Create new fishing position"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            INSERT INTO positions (user_id, entry_price)
            VALUES ($1, $2)
        ''', telegram_id, entry_price)
        print(f"Created position for user {telegram_id} at price {entry_price}")
    finally:
        await conn.close()

async def close_position(position_id, exit_price, pnl_percent, fish_caught_id):
    """Close fishing position and record results"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            UPDATE positions 
            SET status = 'closed', exit_price = $2, exit_time = CURRENT_TIMESTAMP,
                pnl_percent = $3, fish_caught_id = $4
            WHERE id = $1
        ''', position_id, exit_price, pnl_percent, fish_caught_id)
    finally:
        await conn.close()

async def use_bait(telegram_id):
    """Use 1 BAIT token for fishing"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.execute('''
            UPDATE users 
            SET bait_tokens = bait_tokens - 1
            WHERE telegram_id = $1 AND bait_tokens > 0
        ''', telegram_id)
        return result != 'UPDATE 0'
    finally:
        await conn.close()

async def _insert_default_ponds(conn):
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

async def _insert_default_rods(conn):
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

async def _insert_default_fish(conn):
    """Insert default fish if they don't exist - only basic ones, full sync via sync_fish_database.py"""
    count = await conn.fetchval('SELECT COUNT(*) FROM fish')
    if count == 0:
        fish_data = [
            ('Старый Сапог', '🦐', 'Мусор со дна водоема', -100, -20, 1, '', '', 'trash', 
             'Вы чувствуете груз разочарования... {emoji} {name}... серьезно? Чей-то мусор стал вашим... тоже мусором.',
             'An old waterlogged leather boot lying on the ocean floor, murky water, disappointing, low quality'),
            
            ('Счастливая Плотва', '🐟', 'Маленькая, но приносящая удачу', 0, 10, 1, '', '', 'common',
             'Маленький, но счастливый улов! {emoji} {name} - маленькая, но считается!',
             'A small shiny silver minnow fish swimming gracefully, clear water, simple, clean')
        ]
        
        await conn.executemany('''
            INSERT INTO fish (name, emoji, description, min_pnl, max_pnl, min_user_level, required_ponds, required_rods, rarity, story_template, ai_prompt)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ''', fish_data)

async def get_available_ponds(user_level):
    """Get ponds available for user level"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        ponds = await conn.fetch('''
            SELECT * FROM ponds 
            WHERE required_level <= $1 AND is_active = true
            ORDER BY required_level
        ''', user_level)
        return [dict(pond) for pond in ponds]
    finally:
        await conn.close()

async def get_user_rods(telegram_id):
    """Get all rods owned by user"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rods = await conn.fetch('''
            SELECT r.* FROM rods r
            JOIN user_rods ur ON r.id = ur.rod_id
            WHERE ur.user_id = $1
            ORDER BY r.leverage
        ''', telegram_id)
        return [dict(rod) for rod in rods]
    finally:
        await conn.close()

async def give_starter_rod(telegram_id):
    """Give starter rod to user if they don't have any"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Check if user already has rods
        has_rods = await conn.fetchval('SELECT COUNT(*) FROM user_rods WHERE user_id = $1', telegram_id)
        
        if has_rods == 0:
            # Get starter rod ID
            starter_rod_id = await conn.fetchval('SELECT id FROM rods WHERE is_starter = true LIMIT 1')
            
            if starter_rod_id:
                await conn.execute('''
                    INSERT INTO user_rods (user_id, rod_id)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id, rod_id) DO NOTHING
                ''', telegram_id, starter_rod_id)
                print(f"Gave starter rod to user {telegram_id}")
    finally:
        await conn.close()

async def ensure_user_has_level(telegram_id):
    """Ensure user has level and experience columns set"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Check if user has level set
        level = await conn.fetchval('SELECT level FROM users WHERE telegram_id = $1', telegram_id)
        
        if not level:
            await conn.execute('''
                UPDATE users 
                SET level = 1, experience = 0 
                WHERE telegram_id = $1
            ''', telegram_id)
            print(f"Set default level for user {telegram_id}")
    finally:
        await conn.close()

async def create_position_with_gear(telegram_id, pond_id, rod_id, entry_price):
    """Create new fishing position with specific pond and rod"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            INSERT INTO positions (user_id, pond_id, rod_id, entry_price)
            VALUES ($1, $2, $3, $4)
        ''', telegram_id, pond_id, rod_id, entry_price)
        print(f"Created position for user {telegram_id} with pond {pond_id} and rod {rod_id}")
    finally:
        await conn.close()

async def get_pond_by_id(pond_id):
    """Get pond by ID"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pond = await conn.fetchrow('SELECT * FROM ponds WHERE id = $1', pond_id)
        return dict(pond) if pond else None
    finally:
        await conn.close()

async def get_rod_by_id(rod_id):
    """Get rod by ID"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rod = await conn.fetchrow('SELECT * FROM rods WHERE id = $1', rod_id)
        return dict(rod) if rod else None
    finally:
        await conn.close()

async def get_suitable_fish(pnl_percent, user_level, pond_id, rod_id):
    """Get fish that can be caught based on conditions with rarity weighting"""
    import random
    
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Get all fish that match basic conditions (PnL range and user level)
        all_matching_fish = await conn.fetch('''
            SELECT * FROM fish 
            WHERE min_pnl <= $1 AND max_pnl >= $2 AND min_user_level <= $3
        ''', pnl_percent, pnl_percent, user_level)
        
        if not all_matching_fish:
            return None
        
        # Filter fish based on pond and rod requirements
        suitable_fish = []
        
        for fish in all_matching_fish:
            fish_dict = dict(fish)
            
            # Check pond requirement
            pond_ok = True
            required_ponds = fish_dict.get('required_ponds', '')
            if required_ponds and required_ponds.strip():
                pond_list = [p.strip() for p in required_ponds.split(',')]
                pond_ok = str(pond_id) in pond_list
            
            # Check rod requirement  
            rod_ok = True
            required_rods = fish_dict.get('required_rods', '')
            if required_rods and required_rods.strip():
                rod_list = [r.strip() for r in required_rods.split(',')]
                rod_ok = str(rod_id) in rod_list
            
            if pond_ok and rod_ok:
                suitable_fish.append(fish_dict)
        
        if not suitable_fish:
            return None
        
        # Apply rarity-based weighting for selection
        rarity_weights = {
            'trash': 1.0,      # Most common
            'common': 0.8,     # Common  
            'rare': 0.4,       # Less common
            'epic': 0.15,      # Rare
            'legendary': 0.05  # Very rare
        }
        
        # Create weighted list for random selection
        weighted_fish = []
        for fish in suitable_fish:
            rarity = fish.get('rarity', 'common')
            weight = rarity_weights.get(rarity, 0.5)
            # Add fish to list multiple times based on weight
            copies = max(1, int(weight * 20))
            weighted_fish.extend([fish] * copies)
        
        # Randomly select from weighted list
        selected_fish = random.choice(weighted_fish)
        return selected_fish
    finally:
        await conn.close()

async def get_fish_by_id(fish_id):
    """Get fish by ID"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        fish = await conn.fetchrow('SELECT * FROM fish WHERE id = $1', fish_id)
        return dict(fish) if fish else None
    finally:
        await conn.close()

async def get_fish_image_cache(fish_id, rarity):
    """Get cached image for fish"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.fetchval('''
            SELECT image_path FROM fish_images 
            WHERE fish_id = $1 AND rarity = $2
        ''', fish_id, rarity)
        return result
    finally:
        await conn.close()

async def save_fish_image_cache(fish_id, rarity, image_path, cache_key):
    """Save generated image to cache"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            INSERT INTO fish_images (fish_id, rarity, image_path, cache_key)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (cache_key) DO UPDATE SET image_path = EXCLUDED.image_path
        ''', fish_id, rarity, image_path, cache_key)
    finally:
        await conn.close()

async def get_user_stats(telegram_id):
    """Get comprehensive user statistics"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
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
            'user': dict(user_data),
            'fishing': dict(fishing_stats),
            'fish_collection': [dict(fish) for fish in fish_collection],
            'rods': [dict(rod) for rod in owned_rods]
        }
    finally:
        await conn.close()

# AI Prompt Management Functions
async def get_fish_ai_prompt(fish_id):
    """Get AI prompt for specific fish"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.fetchval('SELECT ai_prompt FROM fish WHERE id = $1', fish_id)
        return result
    finally:
        await conn.close()

async def update_fish_ai_prompt(fish_id, ai_prompt):
    """Update AI prompt for specific fish"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.execute('UPDATE fish SET ai_prompt = $1 WHERE id = $2', ai_prompt, fish_id)
        return result != 'UPDATE 0'
    finally:
        await conn.close()

async def get_all_fish_prompts():
    """Get all fish with their AI prompts for bulk management"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        fish_prompts = await conn.fetch('''
            SELECT id, name, emoji, rarity, ai_prompt 
            FROM fish 
            ORDER BY rarity, name
        ''')
        return [dict(fish) for fish in fish_prompts]
    finally:
        await conn.close()

async def update_fish_prompts_bulk(prompts_data):
    """Update multiple fish prompts at once"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.executemany('''
            UPDATE fish SET ai_prompt = $1 WHERE id = $2
        ''', [(prompt, fish_id) for fish_id, prompt in prompts_data])
        return len(prompts_data)
    finally:
        await conn.close()

async def get_fish_by_name(fish_name):
    """Get fish by name for easier prompt management"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        fish = await conn.fetchrow('SELECT * FROM fish WHERE name = $1', fish_name)
        return dict(fish) if fish else None
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(init_database())