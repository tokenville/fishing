#!/usr/bin/env python3
"""
Generate mock fish images for development
Creates simple colored squares with fish emojis and rarity labels
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Create mock/images directory
os.makedirs('images', exist_ok=True)

# Define rarity colors and sample fish
fish_samples = [
    {'id': 1, 'name': 'golden_dragon', 'emoji': '🐉', 'rarity': 'legendary', 'color': '#FFD700'},
    {'id': 2, 'name': 'nft_monkey', 'emoji': '🐵', 'rarity': 'rare', 'color': '#4169E1'},
    {'id': 3, 'name': 'scam_frog', 'emoji': '🐸', 'rarity': 'rare', 'color': '#4169E1'},
    {'id': 4, 'name': 'degen_mermaid', 'emoji': '🧜‍♀️', 'rarity': 'epic', 'color': '#9370DB'},
    {'id': 5, 'name': 'old_boot', 'emoji': '👢', 'rarity': 'trash', 'color': '#808080'},
    {'id': 6, 'name': 'cyber_carp', 'emoji': '🤖', 'rarity': 'common', 'color': '#90EE90'},
    {'id': 7, 'name': 'gopnik_catfish', 'emoji': '🐟', 'rarity': 'common', 'color': '#90EE90'},
    {'id': 8, 'name': 'profit_shark', 'emoji': '🦈', 'rarity': 'epic', 'color': '#9370DB'},
    {'id': 9, 'name': 'plastic_bottle', 'emoji': '🍶', 'rarity': 'trash', 'color': '#808080'},
]

# Rarity badges
rarity_colors = {
    'legendary': '#FFD700',
    'epic': '#9370DB',
    'rare': '#4169E1',
    'common': '#90EE90',
    'trash': '#808080'
}

def create_mock_fish_image(fish_data, size=400):
    """Create a simple mock fish image"""
    # Create image with gradient background
    img = Image.new('RGB', (size, size), fish_data['color'])
    draw = ImageDraw.Draw(img)
    
    # Add a simple pattern
    for i in range(0, size, 40):
        draw.line([(0, i), (size, i)], fill='white', width=1)
        draw.line([(i, 0), (i, size)], fill='white', width=1)
    
    # Add rarity label
    rarity_text = fish_data['rarity'].upper()
    text_bbox = draw.textbbox((0, 0), rarity_text)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Draw rarity badge
    badge_padding = 10
    badge_rect = [
        10, 10,
        text_width + 20 + badge_padding * 2,
        text_height + 10 + badge_padding * 2
    ]
    draw.rectangle(badge_rect, fill='black')
    draw.text((20, 15), rarity_text, fill=fish_data['color'])
    
    # Add fish ID in corner
    id_text = f"#{fish_data['id']}"
    draw.text((size - 50, size - 30), id_text, fill='white')
    
    # Add emoji representation in center (as text)
    emoji_text = fish_data['emoji']
    try:
        # Try to use a larger font if available
        font = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 100)
        draw.text((size//2 - 50, size//2 - 50), emoji_text, fill='white', font=font)
    except:
        # Fallback to default font
        draw.text((size//2 - 20, size//2 - 20), emoji_text, fill='white')
    
    return img

# Generate images
print("Generating mock fish images...")
for fish in fish_samples:
    # Generate full size
    img = create_mock_fish_image(fish, 400)
    filename = f"images/fish_{fish['id']}.png"
    img.save(filename)
    print(f"Created {filename}")
    
    # Generate thumbnail
    thumbnail = create_mock_fish_image(fish, 200)
    thumb_filename = f"images/fish_{fish['id']}_thumb.png"
    thumbnail.save(thumb_filename)
    print(f"Created {thumb_filename}")

# Create a generic fish placeholder
placeholder = Image.new('RGB', (400, 400), '#E0E0E0')
draw = ImageDraw.Draw(placeholder)
draw.text((170, 180), "🐟", fill='#808080')
draw.text((150, 250), "Loading...", fill='#808080')
placeholder.save('images/placeholder.png')
print("Created images/placeholder.png")

print(f"\n✅ Generated {len(fish_samples) * 2 + 1} mock images in mock/images/")
print("These images can be served by the mock server for development.")