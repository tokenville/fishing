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

    async def generate_fish_card(self, fish_name: str, pnl: float, time_fishing: str) -> bytes:
        """Generate simple fish card with AI image"""
        
        # Determine rarity for caching
        rarity = self.determine_rarity(pnl)
        
        # Check cache first
        cache_key = self.get_cache_key(fish_name, rarity)
        cached_path = self.cache_dir / f"{cache_key}.png"
        
        if cached_path.exists():
            logger.info(f"Using cached image for {fish_name}")
            with open(cached_path, 'rb') as f:
                cached_image = f.read()
        else:
            logger.info(f"Generating new image for {fish_name} ({rarity})")
            # Generate new image
            prompt = self.create_fish_prompt(fish_name, rarity)
            cached_image = await self.generate_ai_image(prompt)
            
            # Cache the generated image
            with open(cached_path, 'wb') as f:
                f.write(cached_image)
        
        # Create final card with text overlay
        return self.create_simple_card(cached_image, fish_name, pnl, time_fishing, rarity)

    def determine_rarity(self, pnl: float) -> str:
        """Determine rarity based on P&L"""
        if pnl < -10:
            return "trash"
        elif pnl < 0:
            return "trash"
        elif pnl < 20:
            return "common"
        elif pnl < 50:
            return "rare"
        elif pnl < 100:
            return "epic"
        else:
            return "legendary"

    def get_cache_key(self, fish_name: str, rarity: str) -> str:
        """Generate cache key"""
        key_string = f"{fish_name}_{rarity}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def create_fish_prompt(self, fish_name: str, rarity: str) -> str:
        """Create AI prompt for fish"""
        
        base_prompts = {
            "🦐 Soggy Boot": "An old waterlogged leather boot on the ocean floor",
            "🐡 Pufferfish of Regret": "A spiky inflated pufferfish with sad expression", 
            "🐟 Lucky Minnow": "A small shiny silver minnow fish swimming gracefully",
            "🐠 Diamond Fin Bass": "A beautiful bass fish with sparkling diamond-like fins",
            "🦈 Profit Shark": "A powerful sleek shark swimming confidently",
            "🐋 Legendary Whale": "A massive majestic whale with golden markings"
        }
        
        rarity_modifiers = {
            "trash": "murky water, disappointing, low quality",
            "common": "clear water, simple, clean", 
            "rare": "beautiful lighting, shimmering water",
            "epic": "dramatic lighting, treasure elements, dynamic",
            "legendary": "epic golden lighting, divine aura, treasure and glory"
        }
        
        base_prompt = base_prompts.get(fish_name, f"A fish representing {fish_name}")
        modifier = rarity_modifiers.get(rarity, "underwater scene")
        
        return f"{base_prompt}, {modifier}. Square format, centered composition, high quality digital art, underwater scene."

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

# Global instance
simple_generator = SimpleFishGenerator()

async def generate_fish_card_image(fish_name: str, pnl: float, time_fishing: str) -> bytes:
    """Generate simple fish card image"""
    return await simple_generator.generate_fish_card(fish_name, pnl, time_fishing)