"""
Message templates and text generators for the fishing bot.
Contains all static messages and dynamic text generation functions.
"""

import random


def get_cast_header(username, rod_name, pond_name, pond_pair, entry_price, leverage, user_level=1):
    """Fixed casting header with key information"""
    safe_username = username if username else "Angler"
    stake_amount = user_level * 1000

    return (
        f"🎣 <b>{safe_username}</b> is casting:\n\n"
        f"Rod: {rod_name} (leverage {leverage}x, stake ${stake_amount})\n"
        f"Fishery: {pond_name} ({pond_pair})\n"
        f"📈 Entry position: <b>${entry_price:.2f}</b>"
    )


def get_cast_animated_sequence():
    """Animated sequence for casting (only this part changes)"""
    return [
        "💫 Swing! The rod flies through the air!",
        "💦 SPLASH! Perfect hit!",
        "🪱 Bait slowly sinking...",
        "🐟 Fish are getting interested in the bait!",
        "✨ Hook with /hook when you're ready..."
    ]


def format_cast_message(header, animated_text):
    """Combine header and animated text for casting message"""
    return f"{header}\n\n{animated_text}"


def get_hook_animated_sequence():
    """Animated sequence for hooking (only this part changes)"""
    return [
        "⚡ Hooking! Something on the line!",
        "🎣 The fight begins! Pulling carefully...",
        "🌊 Resistance! Fish doesn't want to give up!",
        "💫 Almost got it... one last effort!",
        "🐟 Something is rising from the depths!"
    ]


def get_catch_story_from_db(fish_data):
    """Get simple catch story from database fish data"""
    if not fish_data:
        return "🎣 You caught something!"

    # Handle both dict-like objects (asyncpg Record) and tuples (sqlite)
    if hasattr(fish_data, 'get'):
        # asyncpg Record access
        fish_name = fish_data.get('name', 'Unknown fish')
        emoji = fish_data.get('emoji', '🐟')
        description = fish_data.get('description', '')
    elif hasattr(fish_data, '__getitem__'):
        try:
            # Dictionary or tuple access
            fish_name = fish_data['name'] if 'name' in fish_data else fish_data[1]
            emoji = fish_data['emoji'] if 'emoji' in fish_data else fish_data[2]
            description = fish_data['description'] if 'description' in fish_data else (fish_data[3] if len(fish_data) > 3 else '')
        except (IndexError, KeyError, TypeError):
            fish_name = "Unknown fish"
            emoji = "🐟"
            description = ""
    else:
        fish_name = "Unknown fish"
        emoji = "🐟"
        description = ""

    return f"<b>{fish_name}</b>. {description}. {emoji}"


def get_quick_fishing_message(fishing_time_seconds):
    """Get random funny message for quick fishing attempts"""
    messages = [
        f"⚡ At this speed you'll only catch dust from the screen! 💨",
        f"⏰ The fish haven't even noticed your bait yet! Patience, friend!",
        f"🏃‍♂️ Even Flash doesn't catch fish in {fishing_time_seconds} seconds! Slow down a bit ⚡",
        f"🐌 Don't rush! Good fish takes time, like good wine 🍷",
        f"⚡ Faster than lightning! But fish don't like speedsters 🐟",
        f"🎯 At this speed you can only play Call of Duty, not fish!",
        f"⏳ Time is money, but in fishing time is FISH! Give it time!",
        f"🚗 Slow down, racer! This is fishing, not Formula-1 🏎️",
        f"🕐 Even a microwave heats longer than {fishing_time_seconds} seconds!",
        f"⚡ Teleportation doesn't work in fishing! Need patience like a real angler 🎣"
    ]

    return random.choice(messages)


def get_inheritance_welcome_message(username: str) -> str:
    """Get welcome message for users who haven't claimed their inheritance yet"""
    return f"""<b>📜 Welcome, {username}!</b>

You have received a mysterious letter...

🏴‍☠️ <i>From your grandfather, the legendary crypto anarchist</i>

Open the app to learn about your inheritance!"""


