"""
Message templates and text generators for the fishing bot.
Contains all static messages, dynamic text generation functions, and story templates.
"""

def get_simple_cast_messages():
    """Simple casting messages with emojis"""
    return [
        "🎣 Getting ready to cast...",
        "💫 Whoosh! Line flies through the air!",
        "💦 *SPLASH!* Perfect landing!",
        "🌊 Bait sinks into the depths..."
    ]

def get_waiting_messages():
    """Progressive waiting messages"""
    return [
        "🌊 Line in the water... waiting for a bite",
        "🐟 Something moves in the depths...", 
        "📍 The float bobs gently on the waves",
        "🐠 Fish are getting curious about your bait",
        "⚡ Energy builds in the water...",
        "🔮 We can only wait and see what happens..."
    ]

def get_status_description(pnl, time_fishing):
    """Get dynamic status based on P&L and time"""
    if pnl > 15:
        return f"🦈 MASSIVE FISH SPOTTED! Something huge is fighting! ({time_fishing})"
    elif pnl > 5:
        return f"🐠 Good catch on the line! Fish is struggling! ({time_fishing})"
    elif pnl > -5:
        return f"🐟 Small fish nibbling... be patient ({time_fishing})"
    elif pnl > -15:
        return f"🌊 Fish diving deep, taking you down... ({time_fishing})"
    else:
        return f"🦐 Feels like an old boot... or worse ({time_fishing})"
        
def get_hook_tension_message(pnl):
    """Get tension-building message before revealing catch"""
    if pnl > 20:
        return "🎣 EPIC BATTLE! The whole line is shaking! This is HUGE! 🌊💥"
    elif pnl > 10:
        return "🐠 Strong resistance! This fish has some fight in it! ⚡"
    elif pnl > 0:
        return "🐟 Something decent on the hook... let's see what we got! 🤔"
    elif pnl > -10:
        return "🌊 Feels light... maybe just seaweed? 😅"
    else:
        return "🦐 Oh no... this feels like junk... 😬"

def get_catch_story(fish_name, pnl, time_fishing):
    """Get dramatic catch reveal story"""
    stories = {
        "🐋 Legendary Whale": [
            f"🌊 The water EXPLODES as you pull up...",
            f"🐋 A LEGENDARY WHALE emerges from the depths!", 
            f"📸 Other fishermen stop to watch in awe!",
            f"🏆 This will be remembered forever! (+{pnl:.1f}% in {time_fishing})"
        ],
        "🦈 Profit Shark": [
            f"⚡ Something powerful breaks the surface!",
            f"🦈 A fierce PROFIT SHARK in all its glory!",
            f"💪 What a fight that was! Your arms are tired but happy!",
            f"🎉 Excellent technique! (+{pnl:.1f}% in {time_fishing})"
        ],
        "🐠 Diamond Fin Bass": [
            f"🌟 A beautiful fish shimmers in the sunlight!",
            f"🐠 A stunning Diamond Fin Bass! ",
            f"📱 Definitely worth a photo for the group!",
            f"😊 Nice catch! (+{pnl:.1f}% in {time_fishing})"
        ],
        "🐟 Lucky Minnow": [
            f"🐟 A small but lucky catch appears!",
            f"🍀 Lucky Minnow - small but still counts!",
            f"🎣 Every fish is a good fish!",
            f"👍 Not bad! (+{pnl:.1f}% in {time_fishing})"
        ],
        "🐡 Pufferfish of Regret": [
            f"😬 Uh oh... something weird on the hook...",
            f"🐡 A Pufferfish of Regret inflates angrily!",
            f"💸 This one's going to cost you...",
            f"😅 Better luck next time! ({pnl:.1f}% in {time_fishing})"
        ],
        "🦐 Soggy Boot": [
            f"🤦‍♂️ You feel the weight of disappointment...",
            f"🦐 An old Soggy Boot... seriously?",
            f"👢 Someone's trash became your... also trash",
            f"💔 Rough day on the water... ({pnl:.1f}% in {time_fishing})"
        ]
    }
    
    return "\n".join(stories.get(fish_name, [
        f"🎣 You caught something!",
        f"🐟 {fish_name}",
        f"📊 Result: {pnl:+.1f}% in {time_fishing}"
    ]))

