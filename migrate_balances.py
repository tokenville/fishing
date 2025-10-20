#!/usr/bin/env python3
"""
Migration script to convert user balances from old PnL-based calculation
to new static balance system stored in user_balances table.

Run this script ONCE after deploying the new balance system changes.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db_manager import migrate_user_balances, init_database


async def main():
    """Run balance migration"""
    print("🔄 Starting balance migration...")
    print("=" * 50)

    # Initialize database (creates user_balances table if needed)
    print("📊 Initializing database...")
    await init_database()
    print("✓ Database initialized\n")

    # Run migration
    print("💰 Migrating user balances...")
    migrated_count = await migrate_user_balances()

    print("=" * 50)
    print(f"✅ Migration complete! Migrated {migrated_count} users.")
    print("\nAll user balances have been successfully migrated to the new system.")
    print("Old balances calculated from positions + balance_bonus.")
    print("New balances stored in user_balances table.\n")


if __name__ == "__main__":
    asyncio.run(main())
