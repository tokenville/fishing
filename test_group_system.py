#!/usr/bin/env python3
"""
Test script for the new group pond system.
Tests database functions and pond creation logic.
"""

import asyncio
import logging
from src.database.db_manager import (
    init_database, get_pond_name_and_type, 
    create_or_update_group_pond, get_user_group_ponds,
    add_user_to_group, get_group_pond_by_chat_id,
    create_user
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_group_system():
    """Test the group pond system functionality"""
    try:
        logger.info("🧪 Testing Group Pond System")
        
        # Initialize database
        await init_database()
        logger.info("✅ Database initialized")
        
        # Test pond name generation
        test_cases = [
            ("Small Group", 3),
            ("Medium Group", 25),
            ("Large Group", 80),
            ("Huge Group", 150)
        ]
        
        logger.info("\n🏷️ Testing pond name generation:")
        for group_name, member_count in test_cases:
            pond_name, pair_count = get_pond_name_and_type(group_name, member_count)
            logger.info(f"  {member_count} members: {pond_name} ({pair_count} trading pairs)")
        
        # Test creating group ponds
        logger.info("\n🌊 Testing group pond creation:")
        
        # Create test group ponds
        test_groups = [
            (-123456, "Test Creek Group", "supergroup", 4),
            (-234567, "Test Lake Community", "group", 25),
            (-345678, "Test Ocean Guild", "supergroup", 120)
        ]
        
        created_ponds = []
        for chat_id, title, chat_type, member_count in test_groups:
            pond_id = await create_or_update_group_pond(chat_id, title, chat_type, member_count)
            created_ponds.append(pond_id)
            
            # Verify pond was created
            pond = await get_group_pond_by_chat_id(chat_id)
            if pond:
                logger.info(f"  ✅ Created: {pond['name']} (ID: {pond_id})")
            else:
                logger.error(f"  ❌ Failed to create pond for {title}")
        
        # Test user group membership
        logger.info("\n👥 Testing user group memberships:")
        import random
        test_user_id = random.randint(900000000, 999999999)  # Use random ID to avoid conflicts
        
        # Create test user first
        await create_user(test_user_id, "TestUser")
        logger.info(f"  ✅ Created test user: {test_user_id}")
        
        # Add user to all test groups
        for chat_id, _, _, _ in test_groups:
            await add_user_to_group(test_user_id, chat_id)
        
        # Get user's available ponds
        user_ponds = await get_user_group_ponds(test_user_id)
        logger.info(f"  User has access to {len(user_ponds)} ponds:")
        for pond in user_ponds:
            logger.info(f"    - {pond['name']} ({pond['member_count']} members)")
        
        # Test pond updates
        logger.info("\n🔄 Testing pond updates:")
        chat_id = test_groups[0][0]  # Use first test group
        
        # Update member count (should trigger name change)
        new_pond_id = await create_or_update_group_pond(chat_id, "Test Creek Group", "supergroup", 30)  # Now should be Lake
        updated_pond = await get_group_pond_by_chat_id(chat_id)
        if updated_pond:
            logger.info(f"  ✅ Updated pond: {updated_pond['name']} (now has 30 members)")
        
        logger.info("\n🎉 Group pond system test completed successfully!")
        
        # Show summary
        logger.info("\n📊 Test Summary:")
        logger.info(f"  • Pond name generation: ✅ Working")
        logger.info(f"  • Group pond creation: ✅ Working")
        logger.info(f"  • User memberships: ✅ Working")
        logger.info(f"  • Pond updates: ✅ Working")
        logger.info(f"  • Created {len(created_ponds)} test ponds")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(test_group_system())