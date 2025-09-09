"""
BunnyCDN integration for uploading and managing fish images
"""

import os
import aiohttp
import hashlib
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class BunnyCDNUploader:
    """Upload and manage images on BunnyCDN"""
    
    def __init__(self):
        self.storage_zone = os.getenv("BUNNYCDN_STORAGE_ZONE", "miniapps")
        self.api_key = os.getenv("BUNNYCDN_API_KEY")
        self.hostname = os.getenv("BUNNYCDN_HOSTNAME", "se.storage.bunnycdn.com")
        self.public_url = os.getenv("BUNNYCDN_PUBLIC_URL", "https://miniapps.b-cdn.net")
        
        if not self.api_key:
            logger.warning("BUNNYCDN_API_KEY not set - CDN uploads will be disabled")
    
    async def upload_image(self, image_data: bytes, filename: str, folder: str = "fish") -> Optional[str]:
        """
        Upload image to BunnyCDN and return public URL
        
        Args:
            image_data: Image bytes to upload
            filename: Name for the file (e.g., "fish_123_legendary.png")
            folder: Folder in storage zone (default: "fish")
            
        Returns:
            Public CDN URL or None if upload fails
        """
        if not self.api_key:
            logger.warning("CDN upload skipped - no API key")
            return None
        
        try:
            # Construct upload URL
            upload_path = f"{folder}/{filename}"
            upload_url = f"https://{self.hostname}/{self.storage_zone}/{upload_path}"
            
            headers = {
                "AccessKey": self.api_key,
                "Content-Type": "application/octet-stream"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(upload_url, data=image_data, headers=headers) as response:
                    if response.status in [200, 201]:
                        # Return public CDN URL
                        public_url = f"{self.public_url}/{upload_path}"
                        logger.info(f"Successfully uploaded to CDN: {public_url}")
                        return public_url
                    else:
                        error_text = await response.text()
                        logger.error(f"CDN upload failed ({response.status}): {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"CDN upload error: {e}")
            return None
    
    async def upload_fish_image(self, fish_id: int, rarity: str, image_data: bytes) -> Optional[str]:
        """
        Upload fish image with standardized naming
        
        Args:
            fish_id: Fish ID from database
            rarity: Fish rarity (for caching)
            image_data: Image bytes
            
        Returns:
            Public CDN URL or None if upload fails
        """
        # Generate unique filename based on fish_id and content hash
        content_hash = hashlib.md5(image_data).hexdigest()[:8]
        filename = f"fish_{fish_id}_{rarity}_{content_hash}.png"
        
        return await self.upload_image(image_data, filename, folder="fish")
    
    def get_optimized_url(self, cdn_url: str, width: Optional[int] = None, height: Optional[int] = None, quality: int = 85) -> str:
        """
        Get optimized image URL using Bunny CDN optimizer
        
        Args:
            cdn_url: Original CDN URL
            width: Target width (optional)
            height: Target height (optional)
            quality: JPEG quality (1-100, default 85)
            
        Returns:
            Optimized image URL
        """
        if not cdn_url or not cdn_url.startswith(self.public_url):
            return cdn_url
        
        # Build optimization parameters
        params = []
        if width:
            params.append(f"width={width}")
        if height:
            params.append(f"height={height}")
        params.append(f"quality={quality}")
        
        # Add optimization parameters to URL
        separator = "&" if "?" in cdn_url else "?"
        optimized_url = f"{cdn_url}{separator}{'&'.join(params)}"
        
        return optimized_url
    
    def get_thumbnail_url(self, cdn_url: str, size: int = 200) -> str:
        """
        Get thumbnail URL for fish grid display
        
        Args:
            cdn_url: Original CDN URL
            size: Thumbnail size (default 200px)
            
        Returns:
            Thumbnail URL
        """
        return self.get_optimized_url(cdn_url, width=size, height=size, quality=80)
    
    def get_full_image_url(self, cdn_url: str, max_width: int = 800) -> str:
        """
        Get full image URL for detailed view
        
        Args:
            cdn_url: Original CDN URL
            max_width: Maximum width (default 800px)
            
        Returns:
            Full image URL
        """
        return self.get_optimized_url(cdn_url, width=max_width, quality=90)

# Global instance
cdn_uploader = BunnyCDNUploader()