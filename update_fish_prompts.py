#!/usr/bin/env python3
"""
Script to update all fish AI prompts with absurd, trash-style redesigns
"""

import sqlite3
import sys
from absurd_fish_data import ABSURD_FISH_DATA

def connect_db():
    """Connect to the fishing bot database"""
    return sqlite3.connect('fishing_bot.db')

def backup_current_prompts(cursor):
    """Backup current AI prompts before updating"""
    cursor.execute("SELECT name, ai_prompt FROM fish ORDER BY name")
    fish_prompts = cursor.fetchall()
    
    with open('fish_prompts_backup.txt', 'w', encoding='utf-8') as f:
        f.write("# Fish AI Prompts Backup\n\n")
        for name, prompt in fish_prompts:
            f.write(f"## {name}\n")
            f.write(f"{prompt}\n\n")
    
    print(f"✅ Backed up {len(fish_prompts)} fish prompts to fish_prompts_backup.txt")

def update_fish_prompts(cursor):
    """Update all fish AI prompts with absurd redesigns"""
    updated_count = 0
    not_found = []
    
    for fish in ABSURD_FISH_DATA:
        # Try to find the fish by name
        cursor.execute("SELECT id FROM fish WHERE name = ?", (fish["name"],))
        result = cursor.fetchone()
        
        if result:
            fish_id = result[0]
            # Update the AI prompt
            cursor.execute(
                "UPDATE fish SET ai_prompt = ? WHERE id = ?",
                (fish["ai_prompt"], fish_id)
            )
            updated_count += 1
            print(f"✅ Updated {fish['name']}")
        else:
            not_found.append(fish["name"])
            print(f"⚠️  Fish not found: {fish['name']}")
    
    return updated_count, not_found

def clear_image_cache(cursor):
    """Clear all cached fish images to force regeneration with new prompts"""
    cursor.execute("DELETE FROM fish_images")
    deleted_count = cursor.rowcount
    print(f"🗑️  Cleared {deleted_count} cached fish images")

def verify_updates(cursor):
    """Verify that all updates were applied correctly"""
    print("\n📊 Verification Report:")
    
    # Count fish by rarity
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
    
    # Show some example updated prompts
    cursor.execute("SELECT name, ai_prompt FROM fish WHERE rarity = 'trash' LIMIT 3")
    examples = cursor.fetchall()
    print(f"\n🎯 Example updated prompts:")
    for name, prompt in examples:
        print(f"  {name}: {prompt[:80]}...")

def main():
    """Main function to update fish prompts"""
    print("🎣 Updating Fish AI Prompts with Absurd Trash Style")
    print("=" * 50)
    
    try:
        # Connect to database
        conn = connect_db()
        cursor = conn.cursor()
        
        # Backup current prompts
        backup_current_prompts(cursor)
        
        # Update fish prompts
        updated_count, not_found = update_fish_prompts(cursor)
        
        # Clear image cache to force regeneration
        clear_image_cache(cursor)
        
        # Commit changes
        conn.commit()
        
        # Verify updates
        verify_updates(cursor)
        
        print(f"\n🎉 Successfully updated {updated_count} fish prompts!")
        
        if not_found:
            print(f"\n⚠️  Fish not found in database ({len(not_found)}):")
            for fish_name in not_found:
                print(f"  - {fish_name}")
        
        print("\n📝 Next steps:")
        print("  1. Test image generation with: python test_fish_cards.py")
        print("  2. Check the bot works correctly with new prompts")
        print("  3. Backup saved to: fish_prompts_backup.txt")
        
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