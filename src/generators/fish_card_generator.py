import os
import hashlib
import asyncio
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import json
from typing import Tuple, Optional
import requests
import aiohttp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class SimpleFishGenerator:
    """Simple fish card generator with square images and minimal frame"""
    
    def __init__(self, cache_dir: str = "generated_fish_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    async def generate_fish_card(self, fish_data: tuple, pnl: float, time_fishing: str) -> bytes:
        """Generate simple fish card with AI image using fish database data"""
        
        # Handle both old and new fish data formats (with/without ai_prompt)
        if len(fish_data) == 12:  # Old format without ai_prompt
            fish_id, fish_name, emoji, description, min_pnl, max_pnl, min_user_level, required_ponds, required_rods, rarity, story_template, created_at = fish_data
            ai_prompt = None
        elif len(fish_data) == 13:  # New format with ai_prompt at the end
            fish_id, fish_name, emoji, description, min_pnl, max_pnl, min_user_level, required_ponds, required_rods, rarity, story_template, created_at, ai_prompt = fish_data
        else:
            # Unexpected format, use safe defaults
            fish_id = fish_data[0]
            fish_name = fish_data[1] if len(fish_data) > 1 else "Unknown Fish"
            emoji = fish_data[2] if len(fish_data) > 2 else "🐟"
            description = fish_data[3] if len(fish_data) > 3 else ""
            rarity = fish_data[9] if len(fish_data) > 9 else "common"
            ai_prompt = fish_data[12] if len(fish_data) > 12 else None
        
        # Check database cache first
        from src.database.db_manager import get_fish_image_cache, save_fish_image_cache, get_fish_ai_prompt
        
        cached_image_path = get_fish_image_cache(fish_id, rarity)
        
        if cached_image_path and Path(cached_image_path).exists():
            logger.info(f"Using database cached image for {fish_name}")
            with open(cached_image_path, 'rb') as f:
                cached_image = f.read()
        else:
            logger.info(f"Generating new image for {fish_name} ({rarity})")
            
            # Static style description for consistent quality
            style_context = (
                "Absurd and unexpected artwork, intentionally crude digital drawing, "
                "MS Paint style, flat colors, rough outlines, naive composition, "
                "awkward proportions, exaggerated features, comedic surrealism, "
                "funny and playful, intentionally low-quality, "
                "square format (1:1 aspect ratio), centered subject"
            )

            
            # Use AI prompt from database if available, otherwise generate from data
            if ai_prompt:
                prompt = f"{ai_prompt}. {style_context}"
            else:
                # Fallback to get AI prompt from database
                db_prompt = get_fish_ai_prompt(fish_id)
                if db_prompt:
                    prompt = f"{db_prompt}. {style_context}"
                else:
                    # Fallback to simple description-based prompt
                    base_prompt = description if description else f"A fish representing {fish_name}"
                    prompt = f"{base_prompt}. {style_context}"
            
            cached_image = await self.generate_ai_image(prompt)
            
            # Save to database cache
            cache_key = self.get_cache_key(fish_name, rarity)
            image_path = self.cache_dir / f"{cache_key}.png"
            
            with open(image_path, 'wb') as f:
                f.write(cached_image)
            
            save_fish_image_cache(fish_id, rarity, str(image_path), cache_key)
        
        # Create final card with text overlay
        return self.create_simple_card(cached_image, f"{emoji} {fish_name}", pnl, time_fishing, rarity)

    def get_cache_key(self, fish_name: str, rarity: str) -> str:
        """Generate cache key"""
        key_string = f"{fish_name}_{rarity}"
        return hashlib.md5(key_string.encode()).hexdigest()

    async def generate_ai_image(self, prompt: str) -> bytes:
        """Generate AI image using OpenRouter"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not api_key:
            raise Exception("OPENROUTER_API_KEY is required for image generation")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/fishing-bot",
            "X-Title": "Fishing Bot"
        }
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": "google/gemini-2.5-flash-image-preview:free",
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return await self.extract_image_from_response(data)
                else:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")

    async def extract_image_from_response(self, data: dict) -> bytes:
        """Extract image from OpenRouter response"""
        if "choices" in data and data["choices"]:
            message = data["choices"][0].get("message", {})
            
            if "images" in message and message["images"]:
                image_data = message["images"][0]
                image_url = image_data.get("image_url", {}).get("url", "")
                
                if image_url.startswith("data:image"):
                    import base64
                    base64_data = image_url.split(",")[1]
                    return base64.b64decode(base64_data)
                
                elif image_url.startswith("http"):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                return await img_response.read()
        
        raise Exception("No image found in generation response")

    def create_simple_card(self, fish_image: bytes, fish_name: str, pnl: float, time_fishing: str, rarity: str) -> bytes:
        """Create simple square card with minimal frame"""
        
        # Square card - 400x400px
        card_size = 400
        border_size = 15  # Just 3.75% border
        image_size = card_size - (border_size * 2)  # 370px image area
        
        # Create square card
        card = Image.new('RGB', (card_size, card_size), color='#1a1a1a')  # Dark background
        
        try:
            # Load and process fish image
            fish_img = Image.open(BytesIO(fish_image))
            fish_img = self.make_square_image(fish_img, image_size)
            card.paste(fish_img, (border_size, border_size))
        except Exception as e:
            logging.warning(f"Could not load fish image: {e}")
            # Simple placeholder
            draw = ImageDraw.Draw(card)
            draw.rectangle([border_size, border_size, card_size - border_size, card_size - border_size], 
                          fill='#333333', outline='#555555')
        
        # Add simple text and border
        self.add_simple_overlay(card, fish_name, pnl, time_fishing, rarity, card_size)
        
        # Convert to bytes
        buffer = BytesIO()
        card.save(buffer, format='PNG', quality=95)
        return buffer.getvalue()

    def make_square_image(self, image, target_size):
        """Convert image to square format"""
        width, height = image.size
        
        # Resize maintaining aspect ratio
        if width > height:
            new_width = target_size
            new_height = int((height * target_size) / width)
        else:
            new_height = target_size
            new_width = int((width * target_size) / height)
            
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Center on square canvas
        square_img = Image.new('RGB', (target_size, target_size), color=(20, 20, 20))
        x = (target_size - new_width) // 2
        y = (target_size - new_height) // 2
        square_img.paste(image, (x, y))
        
        return square_img

    def remove_emoji(self, text):
        """Remove emoji (first character) from text"""
        if len(text) > 0 and ord(text[0]) > 127:  # Basic emoji detection
            # Remove first character and any following space
            cleaned = text[1:].strip()
            return cleaned
        return text

    def add_simple_overlay(self, card, fish_name, pnl, time_fishing, rarity, card_size):
        """Add simple text overlay and border"""
        draw = ImageDraw.Draw(card)
        
        # Colored border based on rarity
        border_colors = {
            "trash": "#8B4513",     # Brown
            "common": "#C0C0C0",    # Silver  
            "rare": "#1E90FF",      # Blue
            "epic": "#9932CC",      # Purple
            "legendary": "#FFD700"  # Gold
        }
        
        border_color = border_colors.get(rarity, "#FFFFFF")
        draw.rectangle([0, 0, card_size-1, card_size-1], outline=border_color, width=4)
        
        # Text overlay at bottom
        overlay_height = 50
        overlay_y = card_size - overlay_height
        
        # Semi-transparent black overlay
        overlay = Image.new('RGBA', (card_size, overlay_height), (0, 0, 0, 180))
        card.paste(overlay, (0, overlay_y), overlay)
        
        # Text
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 14)
            small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
        except:
            font = small_font = ImageFont.load_default()
        
        # Fish name (remove emoji)
        clean_fish_name = self.remove_emoji(fish_name)
        draw.text((8, overlay_y + 5), clean_fish_name, fill='white', font=font)
        
        # P&L and time
        pnl_color = '#00FF88' if pnl >= 0 else '#FF4444'
        pnl_text = f"+${pnl:.1f}" if pnl >= 0 else f"${pnl:.1f}"
        draw.text((8, overlay_y + 25), f"{pnl_text} • {time_fishing}", fill=pnl_color, font=small_font)

class FishPromptManager:
    """Manager for fish AI prompts with convenient methods"""
    
    def __init__(self):
        pass
    
    def list_all_prompts(self):
        """List all fish with their current AI prompts"""
        from src.database.db_manager import get_all_fish_prompts
        return get_all_fish_prompts()
    
    def get_prompt(self, fish_name: str):
        """Get AI prompt for fish by name"""
        from src.database.db_manager import get_fish_by_name, get_fish_ai_prompt
        fish = get_fish_by_name(fish_name)
        if fish:
            return get_fish_ai_prompt(fish[0])  # fish[0] is ID
        return None
    
    def update_prompt(self, fish_name: str, new_prompt: str) -> bool:
        """Update AI prompt for fish by name"""
        from src.database.db_manager import get_fish_by_name, update_fish_ai_prompt
        fish = get_fish_by_name(fish_name)
        if fish:
            return update_fish_ai_prompt(fish[0], new_prompt)  # fish[0] is ID
        return False
    
    def update_prompt_by_id(self, fish_id: int, new_prompt: str) -> bool:
        """Update AI prompt for fish by ID"""
        from src.database.db_manager import update_fish_ai_prompt
        return update_fish_ai_prompt(fish_id, new_prompt)
    
    def bulk_update_prompts(self, prompts_dict: dict) -> int:
        """Update multiple prompts at once
        
        Args:
            prompts_dict: Dictionary {fish_name: new_prompt}
        
        Returns:
            Number of prompts updated
        """
        from src.database.db_manager import get_fish_by_name, update_fish_prompts_bulk
        
        prompts_data = []
        for fish_name, prompt in prompts_dict.items():
            fish = get_fish_by_name(fish_name)
            if fish:
                prompts_data.append((fish[0], prompt))  # (fish_id, prompt)
        
        if prompts_data:
            return update_fish_prompts_bulk(prompts_data)
        return 0
    
    def generate_default_prompt(self, fish_name: str) -> str:
        """Generate a default AI prompt for a fish"""
        from src.database.db_manager import get_fish_by_name
        
        fish = get_fish_by_name(fish_name)
        if fish:
            _, name, _, description, _, _, _, _, _, rarity_db, _ = fish[:11]
            
            base_prompt = description if description else f"A fish representing {name}"
            return f"{base_prompt}. Square format, centered composition, high quality digital art, underwater scene."
        
        return f"A fish representing {fish_name}, underwater scene, high quality digital art."
    
    def clear_image_cache(self, fish_name: str = None):
        """Clear cached images to force regeneration with new prompts"""
        if fish_name:
            # Clear cache for specific fish
            from src.database.db_manager import get_fish_by_name
            fish = get_fish_by_name(fish_name)
            if fish:
                fish_id = fish[0]
                # Remove cached images from filesystem and database
                import sqlite3
                from pathlib import Path
                
                conn = sqlite3.connect('fishing_bot.db')
                cursor = conn.cursor()
                
                cursor.execute('SELECT image_path FROM fish_images WHERE fish_id = ?', (fish_id,))
                cached_paths = cursor.fetchall()
                
                for path_tuple in cached_paths:
                    try:
                        Path(path_tuple[0]).unlink(missing_ok=True)
                    except:
                        pass
                
                cursor.execute('DELETE FROM fish_images WHERE fish_id = ?', (fish_id,))
                conn.commit()
                conn.close()
        else:
            # Clear all cached images
            import sqlite3
            from pathlib import Path
            
            conn = sqlite3.connect('fishing_bot.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT image_path FROM fish_images')
            cached_paths = cursor.fetchall()
            
            for path_tuple in cached_paths:
                try:
                    Path(path_tuple[0]).unlink(missing_ok=True)
                except:
                    pass
            
            cursor.execute('DELETE FROM fish_images')
            conn.commit()
            conn.close()

# Global instances
simple_generator = SimpleFishGenerator()
prompt_manager = FishPromptManager()

async def generate_fish_card_from_db(fish_data: tuple, pnl: float, time_fishing: str) -> bytes:
    """Generate fish card image from database fish data"""
    return await simple_generator.generate_fish_card(fish_data, pnl, time_fishing)

