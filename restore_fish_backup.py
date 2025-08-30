#!/usr/bin/env python3
"""
Script to restore fish database from JSON backup
"""

import sqlite3
import json
import sys
import os
from glob import glob

def connect_db():
    """Connect to the fishing bot database"""
    return sqlite3.connect('fishing_bot.db')

def list_backups():
    """List available backup files"""
    backups = glob('fish_backup_*.json')
    if not backups:
        print("❌ No backup files found")
        return None
    
    backups.sort(reverse=True)  # Most recent first
    print("📦 Available backups:")
    for i, backup in enumerate(backups, 1):
        size = os.path.getsize(backup) / 1024
        print(f"  {i}. {backup} ({size:.1f} KB)")
    
    return backups

def restore_from_backup(cursor, backup_file):
    """Restore fish data from backup file"""
    with open(backup_file, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    print(f"\n📥 Restoring {len(backup_data)} fish from {backup_file}")
    
    # Clear existing fish data
    cursor.execute("DELETE FROM fish")
    print("🗑️  Cleared existing fish data")
    
    # Restore each fish
    restored = 0
    for fish in backup_data:
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
            fish.get("story_template", f"Поймал! {fish['emoji']} {fish['name']}!"),
            fish.get("ai_prompt", "")
        ))
        restored += 1
    
    print(f"✅ Restored {restored} fish")
    return restored

def verify_restore(cursor):
    """Verify the restored database"""
    cursor.execute("SELECT COUNT(*) FROM fish")
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT rarity, COUNT(*) 
        FROM fish 
        GROUP BY rarity
    """)
    
    rarity_counts = cursor.fetchall()
    
    print("\n📊 Restored Database:")
    print(f"  Total fish: {total}")
    for rarity, count in rarity_counts:
        print(f"  {rarity.title()}: {count} fish")

def main():
    """Main restore function"""
    print("🔄 Fish Database Restore Tool")
    print("=" * 50)
    
    try:
        # List available backups
        backups = list_backups()
        if not backups:
            sys.exit(1)
        
        # Select backup
        print("\nSelect backup to restore (or 0 to cancel):")
        choice = input("Choice: ").strip()
        
        if choice == '0':
            print("❌ Restore cancelled")
            sys.exit(0)
        
        try:
            index = int(choice) - 1
            if index < 0 or index >= len(backups):
                raise ValueError
            backup_file = backups[index]
        except (ValueError, IndexError):
            print("❌ Invalid choice")
            sys.exit(1)
        
        # Confirm restore
        print(f"\n⚠️  WARNING: This will replace ALL fish data!")
        print(f"Restore from: {backup_file}")
        confirm = input("Continue? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Restore cancelled")
            sys.exit(0)
        
        # Connect and restore
        conn = connect_db()
        cursor = conn.cursor()
        
        restored = restore_from_backup(cursor, backup_file)
        conn.commit()
        
        verify_restore(cursor)
        
        print("\n🎉 Restore complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()