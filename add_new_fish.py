#!/usr/bin/env python3
"""
Script to add new fish to the database (not just update existing ones)
"""

import sqlite3
import sys
from absurd_fish_data import ABSURD_FISH_DATA

def connect_db():
    """Connect to the fishing bot database"""
    return sqlite3.connect('fishing_bot.db')

def add_new_fish(cursor):
    """Add new fish that don't exist in the database yet"""
    added_count = 0
    updated_count = 0
    
    for fish in ABSURD_FISH_DATA:
        # Check if fish already exists
        cursor.execute("SELECT id FROM fish WHERE name = ?", (fish["name"],))
        result = cursor.fetchone()
        
        if result:
            # Fish exists, update it
            fish_id = result[0]
            cursor.execute("""
                UPDATE fish 
                SET emoji = ?, description = ?, min_pnl = ?, max_pnl = ?, 
                    rarity = ?, ai_prompt = ?
                WHERE id = ?
            """, (
                fish["emoji"], 
                fish["description"], 
                fish["min_pnl"], 
                fish["max_pnl"], 
                fish["rarity"], 
                fish["ai_prompt"], 
                fish_id
            ))
            updated_count += 1
            print(f"📝 Updated existing: {fish['name']}")
        else:
            # Fish doesn't exist, add it
            cursor.execute("""
                INSERT INTO fish (
                    name, emoji, description, min_pnl, max_pnl, 
                    min_user_level, required_ponds, required_rods, 
                    rarity, story_template, ai_prompt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fish["name"],
                fish["emoji"],
                fish["description"],
                fish["min_pnl"],
                fish["max_pnl"],
                fish.get("min_user_level", 0),  # Default level 0
                fish.get("required_ponds", ""),  # No specific ponds required
                fish.get("required_rods", ""),   # No specific rods required
                fish["rarity"],
                fish.get("story_template", f"Поймал! {fish['emoji']} {fish['name']}! {{pnl:+.1f}}% профита!"),
                fish["ai_prompt"]
            ))
            added_count += 1
            print(f"✅ Added new fish: {fish['name']} ({fish['emoji']})")
    
    return added_count, updated_count

def verify_database(cursor):
    """Verify the database state after adding fish"""
    print("\n📊 Database Verification:")
    
    # Count total fish
    cursor.execute("SELECT COUNT(*) FROM fish")
    total = cursor.fetchone()[0]
    print(f"Total fish in database: {total}")
    
    # Count by rarity
    cursor.execute("""
        SELECT rarity, COUNT(*) as count 
        FROM fish 
        GROUP BY rarity 
        ORDER BY 
            CASE rarity 
                WHEN 'trash' THEN 1
                WHEN 'common' THEN 2  
                WHEN 'rare' THEN 3
                WHEN 'epic' THEN 4
                WHEN 'legendary' THEN 5
            END
    """)
    
    rarity_counts = cursor.fetchall()
    for rarity, count in rarity_counts:
        print(f"  {rarity.title()}: {count} fish")
    
    # Show some of the new fish
    print("\n🆕 Sample of recently added fish:")
    cursor.execute("""
        SELECT name, emoji, min_pnl, max_pnl, rarity 
        FROM fish 
        WHERE name IN (
            'Кибер-Карась', 'Гопник Сомик', 'Апрувнутый Спам-Бот', 
            'NFT-Обезьяна', 'Скам-Лягушка'
        )
        LIMIT 5
    """)
    
    new_fish = cursor.fetchall()
    for name, emoji, min_pnl, max_pnl, rarity in new_fish:
        print(f"  {emoji} {name} ({rarity}): {min_pnl}% to {max_pnl}%")

def main():
    """Main function to add new fish to database"""
    print("🎣 Adding New Absurd Fish to Database")
    print("=" * 50)
    
    try:
        # Connect to database
        conn = connect_db()
        cursor = conn.cursor()
        
        # Add new fish and update existing ones
        added, updated = add_new_fish(cursor)
        
        # Commit changes
        conn.commit()
        
        # Verify the database
        verify_database(cursor)
        
        print(f"\n🎉 Results:")
        print(f"  • Added {added} new fish")
        print(f"  • Updated {updated} existing fish")
        print(f"  • Total fish from absurd_fish_data.py: {len(ABSURD_FISH_DATA)}")
        
        print("\n📝 Next steps:")
        print("  1. Test the bot with new fish")
        print("  2. Generate sample cards if needed")
        print("  3. Clear image cache to regenerate with new prompts")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()