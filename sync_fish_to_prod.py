#!/usr/bin/env python3
"""
Sync fish database with absurd_fish_data.py for PostgreSQL
- Adds new fish
- Updates existing fish
- Works with production database via DATABASE_URL
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime
from absurd_fish_data import ABSURD_FISH_DATA

async def connect_db():
    """Connect to PostgreSQL database"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)

    return await asyncpg.connect(database_url)

async def backup_database(conn):
    """Create a backup of current fish data"""
    rows = await conn.fetch("""
        SELECT name, emoji, description, min_pnl, max_pnl,
               min_user_level, required_ponds, required_rods,
               rarity, story_template, ai_prompt
        FROM fish
    """)

    backup_filename = f'fish_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

    with open(backup_filename, 'w', encoding='utf-8') as f:
        f.write(f"Backup created: {datetime.now()}\n")
        f.write(f"Total fish: {len(rows)}\n")
        f.write("=" * 80 + "\n\n")

        for row in rows:
            f.write(f"Name: {row['name']}\n")
            f.write(f"Emoji: {row['emoji']}\n")
            f.write(f"Description: {row['description']}\n")
            f.write(f"PnL Range: {row['min_pnl']}% to {row['max_pnl']}%\n")
            f.write(f"Rarity: {row['rarity']}\n")
            f.write("-" * 80 + "\n")

    print(f"✅ Backed up {len(rows)} fish to {backup_filename}")
    return backup_filename

async def sync_fish_data(conn):
    """Sync database with absurd_fish_data.py"""
    added_count = 0
    updated_count = 0

    # Get all existing fish names from database
    existing_fish_rows = await conn.fetch("SELECT name FROM fish")
    existing_fish = set(row['name'] for row in existing_fish_rows)

    # Process each fish from data file
    for fish in ABSURD_FISH_DATA:
        if fish["name"] in existing_fish:
            # Fish exists, update it
            await conn.execute("""
                UPDATE fish
                SET emoji = $1, description = $2, min_pnl = $3, max_pnl = $4,
                    rarity = $5, ai_prompt = $6, min_user_level = $7,
                    required_ponds = $8, required_rods = $9, story_template = $10
                WHERE name = $11
            """,
                fish["emoji"],
                fish["description"],
                fish["min_pnl"],
                fish["max_pnl"],
                fish["rarity"],
                fish["ai_prompt"],
                fish.get("min_user_level", 0),
                fish.get("required_ponds", ""),
                fish.get("required_rods", ""),
                fish.get("story_template", f"Caught! {fish['emoji']} {fish['name']}! {{pnl:+.1f}}% profit!"),
                fish["name"]
            )
            updated_count += 1
            print(f"📝 Updated: {fish['name']}")
        else:
            # Fish doesn't exist, add it
            await conn.execute("""
                INSERT INTO fish (
                    name, emoji, description, min_pnl, max_pnl,
                    min_user_level, required_ponds, required_rods,
                    rarity, story_template, ai_prompt
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                fish["name"],
                fish["emoji"],
                fish["description"],
                fish["min_pnl"],
                fish["max_pnl"],
                fish.get("min_user_level", 0),
                fish.get("required_ponds", ""),
                fish.get("required_rods", ""),
                fish["rarity"],
                fish.get("story_template", f"Caught! {fish['emoji']} {fish['name']}! {{pnl:+.1f}}% profit!"),
                fish["ai_prompt"]
            )
            added_count += 1
            print(f"✅ Added: {fish['name']} ({fish['emoji']})")

    return added_count, updated_count

async def verify_database(conn):
    """Verify the database state"""
    print("\n📊 Database Status:")
    print("-" * 40)

    # Count total fish
    total_row = await conn.fetchrow("SELECT COUNT(*) as count FROM fish")
    total = total_row['count']
    print(f"Total fish: {total}")

    # Count by rarity
    rarity_rows = await conn.fetch("""
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
    for row in rarity_rows:
        print(f"  {row['rarity'].title():>10}: {row['count']} fish")

    # Show PnL range coverage
    stats_row = await conn.fetchrow("""
        SELECT
            MIN(min_pnl) as lowest_pnl,
            MAX(max_pnl) as highest_pnl,
            COUNT(DISTINCT rarity) as rarity_types
        FROM fish
    """)

    print(f"\nPnL range: {stats_row['lowest_pnl']}% to {stats_row['highest_pnl']}%")
    print(f"Rarity types: {stats_row['rarity_types']}")

async def main():
    """Main function to sync fish database"""
    print("🎣 Fish Database Sync Tool (PostgreSQL)")
    print("=" * 50)
    print(f"Data source: absurd_fish_data.py ({len(ABSURD_FISH_DATA)} fish)")
    print()

    conn = None
    try:
        # Connect to database
        print("Connecting to database...")
        conn = await connect_db()
        print("✅ Connected to database")
        print()

        # Create backup
        backup_file = await backup_database(conn)
        print()

        # Sync fish data
        print("Starting sync...")
        added, updated = await sync_fish_data(conn)
        print()

        # Verify the database
        await verify_database(conn)

        # Summary
        print("\n🎉 Sync Complete!")
        print("-" * 40)
        print(f"  ✅ Added: {added} fish")
        print(f"  📝 Updated: {updated} fish")
        print(f"  📦 Backup: {backup_file}")

        print("\n💡 Next steps:")
        print("  1. Test bot to verify new fish appear")
        print("  2. Images will be generated on first catch")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            await conn.close()
            print("\n✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())
