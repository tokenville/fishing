#!/usr/bin/env python3
"""
Universal script to sync fish database with absurd_fish_data.py
- Adds new fish
- Updates existing fish
- Removes fish not in data file
- Backs up before changes
"""

import sqlite3
import sys
import json
from datetime import datetime
from absurd_fish_data import ABSURD_FISH_DATA

def connect_db():
    """Connect to the fishing bot database"""
    return sqlite3.connect('fishing_bot.db')

def backup_database(cursor):
    """Create a backup of current fish data"""
    cursor.execute("""
        SELECT name, emoji, description, min_pnl, max_pnl, 
               min_user_level, required_ponds, required_rods, 
               rarity, story_template, ai_prompt 
        FROM fish
    """)
    
    fish_data = cursor.fetchall()
    backup_filename = f'fish_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    backup = []
    for row in fish_data:
        backup.append({
            "name": row[0],
            "emoji": row[1],
            "description": row[2],
            "min_pnl": row[3],
            "max_pnl": row[4],
            "min_user_level": row[5],
            "required_ponds": row[6],
            "required_rods": row[7],
            "rarity": row[8],
            "story_template": row[9],
            "ai_prompt": row[10]
        })
    
    with open(backup_filename, 'w', encoding='utf-8') as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Backed up {len(backup)} fish to {backup_filename}")
    return backup_filename

def sync_fish_data(cursor):
    """Sync database with absurd_fish_data.py"""
    added_count = 0
    updated_count = 0
    removed_count = 0
    
    # Get all existing fish names from database
    cursor.execute("SELECT name FROM fish")
    existing_fish = set(row[0] for row in cursor.fetchall())
    
    # Track fish names from data file
    data_fish_names = set()
    
    # Process each fish from data file
    for fish in ABSURD_FISH_DATA:
        data_fish_names.add(fish["name"])
        
        # Check if fish already exists
        cursor.execute("SELECT id FROM fish WHERE name = ?", (fish["name"],))
        result = cursor.fetchone()
        
        if result:
            # Fish exists, update it
            fish_id = result[0]
            cursor.execute("""
                UPDATE fish 
                SET emoji = ?, description = ?, min_pnl = ?, max_pnl = ?, 
                    rarity = ?, ai_prompt = ?, min_user_level = ?,
                    required_ponds = ?, required_rods = ?, story_template = ?
                WHERE id = ?
            """, (
                fish["emoji"], 
                fish["description"], 
                fish["min_pnl"], 
                fish["max_pnl"], 
                fish["rarity"], 
                fish["ai_prompt"],
                fish.get("min_user_level", 0),
                fish.get("required_ponds", ""),
                fish.get("required_rods", ""),
                fish.get("story_template", f"Поймал! {fish['emoji']} {fish['name']}! {{pnl:+.1f}}% профита!"),
                fish_id
            ))
            updated_count += 1
            print(f"📝 Updated: {fish['name']}")
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
                fish.get("min_user_level", 0),
                fish.get("required_ponds", ""),
                fish.get("required_rods", ""),
                fish["rarity"],
                fish.get("story_template", f"Поймал! {fish['emoji']} {fish['name']}! {{pnl:+.1f}}% профита!"),
                fish["ai_prompt"]
            ))
            added_count += 1
            print(f"✅ Added: {fish['name']} ({fish['emoji']})")
    
    # Find and optionally remove fish not in data file
    orphaned_fish = existing_fish - data_fish_names
    if orphaned_fish:
        print(f"\n⚠️  Found {len(orphaned_fish)} fish in database but not in data file:")
        for name in orphaned_fish:
            print(f"   - {name}")
        
        response = input("\nRemove these fish from database? (y/N): ").strip().lower()
        if response == 'y':
            for name in orphaned_fish:
                cursor.execute("DELETE FROM fish WHERE name = ?", (name,))
                removed_count += 1
                print(f"🗑️  Removed: {name}")
    
    return added_count, updated_count, removed_count

def clear_image_cache(cursor):
    """Clear all cached fish images"""
    cursor.execute("DELETE FROM fish_images")
    deleted_count = cursor.rowcount
    if deleted_count > 0:
        print(f"🗑️  Cleared {deleted_count} cached fish images")
    return deleted_count

def verify_database(cursor):
    """Verify the database state"""
    print("\n📊 Database Status:")
    print("-" * 40)
    
    # Count total fish
    cursor.execute("SELECT COUNT(*) FROM fish")
    total = cursor.fetchone()[0]
    print(f"Total fish: {total}")
    
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
    
    print("\nBy rarity:")
    rarity_counts = cursor.fetchall()
    for rarity, count in rarity_counts:
        print(f"  {rarity.title():>10}: {count} fish")
    
    # Show PnL range coverage
    cursor.execute("""
        SELECT 
            MIN(min_pnl) as lowest_pnl,
            MAX(max_pnl) as highest_pnl,
            COUNT(DISTINCT rarity) as rarity_types
        FROM fish
    """)
    
    stats = cursor.fetchone()
    print(f"\nPnL range: {stats[0]}% to {stats[1]}%")
    print(f"Rarity types: {stats[2]}")

def main():
    """Main function to sync fish database"""
    print("🎣 Fish Database Sync Tool")
    print("=" * 50)
    print(f"Data source: absurd_fish_data.py ({len(ABSURD_FISH_DATA)} fish)")
    print()
    
    try:
        # Connect to database
        conn = connect_db()
        cursor = conn.cursor()
        
        # Create backup
        backup_file = backup_database(cursor)
        print()
        
        # Sync fish data
        added, updated, removed = sync_fish_data(cursor)
        
        # Clear image cache
        print()
        clear_response = input("Clear image cache to force regeneration? (Y/n): ").strip().lower()
        if clear_response != 'n':
            clear_image_cache(cursor)
        
        # Commit changes
        conn.commit()
        
        # Verify the database
        verify_database(cursor)
        
        # Summary
        print("\n🎉 Sync Complete!")
        print("-" * 40)
        print(f"  ✅ Added: {added} fish")
        print(f"  📝 Updated: {updated} fish")
        print(f"  🗑️  Removed: {removed} fish")
        print(f"  📦 Backup: {backup_file}")
        
        print("\n💡 Next steps:")
        print("  1. Test bot with: python3 main.py")
        print("  2. Generate test cards: python3 test_fish_cards.py")
        print("  3. Restore backup if needed: restore_fish_backup.py")
        
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