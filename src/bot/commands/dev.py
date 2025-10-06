"""
Development commands (testing, debugging)
"""

import random
import logging
from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from src.database.db_manager import get_suitable_fish
from src.bot.utils.telegram_utils import safe_reply
from src.generators.fish_card_generator import generate_fish_card_from_db

logger = logging.getLogger(__name__)


async def test_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /test_card command - for development only"""
    try:
        # Check if it's development mode (you can add your own check here)
        if update.effective_user.id not in [6919477427]:  # Replace with your dev user IDs
            await safe_reply(update, "🎣 This command is only available to developers!")
            return

        username = update.effective_user.username or update.effective_user.first_name
        await safe_reply(update, "🎨 Generating test card...")

        # Generate test card with random fish
        pnl = random.uniform(-50, 100)

        # Get a random fish
        fish_data = await get_suitable_fish(pnl, 1, 9, 9)  # Use real IDs

        if fish_data:
            card_image = await generate_fish_card_from_db(fish_data)

            if card_image:
                await update.message.reply_photo(
                    photo=BytesIO(card_image),
                    caption=f"🎣 Test card: {fish_data['emoji']} {fish_data['name']}"
                )
            else:
                await safe_reply(update, "🎣 Failed to generate image")
        else:
            await safe_reply(update, "🎣 Failed to find suitable fish")

    except Exception as e:
        logger.error(f"Error in test_card command: {e}")
        await safe_reply(update, f"🎣 Generation error: {str(e)}")
