"""
Message templates and text generators for the fishing bot.
Contains all static messages, dynamic text generation functions, and story templates.
"""

def escape_markdown(text):
    """Simply return text without escaping - we'll use plain text mode"""
    return text if text else ""

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


        
def get_hook_header(username, rod_name, pond_name, pond_pair, time_fishing, entry_price, current_price, leverage, user_level=1):
    """Fixed hook header with key information"""
    safe_username = username if username else "Angler"
    stake_amount = user_level * 1000
    
    return (
        f"🎣 <b>{safe_username} IS HOOKING!</b>\n\n"
        f"Rod: {rod_name} (leverage {leverage}x, stake ${stake_amount})\n"
        f"Fishery: {pond_name} ({pond_pair})\n"
        f"Fishing time: <b>{time_fishing}</b>\n"
        f"Position: ${entry_price:.2f} → <b>${current_price:.2f}</b>"
    )

def get_hook_animated_sequence():
    """Animated sequence for hooking (only this part changes)"""
    return [
        "⚡ Hooking! Something on the line!",
        "🎣 The fight begins! Pulling carefully...",
        "🌊 Resistance! Fish doesn't want to give up!",
        "💫 Almost got it... one last effort!",
        "🐟 Something is rising from the depths!"
    ]

def format_hook_message(header, animated_text):
    """Combine header and animated text for hook message"""
    return f"{header}\n\n{animated_text}"

def get_hook_tension_message(pnl):
    """Get tension-building message before revealing catch"""
    if pnl > 20:
        return "🎣 EPIC BATTLE! The whole line is shaking! This is something HUGE! 🌊💥"
    elif pnl > 10:
        return "🐠 Strong resistance! This fish is fighting! ⚡"
    elif pnl > 0:
        return "🐟 Something decent on the hook... let's see what we caught! 🤔"
    elif pnl > -10:
        return "🌊 Feels light... maybe just seaweed? 😅"
    else:
        return "🦐 Oh no... this looks like trash... 😬"

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


def format_fishing_complete_caption(username, catch_story, rod_name, leverage, pond_name, pond_pair, time_fishing, entry_price, current_price, pnl_percent, user_level=1):
    """Format fishing complete photo caption with new structured format"""
    safe_username = username if username else "Angler"
    pnl_color = "🟢" if pnl_percent >= 0 else "🔴"
    
    # Calculate dollar P&L based on user level
    from src.utils.crypto_price import calculate_dollar_pnl
    stake_amount = user_level * 1000
    dollar_pnl = calculate_dollar_pnl(entry_price, current_price, leverage, stake_amount)
    
    # Format PnL with dynamic precision
    if abs(pnl_percent) < 0.01:
        pnl_str = f"{pnl_percent:+.4f}%"
    elif abs(pnl_percent) < 0.1:
        pnl_str = f"{pnl_percent:+.3f}%"
    elif abs(pnl_percent) < 1:
        pnl_str = f"{pnl_percent:+.2f}%"
    else:
        pnl_str = f"{pnl_percent:+.1f}%"
    
    # Format dollar amount with proper sign placement
    if abs(dollar_pnl) < 0.01:
        dollar_str = f"${abs(dollar_pnl):.4f}" if dollar_pnl < 0 else f"${dollar_pnl:.4f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    elif abs(dollar_pnl) < 1:
        dollar_str = f"${abs(dollar_pnl):.2f}" if dollar_pnl < 0 else f"${dollar_pnl:.2f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    else:
        dollar_str = f"${abs(dollar_pnl):.0f}" if dollar_pnl < 0 else f"${dollar_pnl:.0f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    
    return (
        f"This is {catch_story}\n\n"
        f"💰 <b>PnL: {dollar_str} ({pnl_str})</b>\n\n"
        f"Rod: {rod_name} (leverage {leverage}x, stake ${stake_amount})\n"
        f"Fishery: {pond_name} ({pond_pair})\n"
        f"Fishing time: <b>{time_fishing}</b>\n"
        f"Position: ${entry_price:.2f} → ${current_price:.2f}\n\n"
        f"🚀 Use /cast to start fishing!"
    )


