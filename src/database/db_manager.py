import sqlite3
import os

DATABASE_PATH = 'fishing_bot.db'

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            bait_tokens INTEGER DEFAULT 10,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create positions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            entry_price REAL,
            entry_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            exit_price REAL,
            exit_time DATETIME,
            pnl_percent REAL,
            fish_caught TEXT,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
    ''')
    
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
    """Create new user with default BAIT tokens"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO users (telegram_id, username, bait_tokens)
        VALUES (?, ?, 10)
    ''', (telegram_id, username))
    
    conn.commit()
    conn.close()
    print(f"Created user: {username} ({telegram_id})")

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

def close_position(position_id, exit_price, pnl_percent, fish_caught):
    """Close fishing position and record results"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE positions 
        SET status = 'closed', exit_price = ?, exit_time = CURRENT_TIMESTAMP,
            pnl_percent = ?, fish_caught = ?
        WHERE id = ?
    ''', (exit_price, pnl_percent, fish_caught, position_id))
    
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

if __name__ == "__main__":
    init_database()