async def get_help_text():
    """Get dynamic help command text from database"""
    from src.database.db_manager import get_pool

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get fish statistics
            fish_data = await conn.fetch('''
                SELECT emoji, name, rarity, description, min_pnl, max_pnl, required_ponds, required_rods
                FROM fish
                ORDER BY min_pnl DESC
            ''')

            # Get ponds count and info
            ponds_count = await conn.fetchval('SELECT COUNT(*) FROM ponds WHERE is_active = true')

            ponds_data = await conn.fetch('''
                SELECT name, trading_pair, required_level
                FROM ponds
                WHERE is_active = true
                ORDER BY required_level
            ''')

            # Get rods count and leverage range
            rods_count = await conn.fetchval('SELECT COUNT(*) FROM rods')

            leverage_range = await conn.fetchrow('SELECT MIN(leverage), MAX(leverage) FROM rods')

            # Get starter bait amount (from user creation)
            starter_bait = await conn.fetchrow('SELECT bait_tokens FROM users WHERE bait_tokens = 10 LIMIT 1')
            starter_bait_amount = starter_bait['bait_tokens'] if starter_bait else 10

        # Build dynamic help text
        help_text = """🎣 <b>FISHING BOT COMMANDS:</b>

/cast - Cast your rod (cost: 1 🪱 BAIT)
/hook - Pull in your catch and see what you caught!
/status - Check current fishing status
/help - Show this message

<b>🎮 HOW TO PLAY:</b>
1. Use /cast to start fishing
2. Wait and watch the casting animation
3. Use /status to check progress
4. Use /hook when ready to complete position
5. Get a fish card based on your result!

<b>🐟 FISH TYPES:</b>"""

        # Group fish by rarity
        rarity_groups = {
            'trash': [],
            'common': [],
            'rare': [],
            'epic': [],
            'legendary': []
        }

        special_fish = []

        for fish in fish_data:
            emoji = fish['emoji']
            name = fish['name']
            rarity = fish['rarity']
            min_pnl = fish['min_pnl']
            max_pnl = fish['max_pnl']
            required_ponds = fish['required_ponds']
            required_rods = fish['required_rods']

            # Check if it's a special fish (has requirements)
            if required_ponds or required_rods:
                special_fish.append(fish)
            else:
                # Regular fish grouped by rarity
                if rarity in rarity_groups:
                    rarity_groups[rarity].append(fish)

        # Add regular fish by rarity
        rarity_names = {
            'trash': 'Trash',
            'common': 'Common',
            'rare': 'Rare',
            'epic': 'Epic',
            'legendary': 'Legendary'
        }

        for rarity in ['legendary', 'epic', 'rare', 'common', 'trash']:
            for fish in rarity_groups[rarity]:
                emoji = fish['emoji']
                name = fish['name']
                min_pnl = fish['min_pnl']
                max_pnl = fish['max_pnl']
                pnl_desc = f"({min_pnl:+.0f}% to {max_pnl:+.0f}%)" if min_pnl != max_pnl else f"({min_pnl:+.0f}%)"
                help_text += f"\n{emoji} {name} {pnl_desc} - {rarity_names[rarity]}"

        # Add special fish section if any exist
        if special_fish:
            help_text += "\n\n<b>🌟 SPECIAL FISH:</b>"
            for fish in special_fish:
                emoji = fish['emoji']
                name = fish['name']
                required_ponds = fish['required_ponds']
                required_rods = fish['required_rods']

                # Build requirement description
                requirements = []
                if required_ponds:
                    # Get pond names for requirements
                    pond_ids = required_ponds.split(',')
                    pond_names = []
                    for i, pond_data in enumerate(ponds_data):
                        if str(i + 1) in pond_ids:
                            pond_names.append(pond_data['name'])
                    if pond_names:
                        requirements.append(f"only {'/'.join(pond_names)}")

                if required_rods:
                    requirements.append("premium rods")

                req_text = ", ".join(requirements) if requirements else "special conditions"
                help_text += f"\n{emoji} {name} - {req_text}"

        # Add dynamic system info
        help_text += f"\n\n<b>⚙️ SYSTEM:</b>"
        help_text += f"\n• {rods_count} rod types with leverage {leverage_range['min']}x to {leverage_range['max']}x"
        help_text += f"\n• {ponds_count} trading ponds with different crypto pairs:"

        for pond in ponds_data[:4]:  # Show first 4 ponds
            help_text += f"\n  └ {pond['name']} ({pond['trading_pair']}) - level {pond['required_level']}+"

        if ponds_count > 4:
            help_text += f"\n  └ ... and {ponds_count - 4} more"

        help_text += f"\n• Level system to unlock new locations"
        help_text += f"\n• New players get {starter_bait_amount} 🪱 BAIT tokens"
        help_text += f"\n• Works in group and private chats!"

        return help_text

    except Exception:
        # Fallback to static text if database fails
        return """🎣 <b>FISHING BOT COMMANDS:</b>

/cast - Cast your rod (cost: 1 🪱 BAIT)
/hook - Pull in your catch and see what you caught!
/status - Check current fishing status
/help - Show this message

<i>⚠️ Fishing system temporarily unavailable for display.</i>
🚀 Try /cast to start playing!"""