def format_enhanced_status_message(username, pond_name, pond_pair, rod_name, leverage, entry_price, current_price, current_pnl, time_fishing, user_level=1):
    """Format enhanced status command message with precise PnL and dollar amounts"""
    safe_username = escape_markdown(username) if username else "Angler"
    pnl_color = "🟢" if current_pnl >= 0 else "🔴"
    
    # Calculate dollar P&L based on user level
    from src.utils.crypto_price import calculate_dollar_pnl
    stake_amount = user_level * 1000
    dollar_pnl = calculate_dollar_pnl(entry_price, current_price, leverage, stake_amount)
    
    # Format PnL with dynamic precision (more decimal places for small changes)
    if abs(current_pnl) < 0.01:
        pnl_str = f"{current_pnl:+.4f}%"
    elif abs(current_pnl) < 0.1:
        pnl_str = f"{current_pnl:+.3f}%"
    elif abs(current_pnl) < 1:
        pnl_str = f"{current_pnl:+.2f}%"
    else:
        pnl_str = f"{current_pnl:+.1f}%"
    
    # Format dollar amount with proper sign placement
    if abs(dollar_pnl) < 0.01:
        dollar_str = f"${abs(dollar_pnl):.4f}" if dollar_pnl < 0 else f"${dollar_pnl:.4f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    elif abs(dollar_pnl) < 1:
        dollar_str = f"${abs(dollar_pnl):.2f}" if dollar_pnl < 0 else f"${dollar_pnl:.2f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    else:
        dollar_str = f"${abs(dollar_pnl):.0f}" if dollar_pnl < 0 else f"${dollar_pnl:.0f}"
        dollar_str = f"-{dollar_str}" if dollar_pnl < 0 else f"+{dollar_str}"
    
    return (
        f"🎣 <b>Fishing status {safe_username}:</b>\n\n"
        f"Rod: {rod_name} (leverage {leverage}x, stake ${stake_amount})\n"
        f"Fishery: {pond_name} ({pond_pair})\n"
        f"⏱ Fishing time: <b>{time_fishing}</b>\n"
        f"📈 Position: ${entry_price:.2f} → <b>${current_price:.2f}</b>\n"
        f"{pnl_color} PnL: <b>{pnl_str} ({dollar_str})</b>\n\n"
        f"🪝 Use /hook to pull in your catch!"
    )

def format_no_fishing_status(username, bait_tokens, user_stats=None):
    """Format status when user is not fishing with rich statistics"""
    safe_username = escape_markdown(username) if username else "Angler"
    
    base_info = (
        f"🎣 <b>Fishing status {safe_username}:</b>\n\n"
        f"📊 Status: <i>Not fishing</i>\n"
        f"🪱 BAIT tokens: <b>{bait_tokens}</b>\n"
    )
    
    # Add user statistics if available
    if user_stats:
        stats_text = ""
        
        # Add user level and experience
        if 'user' in user_stats and user_stats['user']:
            level = user_stats['user'][2] if len(user_stats['user']) > 2 else 1
            experience = user_stats['user'][3] if len(user_stats['user']) > 3 else 0
            stats_text += f"⭐ Level: <b>{level}</b> (experience: {experience})\n"
        
        # Add fishing statistics
        if 'fishing' in user_stats and user_stats['fishing']:
            completed = user_stats['fishing'][1] or 0
            avg_pnl = user_stats['fishing'][2]
            best_pnl = user_stats['fishing'][3]
            worst_pnl = user_stats['fishing'][4]
            
            if completed > 0:
                stats_text += f"\n<b>📈 Fishing stats:</b>\n"
                stats_text += f"🎣 Total catches: <b>{completed}</b>\n"
                
                if avg_pnl is not None:
                    stats_text += f"📊 Average result: <b>{avg_pnl:+.2f}%</b>\n"
                if best_pnl is not None:
                    stats_text += f"🏆 Best catch: <b>{best_pnl:+.1f}%</b>\n"
                if worst_pnl is not None:
                    stats_text += f"💔 Worst catch: <b>{worst_pnl:+.1f}%</b>\n"
        
        # Add fish collection
        if 'fish_collection' in user_stats and user_stats['fish_collection']:
            collection = user_stats['fish_collection']
            total_fish = sum(fish[3] for fish in collection)
            unique_fish = len(collection)
            
            if total_fish > 0:
                stats_text += f"\n<b>🐟 Fish collection:</b>\n"
                stats_text += f"🎯 Total caught: <b>{total_fish}</b> fish\n"
                stats_text += f"🌈 Unique species: <b>{unique_fish}</b>\n"
                
                # Show top 3 most caught fish
                if len(collection) > 0:
                    stats_text += f"\n<b>Top-3 catches:</b>\n"
                    for i, fish in enumerate(collection[:3], 1):
                        fish_name, emoji, rarity, count = fish
                        rarity_emoji = {"trash": "🗑", "common": "⚪", "rare": "🔵", 
                                      "epic": "🟣", "legendary": "🟡"}.get(rarity, "⚫")
                        stats_text += f"{i}. {emoji} {fish_name} {rarity_emoji} × {count}\n"
        
        # Add rod collection
        if 'rods' in user_stats and user_stats['rods']:
            rods = user_stats['rods']
            stats_text += f"\n<b>🎣 Rods in inventory:</b> {len(rods)}\n"
            best_rod = max(rods, key=lambda x: x[1]) if rods else None
            if best_rod:
                stats_text += f"💪 Best rod: <b>{best_rod[0]}</b> ({best_rod[1]}x)\n"
        
        return base_info + stats_text + "\n🚀 Use /cast to start fishing!"
    
    return base_info + "\n🚀 Use /cast to start fishing!"

def format_new_user_status(username):
    """Format status for new users"""
    safe_username = escape_markdown(username) if username else "Angler"
    
    return (
        f"🎣 <b>Fishing status {safe_username}:</b>\n\n"
        f"🆕 Status: <b>New player</b>\n"
        f"🪱 BAIT tokens: <b>10</b> (starter bonus)\n\n"
        f"🚀 Use /cast to start fishing!"
    )

def get_quick_fishing_message(fishing_time_seconds):
    """Get random funny message for quick fishing attempts"""
    import random
    
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