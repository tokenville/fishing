#!/usr/bin/env python3
"""
Test script to verify absurd fish prompt updates
"""

import sqlite3
import sys
import os

def test_database_connection():
    """Test if we can connect to the database"""
    if not os.path.exists('fishing_bot.db'):
        print("❌ Database file 'fishing_bot.db' not found!")
        return False
    
    try:
        conn = sqlite3.connect('fishing_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fish")
        count = cursor.fetchone()[0]
        print(f"✅ Database connected. Found {count} fish.")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_fish_prompts():
    """Test that fish prompts contain absurd elements"""
    conn = sqlite3.connect('fishing_bot.db')
    cursor = conn.cursor()
    
    # Get some example prompts
    cursor.execute("""
        SELECT name, ai_prompt, rarity 
        FROM fish 
        WHERE rarity IN ('trash', 'common', 'legendary')
        ORDER BY name
        LIMIT 10
    """)
    
    fish_samples = cursor.fetchall()
    
    print("\n🎯 Sample Fish Prompts (checking for absurd elements):")
    print("-" * 60)
    
    absurd_keywords = ['wearing', 'holding', 'costume', 'sunglasses', 'hat', 'ridiculous', 
                       'confused', 'guilty', 'embarrassed', 'craft store', 'fake', 'plastic']
    
    for name, prompt, rarity in fish_samples:
        has_absurd = any(keyword in prompt.lower() for keyword in absurd_keywords)
        status = "✅" if has_absurd else "⚠️"
        
        print(f"{status} {name} ({rarity}):")
        print(f"   {prompt[:100]}...")
        if not has_absurd:
            print("   ^ Missing absurd elements!")
        print()
    
    conn.close()

def test_rarity_distribution():
    """Test that we have good distribution across rarities"""
    conn = sqlite3.connect('fishing_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT rarity, COUNT(*) as count,
               GROUP_CONCAT(name, ', ') as examples
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
    
    print("🎪 Fish Distribution by Rarity:")
    print("-" * 40)
    
    total_fish = 0
    for rarity, count, examples in cursor.fetchall():
        total_fish += count
        example_list = examples.split(', ')[:3]  # Show first 3 examples
        examples_str = ', '.join(example_list)
        if len(example_list) < count:
            examples_str += f" (and {count - len(example_list)} more)"
            
        print(f"{rarity.upper():>10}: {count:>2} fish - {examples_str}")
    
    print(f"{'TOTAL':>10}: {total_fish:>2} fish")
    conn.close()

def main():
    """Run all tests"""
    print("🧪 Testing Absurd Fish Database Updates")
    print("=" * 40)
    
    # Test database connection
    if not test_database_connection():
        sys.exit(1)
    
    # Test fish prompts
    test_fish_prompts()
    
    # Test rarity distribution  
    test_rarity_distribution()
    
    print("\n🎉 Testing completed!")
    print("💡 Run the update script with: python update_fish_prompts.py")

if __name__ == "__main__":
    main()