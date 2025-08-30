import sqlite3
import os

DATABASE_PATH = 'fishing_bot.db'

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create users table with level system
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            bait_tokens INTEGER DEFAULT 10,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create ponds table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ponds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trading_pair TEXT NOT NULL,
            base_currency TEXT NOT NULL,
            quote_currency TEXT NOT NULL,
            image_url TEXT,
            required_level INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create rods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            leverage REAL NOT NULL,
            price INTEGER DEFAULT 0,
            image_url TEXT,
            rarity TEXT DEFAULT 'common',
            is_starter BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create user_rods table (many-to-many relationship)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_rods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            rod_id INTEGER,
            acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id),
            FOREIGN KEY (rod_id) REFERENCES rods (id),
            UNIQUE(user_id, rod_id)
        )
    ''')
    
    # Create updated positions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            pond_id INTEGER,
            rod_id INTEGER,
            entry_price REAL,
            entry_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            exit_price REAL,
            exit_time DATETIME,
            pnl_percent REAL,
            fish_caught_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id),
            FOREIGN KEY (pond_id) REFERENCES ponds (id),
            FOREIGN KEY (rod_id) REFERENCES rods (id),
            FOREIGN KEY (fish_caught_id) REFERENCES fish (id)
        )
    ''')
    
    # Create fish table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fish (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create fish_images table for caching generated images
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fish_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fish_id INTEGER NOT NULL,
            rarity TEXT NOT NULL,
            image_path TEXT NOT NULL,
            cache_key TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fish_id) REFERENCES fish (id)
        )
    ''')
    
    # Add level column to existing users if it doesn't exist
    cursor.execute('''
        PRAGMA table_info(users)
    ''')
    columns = [column[1] for column in cursor.fetchall()]
    if 'level' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1')
        cursor.execute('ALTER TABLE users ADD COLUMN experience INTEGER DEFAULT 0')
    
    # Add pond_id and rod_id to existing positions table if they don't exist
    cursor.execute('''
        PRAGMA table_info(positions)
    ''')
    columns = [column[1] for column in cursor.fetchall()]
    if 'pond_id' not in columns:
        cursor.execute('ALTER TABLE positions ADD COLUMN pond_id INTEGER')
        cursor.execute('ALTER TABLE positions ADD COLUMN rod_id INTEGER')
    
    # Add fish_caught_id to existing positions table if it doesn't exist
    if 'fish_caught_id' not in columns:
        cursor.execute('ALTER TABLE positions ADD COLUMN fish_caught_id INTEGER')
    
    # Add ai_prompt column to existing fish table if it doesn't exist
    cursor.execute('PRAGMA table_info(fish)')
    fish_columns = [column[1] for column in cursor.fetchall()]
    if 'ai_prompt' not in fish_columns:
        cursor.execute('ALTER TABLE fish ADD COLUMN ai_prompt TEXT')
    
    # Insert default ponds
    _insert_default_ponds(cursor)
    # Insert default rods  
    _insert_default_rods(cursor)
    # Insert default fish
    _insert_default_fish(cursor)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def get_user(telegram_id):
    """Get user by telegram_id"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    user = cursor.fetchone()
    
    conn.close()
    return user

def create_user(telegram_id, username):
    """Create new user with default BAIT tokens and starter rod"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO users (telegram_id, username, bait_tokens, level, experience)
        VALUES (?, ?, 10, 1, 0)
    ''', (telegram_id, username))
    
    conn.commit()
    conn.close()
    
    # Give starter rod
    give_starter_rod(telegram_id)
    print(f"Created user: {username} ({telegram_id}) with starter rod")

def get_active_position(telegram_id):
    """Get user's active fishing position"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM positions 
        WHERE user_id = ? AND status = 'active'
        ORDER BY entry_time DESC LIMIT 1
    ''', (telegram_id,))
    
    position = cursor.fetchone()
    conn.close()
    return position

def create_position(telegram_id, entry_price):
    """Create new fishing position"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO positions (user_id, entry_price)
        VALUES (?, ?)
    ''', (telegram_id, entry_price))
    
    conn.commit()
    conn.close()
    print(f"Created position for user {telegram_id} at price {entry_price}")

def close_position(position_id, exit_price, pnl_percent, fish_caught_id):
    """Close fishing position and record results"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if fish_caught_id column exists
    cursor.execute('PRAGMA table_info(positions)')
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'fish_caught_id' in columns:
        cursor.execute('''
            UPDATE positions 
            SET status = 'closed', exit_price = ?, exit_time = CURRENT_TIMESTAMP,
                pnl_percent = ?, fish_caught_id = ?
            WHERE id = ?
        ''', (exit_price, pnl_percent, fish_caught_id, position_id))
    else:
        # Fallback for old schema - use fish_caught text field if fish_caught_id doesn't exist
        cursor.execute('''
            UPDATE positions 
            SET status = 'closed', exit_price = ?, exit_time = CURRENT_TIMESTAMP,
                pnl_percent = ?, fish_caught = ?
            WHERE id = ?
        ''', (exit_price, pnl_percent, str(fish_caught_id), position_id))
    
    conn.commit()
    conn.close()

def use_bait(telegram_id):
    """Use 1 BAIT token for fishing"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users 
        SET bait_tokens = bait_tokens - 1
        WHERE telegram_id = ? AND bait_tokens > 0
    ''', (telegram_id,))
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return rows_affected > 0

