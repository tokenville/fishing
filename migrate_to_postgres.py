#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL
"""
import sqlite3
import asyncio
import asyncpg
import os
from datetime import datetime

SQLITE_DB = 'fishing_bot.db'
POSTGRES_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/fishing_bot')

async def migrate():
    """Migrate all data from SQLite to PostgreSQL"""
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    pg_conn = await asyncpg.connect(POSTGRES_URL)
    
    try:
        print("Starting migration from SQLite to PostgreSQL...")
        
        # First, initialize the PostgreSQL schema
        from src.database.async_db_manager import init_database
        await init_database()
        print("✓ PostgreSQL schema initialized")
        
        # Clear existing data in PostgreSQL (in reverse order of dependencies)
        await pg_conn.execute('TRUNCATE TABLE fish_images CASCADE')
        await pg_conn.execute('TRUNCATE TABLE positions CASCADE')
        await pg_conn.execute('TRUNCATE TABLE user_rods CASCADE')
        await pg_conn.execute('TRUNCATE TABLE users CASCADE')
        await pg_conn.execute('TRUNCATE TABLE fish CASCADE')
        await pg_conn.execute('TRUNCATE TABLE rods CASCADE')
        await pg_conn.execute('TRUNCATE TABLE ponds CASCADE')
        print("✓ Cleared existing PostgreSQL data")
        
        # Migrate users
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        if users:
            user_data = [(
                row['telegram_id'],
                row['username'],
                row['bait_tokens'],
                row['level'] if row['level'] else 1,
                row['experience'] if row['experience'] else 0,
                datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
            ) for row in users]
            
            await pg_conn.executemany('''
                INSERT INTO users (telegram_id, username, bait_tokens, level, experience, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', user_data)
            print(f"✓ Migrated {len(users)} users")
        
        # Migrate ponds
        cursor.execute('SELECT * FROM ponds')
        ponds = cursor.fetchall()
        if ponds:
            # Store mapping of old IDs to new IDs
            pond_id_map = {}
            for row in ponds:
                new_id = await pg_conn.fetchval('''
                    INSERT INTO ponds (name, trading_pair, base_currency, quote_currency, 
                                     image_url, required_level, is_active, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id
                ''', row['name'], row['trading_pair'], row['base_currency'], row['quote_currency'],
                    row['image_url'], row['required_level'], bool(row['is_active']),
                    datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now())
                pond_id_map[row['id']] = new_id
            print(f"✓ Migrated {len(ponds)} ponds")
        
        # Migrate rods
        cursor.execute('SELECT * FROM rods')
        rods = cursor.fetchall()
        if rods:
            rod_id_map = {}
            for row in rods:
                new_id = await pg_conn.fetchval('''
                    INSERT INTO rods (name, leverage, price, image_url, rarity, is_starter, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                ''', row['name'], row['leverage'], row['price'], row['image_url'],
                    row['rarity'], bool(row['is_starter']),
                    datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now())
                rod_id_map[row['id']] = new_id
            print(f"✓ Migrated {len(rods)} rods")
        
        # Migrate fish
        cursor.execute('SELECT * FROM fish')
        fish = cursor.fetchall()
        if fish:
            fish_id_map = {}
            for row in fish:
                new_id = await pg_conn.fetchval('''
                    INSERT INTO fish (name, emoji, description, min_pnl, max_pnl, min_user_level,
                                    required_ponds, required_rods, rarity, story_template, ai_prompt, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    RETURNING id
                ''', row['name'], row['emoji'], row['description'], row['min_pnl'], row['max_pnl'],
                    row['min_user_level'], row['required_ponds'] or '', row['required_rods'] or '',
                    row['rarity'], row['story_template'], row['ai_prompt'],
                    datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now())
                fish_id_map[row['id']] = new_id
            print(f"✓ Migrated {len(fish)} fish")
        
        # Migrate user_rods
        cursor.execute('SELECT * FROM user_rods')
        user_rods = cursor.fetchall()
        if user_rods:
            user_rods_data = []
            for row in user_rods:
                if row['rod_id'] in rod_id_map:
                    user_rods_data.append((
                        row['user_id'],
                        rod_id_map[row['rod_id']],
                        datetime.fromisoformat(row['acquired_at']) if row['acquired_at'] else datetime.now()
                    ))
            
            if user_rods_data:
                await pg_conn.executemany('''
                    INSERT INTO user_rods (user_id, rod_id, acquired_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, rod_id) DO NOTHING
                ''', user_rods_data)
                print(f"✓ Migrated {len(user_rods_data)} user_rods")
        
        # Migrate positions
        cursor.execute('SELECT * FROM positions')
        positions = cursor.fetchall()
        if positions:
            positions_data = []
            for row in positions:
                # Map old IDs to new IDs
                pond_id = pond_id_map.get(row['pond_id']) if row['pond_id'] else None
                rod_id = rod_id_map.get(row['rod_id']) if row['rod_id'] else None
                fish_id = fish_id_map.get(row['fish_caught_id']) if row['fish_caught_id'] else None
                
                positions_data.append((
                    row['user_id'],
                    pond_id,
                    rod_id,
                    row['entry_price'],
                    datetime.fromisoformat(row['entry_time']) if row['entry_time'] else datetime.now(),
                    row['status'],
                    row['exit_price'],
                    datetime.fromisoformat(row['exit_time']) if row['exit_time'] else None,
                    row['pnl_percent'],
                    fish_id
                ))
            
            # Note: entry_time and exit_time are auto-managed in PostgreSQL, so we'll skip them
            # We'll only insert the data columns
            positions_data_simple = []
            for row in positions:
                pond_id = pond_id_map.get(row['pond_id']) if row['pond_id'] else None
                rod_id = rod_id_map.get(row['rod_id']) if row['rod_id'] else None
                fish_id = fish_id_map.get(row['fish_caught_id']) if row['fish_caught_id'] else None
                
                positions_data_simple.append((
                    row['user_id'],
                    pond_id,
                    rod_id,
                    row['entry_price'],
                    row['status'],
                    row['exit_price'],
                    row['pnl_percent'],
                    fish_id
                ))
            
            await pg_conn.executemany('''
                INSERT INTO positions (user_id, pond_id, rod_id, entry_price,
                                     status, exit_price, pnl_percent, fish_caught_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', positions_data_simple)
            print(f"✓ Migrated {len(positions)} positions")
        
        # Migrate fish_images
        cursor.execute('SELECT * FROM fish_images')
        fish_images = cursor.fetchall()
        if fish_images:
            fish_images_data = []
            for row in fish_images:
                if row['fish_id'] in fish_id_map:
                    fish_images_data.append((
                        fish_id_map[row['fish_id']],
                        row['rarity'],
                        row['image_path'],
                        row['cache_key'],
                        datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
                    ))
            
            if fish_images_data:
                await pg_conn.executemany('''
                    INSERT INTO fish_images (fish_id, rarity, image_path, cache_key, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (cache_key) DO NOTHING
                ''', fish_images_data)
                print(f"✓ Migrated {len(fish_images_data)} fish_images")
        
        print("\n✅ Migration completed successfully!")
        
        # Show summary
        user_count = await pg_conn.fetchval('SELECT COUNT(*) FROM users')
        position_count = await pg_conn.fetchval('SELECT COUNT(*) FROM positions')
        fish_count = await pg_conn.fetchval('SELECT COUNT(*) FROM fish')
        
        print(f"\nDatabase summary:")
        print(f"  Users: {user_count}")
        print(f"  Positions: {position_count}")
        print(f"  Fish types: {fish_count}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        sqlite_conn.close()
        await pg_conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())