def get_help_text():
    """Get help command text"""
    return """
🎣 **Fishing Bot Commands:**

/cast - Cast your line into ETH waters (costs 1 🪱 BAIT)
/hook - Reel in your catch and see what you got!  
/status - Check your current fishing progress
/test_card - Generate test fish cards (dev only)
/help - Show this help message

**How to play:**
1. Use /cast to start fishing (2x leverage on ETH)
2. Wait and watch the live updates
3. Use /hook when you want to close your position
4. Collect your fish NFT cards based on your trading performance!

**Fish Types:**
🦐 Soggy Boot (big loss) - Trash rarity
🐡 Pufferfish of Regret (small loss) - Trash rarity
🐟 Lucky Minnow (small profit) - Common rarity
🐠 Diamond Fin Bass (good profit) - Rare rarity
🦈 Profit Shark (great profit) - Epic rarity
🐋 Legendary Whale (amazing profit!) - Legendary rarity

New players get 10 🪱 BAIT tokens to start!
Works in groups and private chats!
    """

def format_cast_initial_message(username, current_price, remaining_bait):
    """Format the initial cast message"""
    return (
        f"🎣 {username} cast into ETH waters!\n\n"
        f"🌊 Line is in the water... 2x leverage active\n"
        f"💰 Entry price: ${current_price:.2f}\n"
        f"🪱 BAIT used: 1 (Remaining: {remaining_bait})\n\n"
        f"📍 Waiting for a bite... Use /hook when ready!"
    )

def format_fishing_status_update(username, time_fishing, status_desc, waiting_msg, entry_price, current_price, current_pnl):
    """Format fishing status update message"""
    return (
        f"🎣 {username} is fishing... ({time_fishing})\n\n"
        f"{status_desc}\n\n"
        f"{waiting_msg}\n\n"
        f"💰 Entry: ${entry_price:.2f} | Current: ${current_price:.2f}\n"
        f"📊 P&L: {current_pnl:+.1f}% (2x leverage)\n\n"
        f"Use /hook to reel in your catch!"
    )

def format_final_waiting_message(username, time_fishing, entry_price, current_price, current_pnl):
    """Format final waiting message"""
    return (
        f"🎣 {username} is fishing... ({time_fishing})\n\n"
        f"🔮 Now we wait... the fish will decide when it's ready.\n\n"
        f"💰 Entry: ${entry_price:.2f} | Current: ${current_price:.2f}\n"
        f"📊 P&L: {current_pnl:+.1f}% (2x leverage)\n\n"
        f"Use /hook when you feel the time is right!"
    )

def format_fishing_complete_caption(catch_story, pnl_percent, entry_price, current_price):
    """Format fishing complete photo caption"""
    return (
        f"🏆 FISHING COMPLETE! 🏆\n\n"
        f"{catch_story}\n\n"
        f"📊 Final P&L: {pnl_percent:+.1f}% (2x leverage)\n"
        f"💰 ${entry_price:.2f} → ${current_price:.2f}\n\n"
        f"🎣 Ready for another cast? Use /cast again!"
    )

def format_status_message(username, status_desc, entry_price, current_price, current_pnl):
    """Format status command message"""
    return (
        f"🎣 {username} fishing status:\n\n"
        f"{status_desc}\n\n"
        f"💰 Entry: ${entry_price:.2f} | Current: ${current_price:.2f}\n"
        f"📊 P&L: {current_pnl:+.1f}% (2x leverage)\n\n"
        f"Use /hook to reel in your catch!"
    )

def format_no_fishing_status(username, bait_tokens):
    """Format status when user is not fishing"""
    return (
        f"🎣 {username} is not currently fishing\n"
        f"🪱 BAIT tokens: {bait_tokens}\n"
        f"Use /cast to start fishing!"
    )

def format_new_user_status(username):
    """Format status for new users"""
    return (
        f"🎣 {username}, you haven't started fishing yet!\n"
        f"Use /cast to begin your fishing adventure!"
    )