def _insert_default_ponds(cursor):
    """Insert default ponds if they don't exist
    
    Each pond represents a different cryptocurrency trading pair:
    - Level 1-8 progression unlocks new ponds
    - Different base currencies (ETH, BTC, SOL, etc.) vs USDT
    - Players start with access to ETH/USDT pond only
    """
    cursor.execute('SELECT COUNT(*) FROM ponds')
    if cursor.fetchone()[0] == 0:
        ponds_data = [
            # (name, trading_pair, base_currency, quote_currency, image_url, required_level, is_active)
            ('🌊 Криптовые Воды', 'ETH/USDT', 'ETH', 'USDT', None, 1, 1),     # Starter pond
            ('💰 Озеро Профита', 'BTC/USDT', 'BTC', 'USDT', None, 2, 1),       # Bitcoin
            ('⚡ Море Волатильности', 'SOL/USDT', 'SOL', 'USDT', None, 3, 1),   # Solana
            ('🌙 Лунные Пруды', 'ADA/USDT', 'ADA', 'USDT', None, 4, 1),        # Cardano
            ('🔥 Вулканические Источники', 'MATIC/USDT', 'MATIC', 'USDT', None, 5, 1), # Polygon
            ('❄️ Ледяные Глубины', 'AVAX/USDT', 'AVAX', 'USDT', None, 6, 1),   # Avalanche
            ('🌈 Радужные Заводи', 'LINK/USDT', 'LINK', 'USDT', None, 7, 1),   # Chainlink
            ('🏔️ Горные Озёра', 'DOT/USDT', 'DOT', 'USDT', None, 8, 1)        # Polkadot
        ]
        
        cursor.executemany('''
            INSERT INTO ponds (name, trading_pair, base_currency, quote_currency, image_url, required_level, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ponds_data)

def _insert_default_rods(cursor):
    """Insert default rods if they don't exist
    
    Rod progression system with increasing leverage and rarity:
    - Starter rod (1.5x) given to all new players for free
    - Higher leverage rods available for purchase with BAIT tokens
    - Rarity affects visual appearance and prestige
    - Leverage directly affects P&L multiplier in trading
    """
    cursor.execute('SELECT COUNT(*) FROM rods')
    if cursor.fetchone()[0] == 0:
        rods_data = [
            # (name, leverage, price, image_url, rarity, is_starter)
            ('🎣 Стартовая удочка', 1.5, 0, None, 'common', 1),      # Free starter
            ('🌊 Морская удочка', 2.0, 50, None, 'common', 0),       # Basic upgrade
            ('⚡ Электрическая удочка', 2.5, 100, None, 'rare', 0),   # Mid-tier
            ('🔥 Огненная удочка', 3.0, 200, None, 'rare', 0),       # Advanced
            ('💎 Алмазная удочка', 3.5, 500, None, 'epic', 0),       # High-end
            ('🌙 Лунная удочка', 4.0, 1000, None, 'epic', 0),        # Premium
            ('☀️ Солнечная удочка', 5.0, 2000, None, 'legendary', 0), # Elite
            ('🎯 Мастерская удочка', 6.0, 5000, None, 'legendary', 0) # Ultimate
        ]
        
        cursor.executemany('''
            INSERT INTO rods (name, leverage, price, image_url, rarity, is_starter)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', rods_data)

def _insert_default_fish(cursor):
    """Insert default fish if they don't exist"""
    cursor.execute('SELECT COUNT(*) FROM fish')
    if cursor.fetchone()[0] == 0:
        fish_data = [
            # (name, emoji, description, min_pnl, max_pnl, min_user_level, required_ponds, required_rods, rarity, story_template, ai_prompt)
            ('Старый Сапог', '🦐', 'Мусор со дна водоема', -100, -20, 1, '', '', 'trash', 
             'Вы чувствуете груз разочарования... {emoji} {name}... серьезно? Чей-то мусор стал вашим... тоже мусором. Тяжелый день на воде...',
             'An old waterlogged leather boot lying on the ocean floor, murky water, disappointing, low quality, dull colors'),
            
            ('Рыба-Сожаление', '🐡', 'Колючая рыба, которая приносит убытки', -20, 0, 1, '', '', 'trash',
             'Ой-ой... что-то странное на крючке... {emoji} {name} сердито раздувается! Эта рыбка вам обойдется... В следующий раз повезет больше!',
             'A spiky inflated pufferfish with sad expression, murky water, disappointing, low quality, dull colors'),
             
            ('Счастливая Плотва', '🐟', 'Маленькая, но приносящая удачу', 0, 10, 1, '', '', 'common',
             'Маленький, но счастливый улов появляется! {emoji} {name} - маленькая, но считается! Каждая рыба - хорошая рыба! Неплохо!',
             'A small shiny silver minnow fish swimming gracefully, clear water, simple, clean, natural lighting'),
             
            ('Алмазный Окунь', '🐠', 'Красивая рыба с хорошим доходом', 10, 30, 2, '', '', 'rare',
             'Красивая рыба переливается в солнечных лучах! {emoji} Потрясающий {name}! Определенно стоит сфотографировать для группы! Хороший улов!',
             'A beautiful bass fish with sparkling diamond-like fins, beautiful lighting, shimmering water, vibrant colors'),
             
            ('Акула Профита', '🦈', 'Мощный хищник, приносящий отличную прибыль', 30, 50, 3, '', '', 'epic',
             'Что-то мощное пробивается на поверхность! {emoji} Свирепая {name} во всей красе! Какая была борьба! Руки устали, но душа радуется! Отличная техника!',
             'A powerful sleek shark swimming confidently, dramatic lighting, treasure elements, dynamic pose, magical effects'),
             
            ('Легендарный Кит', '🐋', 'Мифический гигант океанских глубин', 50, 100, 5, '', '', 'legendary',
             'Вода ВЗРЫВАЕТСЯ, когда вы тянете улов... {emoji} {name} всплывает из глубин! Другие рыбаки останавливаются в восхищении! Этот улов запомнится навсегда!',
             'A massive majestic whale with golden markings, epic golden lighting, divine aura, treasure and glory, mystical atmosphere'),
             
            # Специальные рыбы для особых условий
            ('Золотой Дракон', '🐲', 'Редчайшая рыба из вулканических источников', 80, 150, 6, '5', '', 'legendary',
             'Лава бурлит, и из огненных глубин появляется... {emoji} {name}! Легенды были правдой! Вулканические духи благословили вас! НЕВЕРОЯТНО!',
             'A mythical golden dragon fish with scales like molten gold, swimming through volcanic underwater lava streams, epic golden lighting, divine aura, mystical fire effects'),
             
            ('Ледяная Принцесса', '❄️', 'Мистическое создание ледяных глубин', 60, 120, 7, '6', '', 'legendary',
             'Льдины трескаются под мощью улова... {emoji} {name} грациозно всплывает! Красота северных морей в ваших руках! Замерзшее сокровище!',
             'An elegant ice princess fish with crystalline fins and frost patterns, swimming through frozen arctic waters, epic ice-blue lighting, divine aura, mystical frozen effects'),
             
            ('Лунный Единорог', '🦄', 'Мифическое существо лунных прудов', 70, 200, 8, '4', '6,7,8', 'legendary',
             'Лунный свет сгущается в воде... {emoji} {name} материализуется из магии! Это не просто рыба, это чудо! Боги рыбалки улыбнулись вам!',
             'A mystical unicorn fish with pearl-white scales and a spiraling horn, swimming through moonlit waters with magical sparkles, epic silver-blue lighting, divine aura, celestial effects'),
             
            ('Мусорная Креветка', '🦐', 'Еще больше разочарования', -150, -50, 1, '', '1', 'trash',
             'Это даже хуже сапога... {emoji} {name} - воплощение неудачи! Может стоит сменить наживку? Или хобби...',
             'A sad tiny shrimp covered in algae and debris, floating in polluted murky water, disappointing, extremely low quality, muddy colors'),
        ]
        
        cursor.executemany('''
            INSERT INTO fish (name, emoji, description, min_pnl, max_pnl, min_user_level, required_ponds, required_rods, rarity, story_template, ai_prompt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', fish_data)

def get_available_ponds(user_level):
    """Get ponds available for user level"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM ponds 
        WHERE required_level <= ? AND is_active = 1
        ORDER BY required_level
    ''', (user_level,))
    
    ponds = cursor.fetchall()
    conn.close()
    return ponds

def get_user_rods(telegram_id):
    """Get all rods owned by user"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT r.* FROM rods r
        JOIN user_rods ur ON r.id = ur.rod_id
        WHERE ur.user_id = ?
        ORDER BY r.leverage
    ''', (telegram_id,))
    
    rods = cursor.fetchall()
    conn.close()
    return rods

def give_starter_rod(telegram_id):
    """Give starter rod to user if they don't have any"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if user already has rods
    cursor.execute('SELECT COUNT(*) FROM user_rods WHERE user_id = ?', (telegram_id,))
    has_rods = cursor.fetchone()[0] > 0
    
    if not has_rods:
        # Get starter rod ID
        cursor.execute('SELECT id FROM rods WHERE is_starter = 1 LIMIT 1')
        starter_rod = cursor.fetchone()
        
        if starter_rod:
            cursor.execute('''
                INSERT OR IGNORE INTO user_rods (user_id, rod_id)
                VALUES (?, ?)
            ''', (telegram_id, starter_rod[0]))
            print(f"Gave starter rod to user {telegram_id}")
    
    conn.commit()
    conn.close()

def ensure_user_has_level(telegram_id):
    """Ensure user has level and experience columns set"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if user has level set
    cursor.execute('SELECT level FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    
    if not result or result[0] is None:
        cursor.execute('''
            UPDATE users 
            SET level = 1, experience = 0 
            WHERE telegram_id = ?
        ''', (telegram_id,))
        print(f"Set default level for user {telegram_id}")
    
    conn.commit()
    conn.close()

def create_position_with_gear(telegram_id, pond_id, rod_id, entry_price):
    """Create new fishing position with specific pond and rod"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO positions (user_id, pond_id, rod_id, entry_price)
        VALUES (?, ?, ?, ?)
    ''', (telegram_id, pond_id, rod_id, entry_price))
    
    conn.commit()
    conn.close()
    print(f"Created position for user {telegram_id} with pond {pond_id} and rod {rod_id}")

def get_pond_by_id(pond_id):
    """Get pond by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM ponds WHERE id = ?', (pond_id,))
    pond = cursor.fetchone()
    
    conn.close()
    return pond

def get_rod_by_id(rod_id):
    """Get rod by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM rods WHERE id = ?', (rod_id,))
    rod = cursor.fetchone()
    
    conn.close()
    return rod

def get_suitable_fish_old(pnl_percent, user_level, pond_id, rod_id):
    """Legacy fish selection - kept for compatibility"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get all fish that match PnL range and user level
    cursor.execute('''
        SELECT * FROM fish 
        WHERE min_pnl <= ? AND max_pnl >= ? AND min_user_level <= ?
        ORDER BY 
            CASE 
                WHEN required_ponds = '' THEN 1 
                WHEN required_ponds LIKE '%' || ? || '%' THEN 0
                ELSE 2
            END,
            CASE 
                WHEN required_rods = '' THEN 1 
                WHEN required_rods LIKE '%' || ? || '%' THEN 0
                ELSE 2
            END,
            RANDOM()
        LIMIT 1
    ''', (pnl_percent, pnl_percent, user_level, str(pond_id), str(rod_id)))
    
    fish = cursor.fetchone()
    conn.close()
    return fish

def get_suitable_fish(pnl_percent, user_level, pond_id, rod_id):
    """Get fish that can be caught based on conditions with rarity weighting"""
    import random
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get all fish that match basic conditions (PnL range and user level)
    cursor.execute('''
        SELECT * FROM fish 
        WHERE min_pnl <= ? AND max_pnl >= ? AND min_user_level <= ?
    ''', (pnl_percent, pnl_percent, user_level))
    
    all_matching_fish = cursor.fetchall()
    conn.close()
    
    if not all_matching_fish:
        return None
    
    # Filter fish based on pond and rod requirements
    suitable_fish = []
    
    for fish in all_matching_fish:
        fish_id, name, emoji, description, min_pnl, max_pnl, min_user_level, required_ponds, required_rods, rarity, story_template, ai_prompt, created_at = fish
        
        # Check pond requirement
        pond_ok = True
        if required_ponds and required_ponds.strip():
            pond_list = [p.strip() for p in required_ponds.split(',')]
            pond_ok = str(pond_id) in pond_list
        
        # Check rod requirement  
        rod_ok = True
        if required_rods and required_rods.strip():
            rod_list = [r.strip() for r in required_rods.split(',')]
            rod_ok = str(rod_id) in rod_list
        
        if pond_ok and rod_ok:
            suitable_fish.append(fish)
    
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
        rarity = fish[9]  # rarity is at index 9
        weight = rarity_weights.get(rarity, 0.5)
        # Add fish to list multiple times based on weight (higher weight = more copies = higher chance)
        copies = max(1, int(weight * 20))  # Scale weight to reasonable number of copies
        weighted_fish.extend([fish] * copies)
    
    # Randomly select from weighted list
    selected_fish = random.choice(weighted_fish)
    return selected_fish

def get_fish_by_id(fish_id):
    """Get fish by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM fish WHERE id = ?', (fish_id,))
    fish = cursor.fetchone()
    
    conn.close()
    return fish

def get_fish_image_cache(fish_id, rarity):
    """Get cached image for fish"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT image_path FROM fish_images 
        WHERE fish_id = ? AND rarity = ?
    ''', (fish_id, rarity))
    
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_fish_image_cache(fish_id, rarity, image_path, cache_key):
    """Save generated image to cache"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO fish_images (fish_id, rarity, image_path, cache_key)
        VALUES (?, ?, ?, ?)
    ''', (fish_id, rarity, image_path, cache_key))
    
    conn.commit()
    conn.close()

def get_user_stats(telegram_id):
    """Get comprehensive user statistics"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get basic user info
    cursor.execute('''
        SELECT username, bait_tokens, level, experience, created_at
        FROM users WHERE telegram_id = ?
    ''', (telegram_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        conn.close()
        return None
    
    # Get fishing statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN status = 'closed' THEN 1 END) as completed_sessions,
            AVG(CASE WHEN status = 'closed' AND pnl_percent IS NOT NULL THEN pnl_percent END) as avg_pnl,
            MAX(CASE WHEN status = 'closed' AND pnl_percent IS NOT NULL THEN pnl_percent END) as best_pnl,
            MIN(CASE WHEN status = 'closed' AND pnl_percent IS NOT NULL THEN pnl_percent END) as worst_pnl
        FROM positions WHERE user_id = ?
    ''', (telegram_id,))
    
    fishing_stats = cursor.fetchone()
    
    # Get fish collection stats
    cursor.execute('''
        SELECT f.name, f.emoji, f.rarity, COUNT(*) as catch_count
        FROM positions p
        JOIN fish f ON p.fish_caught_id = f.id
        WHERE p.user_id = ? AND p.status = 'closed'
        GROUP BY f.id
        ORDER BY catch_count DESC, f.min_pnl DESC
    ''', (telegram_id,))
    
    fish_collection = cursor.fetchall()
    
    # Get owned rods
    cursor.execute('''
        SELECT r.name, r.leverage, r.rarity
        FROM user_rods ur
        JOIN rods r ON ur.rod_id = r.id
        WHERE ur.user_id = ?
        ORDER BY r.leverage DESC
    ''', (telegram_id,))
    
    owned_rods = cursor.fetchall()
    
    conn.close()
    
    return {
        'user': user_data,
        'fishing': fishing_stats,
        'fish_collection': fish_collection,
        'rods': owned_rods
    }

# AI Prompt Management Functions
def get_fish_ai_prompt(fish_id):
    """Get AI prompt for specific fish"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT ai_prompt FROM fish WHERE id = ?', (fish_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def update_fish_ai_prompt(fish_id, ai_prompt):
    """Update AI prompt for specific fish"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE fish SET ai_prompt = ? WHERE id = ?', (ai_prompt, fish_id))
    
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def get_all_fish_prompts():
    """Get all fish with their AI prompts for bulk management"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, emoji, rarity, ai_prompt 
        FROM fish 
        ORDER BY rarity, name
    ''')
    
    fish_prompts = cursor.fetchall()
    conn.close()
    return fish_prompts

def update_fish_prompts_bulk(prompts_data):
    """Update multiple fish prompts at once
    
    Args:
        prompts_data: List of tuples (fish_id, ai_prompt)
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.executemany('''
        UPDATE fish SET ai_prompt = ? WHERE id = ?
    ''', [(prompt, fish_id) for fish_id, prompt in prompts_data])
    
    conn.commit()
    updated_count = cursor.rowcount
    conn.close()
    return updated_count

def get_fish_by_name(fish_name):
    """Get fish by name for easier prompt management"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM fish WHERE name = ?', (fish_name,))
    fish = cursor.fetchone()
    
    conn.close()
    return fish

if __name__ == "__main__":
    init_database()
