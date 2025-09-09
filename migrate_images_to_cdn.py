#!/usr/bin/env python3
"""
Background script to migrate existing fish images to Bunny CDN
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Dict

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from src.database.db_manager import (
    get_pool, get_fish_image_cache, save_fish_image_cache
)
from src.utils.bunny_cdn import cdn_uploader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_all_fish_with_missing_cdn() -> List[Dict]:
    """Get all fish that have local images but no CDN URL"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch('''
            SELECT DISTINCT fi.fish_id, fi.rarity, fi.image_path, fi.cache_key
            FROM fish_images fi
            WHERE fi.cdn_url IS NULL 
            AND fi.image_path IS NOT NULL
            ORDER BY fi.fish_id
        ''')
        return [dict(row) for row in result]

async def migrate_single_image(fish_info: Dict) -> bool:
    """Migrate a single fish image to CDN"""
    fish_id = fish_info['fish_id']
    rarity = fish_info['rarity']
    image_path = fish_info['image_path']
    cache_key = fish_info['cache_key']
    
    try:
        # Check if local file exists
        if not Path(image_path).exists():
            logger.warning(f"Local image not found for fish {fish_id}: {image_path}")
            return False
        
        # Read image content
        with open(image_path, 'rb') as f:
            image_content = f.read()
        
        # Upload to CDN
        cdn_url = await cdn_uploader.upload_fish_image(fish_id, rarity, image_content)
        
        if cdn_url:
            # Update database with CDN URL
            await save_fish_image_cache(fish_id, rarity, image_path, cache_key, cdn_url)
            logger.info(f"✅ Migrated fish {fish_id} ({rarity}) to CDN: {cdn_url}")
            return True
        else:
            logger.error(f"❌ Failed to upload fish {fish_id} to CDN")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error migrating fish {fish_id}: {e}")
        return False

async def migrate_all_images(batch_size: int = 10, delay: float = 1.0):
    """Migrate all fish images to CDN in batches"""
    logger.info("🚀 Starting fish image migration to Bunny CDN...")
    
    # Get all fish with missing CDN URLs
    fish_to_migrate = await get_all_fish_with_missing_cdn()
    
    if not fish_to_migrate:
        logger.info("✅ No fish images need migration - all are already on CDN!")
        return
    
    logger.info(f"📊 Found {len(fish_to_migrate)} fish images to migrate")
    
    successful = 0
    failed = 0
    
    # Process in batches
    for i in range(0, len(fish_to_migrate), batch_size):
        batch = fish_to_migrate[i:i + batch_size]
        logger.info(f"📦 Processing batch {i//batch_size + 1}/{(len(fish_to_migrate) + batch_size - 1)//batch_size}")
        
        # Process batch concurrently
        tasks = [migrate_single_image(fish) for fish in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        for result in results:
            if isinstance(result, bool) and result:
                successful += 1
            else:
                failed += 1
        
        # Add delay between batches to avoid overwhelming CDN
        if i + batch_size < len(fish_to_migrate):
            logger.info(f"⏸️  Waiting {delay}s before next batch...")
            await asyncio.sleep(delay)
    
    logger.info(f"🎉 Migration completed! ✅ {successful} successful, ❌ {failed} failed")

async def main():
    """Main migration function"""
    try:
        # Check if CDN is configured
        if not cdn_uploader.api_key:
            logger.error("❌ BUNNYCDN_API_KEY not configured - migration aborted")
            return
        
        logger.info(f"🎯 CDN Configuration:")
        logger.info(f"   Storage Zone: {cdn_uploader.storage_zone}")
        logger.info(f"   Hostname: {cdn_uploader.hostname}")
        logger.info(f"   Public URL: {cdn_uploader.public_url}")
        
        await migrate_all_images(
            batch_size=5,  # Smaller batches to be gentle with CDN
            delay=2.0      # 2 second delay between batches
        )
        
    except Exception as e:
        logger.error(f"💥 Migration failed: {e}")
        raise
    finally:
        # Clean up database connections
        pool = await get_pool()
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())