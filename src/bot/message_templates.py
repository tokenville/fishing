"""
Message templates and text generators for the fishing bot.
Contains all static messages, dynamic text generation functions, and story templates.
"""

def escape_markdown(text):
    """Simply return text without escaping - we'll use plain text mode"""
    return text if text else ""

def get_cast_header(username, rod_name, pond_name, pond_pair, entry_price, leverage):
    """Fixed casting header with key information"""
    safe_username = username if username else "Рыбак"
    
    return (
        f"🎣 <b>{safe_username}</b> забрасывает удочку:\n\n"
        f"Удочка: <b>{rod_name}</b>\n"
        f"Водоем: <b>{pond_name}</b> ({pond_pair})\n"
        f"Стартовая позиция: <b>${entry_price:.2f}</b>\n"
        f"Плечо: <b>{leverage}x</b>"
    )

def get_cast_animated_sequence():
    """Animated sequence for casting (only this part changes)"""
    return [
        "💫 Взмах! Удочка летит через воздух!",
        "💦 ПЛЮХ! Идеальное попадание!",
        "🪱 Наживка медленно погружается...",
        "🐟 Рыба начинает интересоваться наживкой!",
        "✨ Подсекай с /hook, когда будешь готов..."
    ]

def format_cast_message(header, animated_text):
    """Combine header and animated text for casting message"""
    return f"{header}\n\n{animated_text}"


        
def get_hook_header(username, rod_name, pond_name, pond_pair, time_fishing, entry_price, current_price, leverage):
    """Fixed hook header with key information"""
    safe_username = username if username else "Рыбак"
    
    return (
        f"🎣 <b>{safe_username} ПОДСЕКАЕТ!</b>\n\n"
        f"Удочка: <b>{rod_name}</b>\n"
        f"Водоем: <b>{pond_name}</b> ({pond_pair})\n"
        f"⏱ Время рыбалки: <b>{time_fishing}</b>\n"
        f"💰 Позиция: ${entry_price:.2f} → <b>${current_price:.2f}</b>\n"
        f"Плечо: <b>{leverage}x</b>"
    )

def get_hook_animated_sequence():
    """Animated sequence for hooking (only this part changes)"""
    return [
        "⚡ Подсекаем! Что-то на крючке!",
        "🎣 Борьба началась! Тянем осторожно...",
        "🌊 Сопротивление! Рыба не хочет сдаваться!",
        "💫 Почти вытащили... последнее усилие!",
        "🐟 Что-то поднимается из глубин!"
    ]

def format_hook_message(header, animated_text):
    """Combine header and animated text for hook message"""
    return f"{header}\n\n{animated_text}"

def get_hook_tension_message(pnl):
    """Get tension-building message before revealing catch"""
    if pnl > 20:
        return "🎣 ЭПИЧЕСКАЯ БИТВА! Вся леска трясется! Это что-то ОГРОМНОЕ! 🌊💥"
    elif pnl > 10:
        return "🐠 Сильное сопротивление! Эта рыба борется! ⚡"
    elif pnl > 0:
        return "🐟 Что-то приличное на крючке... посмотрим что поймали! 🤔"
    elif pnl > -10:
        return "🌊 Ощущается легко... может просто водоросли? 😅"
    else:
        return "🦐 О нет... это похоже на мусор... 😬"

def get_catch_story_from_db(fish_data, pnl, time_fishing):
    """Get dramatic catch reveal story from database fish data"""
    if not fish_data:
        return f"🎣 Вы что-то поймали!\n📊 Результат: {pnl:+.1f}% за {time_fishing}"
    
    # Handle both old (12 fields) and new (13 fields with ai_prompt) formats
    if len(fish_data) == 12:
        _, fish_name, emoji, _, _, _, _, _, _, _, story_template, _ = fish_data
    elif len(fish_data) == 13:  # 13 fields with ai_prompt at the end (after created_at)
        _, fish_name, emoji, _, _, _, _, _, _, _, story_template, _, _ = fish_data
    else:
        # Safe fallback for unexpected formats
        fish_name = fish_data[1] if len(fish_data) > 1 else "Неизвестная рыба"
        emoji = fish_data[2] if len(fish_data) > 2 else "🐟"
        story_template = fish_data[10] if len(fish_data) > 10 else None
    
    # Use story template from database
    if story_template:
        story = story_template.format(
            emoji=emoji,
            name=fish_name,
            pnl=pnl,
            time_fishing=time_fishing
        )
        return f"{story} ({pnl:+.1f}% за {time_fishing})"
    
    # Fallback to simple story
    return f"🎣 Вы поймали {emoji} {fish_name}!\n📊 Результат: {pnl:+.1f}% за {time_fishing}"


def get_help_text():
    """Get dynamic help command text from database"""
    from src.database.db_manager import DATABASE_PATH
    import sqlite3
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get fish statistics
        cursor.execute('''
            SELECT emoji, name, rarity, description, min_pnl, max_pnl, required_ponds, required_rods
            FROM fish 
            ORDER BY min_pnl DESC
        ''')
        fish_data = cursor.fetchall()
        
        # Get ponds count and info
        cursor.execute('SELECT COUNT(*) FROM ponds WHERE is_active = 1')
        ponds_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT name, trading_pair, required_level 
            FROM ponds 
            WHERE is_active = 1 
            ORDER BY required_level
        ''')
        ponds_data = cursor.fetchall()
        
        # Get rods count and leverage range
        cursor.execute('SELECT COUNT(*) FROM rods')
        rods_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(leverage), MAX(leverage) FROM rods')
        leverage_range = cursor.fetchone()
        
        # Get starter bait amount (from user creation)
        cursor.execute('SELECT bait_tokens FROM users WHERE bait_tokens = 10 LIMIT 1')
        starter_bait = cursor.fetchone()
        starter_bait_amount = starter_bait[0] if starter_bait else 10
        
        conn.close()
        
        # Build dynamic help text
        help_text = """🎣 <b>КОМАНДЫ БОТА РЫБАЛКИ:</b>

/cast - Закинуть удочку (стоимость: 1 🪱 BAIT)
/hook - Вытащить улов и посмотреть что поймали!
/status - Проверить текущий статус рыбалки
/help - Показать это сообщение

<b>🎮 КАК ИГРАТЬ:</b>
1. Используйте /cast чтобы начать рыбалку
2. Ждите и следите за анимацией заброса
3. Используйте /status чтобы проверить прогресс
4. Используйте /hook когда готовы завершить позицию
5. Получите карточку рыбы в зависимости от результата!

<b>🐟 ТИПЫ РЫБ:</b>"""
        
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
            emoji, name, rarity, _, min_pnl, max_pnl, required_ponds, required_rods = fish
            
            # Check if it's a special fish (has requirements)
            if required_ponds or required_rods:
                special_fish.append(fish)
            else:
                # Regular fish grouped by rarity
                if rarity in rarity_groups:
                    rarity_groups[rarity].append(fish)
        
        # Add regular fish by rarity
        rarity_names = {
            'trash': 'Мусор',
            'common': 'Обычная', 
            'rare': 'Редкая',
            'epic': 'Эпическая',
            'legendary': 'Легендарная'
        }
        
        for rarity in ['legendary', 'epic', 'rare', 'common', 'trash']:
            for fish in rarity_groups[rarity]:
                emoji, name, _, _, min_pnl, max_pnl, _, _ = fish
                pnl_desc = f"({min_pnl:+.0f}% to {max_pnl:+.0f}%)" if min_pnl != max_pnl else f"({min_pnl:+.0f}%)"
                help_text += f"\n{emoji} {name} {pnl_desc} - {rarity_names[rarity]}"
        
        # Add special fish section if any exist
        if special_fish:
            help_text += "\n\n<b>🌟 ОСОБЫЕ РЫБЫ:</b>"
            for fish in special_fish:
                emoji, name, rarity, _, min_pnl, max_pnl, required_ponds, required_rods = fish
                
                # Build requirement description
                requirements = []
                if required_ponds:
                    # Get pond names for requirements
                    pond_ids = required_ponds.split(',')
                    pond_names = []
                    for pond_data in ponds_data:
                        if str(ponds_data.index(pond_data) + 1) in pond_ids:
                            pond_names.append(pond_data[0])
                    if pond_names:
                        requirements.append(f"только {'/'.join(pond_names)}")
                
                if required_rods:
                    requirements.append("топовые удочки")
                
                req_text = ", ".join(requirements) if requirements else "особые условия"
                help_text += f"\n{emoji} {name} - {req_text}"
        
        # Add dynamic system info
        help_text += f"\n\n<b>⚙️ СИСТЕМА:</b>"
        help_text += f"\n• {rods_count} типов удочек с плечом {leverage_range[0]}x до {leverage_range[1]}x"
        help_text += f"\n• {ponds_count} торговых водоемов с разными криптопарами:"
        
        for pond in ponds_data[:4]:  # Show first 4 ponds
            help_text += f"\n  └ {pond[0]} ({pond[1]}) - уровень {pond[2]}+"
        
        if ponds_count > 4:
            help_text += f"\n  └ ... и еще {ponds_count - 4}"
            
        help_text += f"\n• Система уровней для разблокировки новых локаций"
        help_text += f"\n• Новые игроки получают {starter_bait_amount} 🪱 BAIT токенов"
        help_text += f"\n• Работает в групповых и личных чатах!"
        
        return help_text
        
    except Exception:
        # Fallback to static text if database fails
        return """🎣 <b>КОМАНДЫ БОТА РЫБАЛКИ:</b>

/cast - Закинуть удочку (стоимость: 1 🪱 BAIT)
/hook - Вытащить улов и посмотреть что поймали!
/status - Проверить текущий статус рыбалки
/help - Показать это сообщение

<i>⚠️ Система рыбалки временно недоступна для отображения.</i>
🚀 Попробуйте /cast чтобы начать игру!"""


def format_fishing_complete_caption(catch_story, pnl_percent, entry_price, current_price, leverage):
    """Format fishing complete photo caption"""
    pnl_color = "🟢" if pnl_percent >= 0 else "🔴"
    return (
        f"🏆 <b>РЫБАЛКА ЗАВЕРШЕНА!</b> 🏆\n\n"
        f"{catch_story}\n\n"
        f"<b>Финальный результат:</b>\n"
        f"{pnl_color} P&L: <b>{pnl_percent:+.1f}%</b> (плечо {leverage}x)\n"
        f"💰 Цена: ${entry_price:.2f} → ${current_price:.2f}\n\n"
        f"🎣 Готовы к новому забросу? Используйте /cast!"
    )


def format_enhanced_status_message(username, pond_name, pond_pair, rod_name, leverage, entry_price, current_pnl, time_fishing):
    """Format enhanced status command message with simple readable structure"""
    safe_username = escape_markdown(username) if username else "Рыбак"
    pnl_color = "🟢" if current_pnl >= 0 else "🔴"
    
    return (
        f"🎣 <b>Статус рыбалки {safe_username}:</b>\n\n"
        f"Удочка: <b>{rod_name}</b>\n"
        f"Водоем: <b>{pond_name}</b> ({pond_pair})\n"
        f"⏱ Время рыбалки: <b>{time_fishing}</b>\n"
        f"Стартовая позиция: <b>${entry_price:.2f}</b>\n"
        f"{pnl_color} PnL: <b>{current_pnl:+.1f}%</b> (плечо {leverage}x)\n\n"
        f"🪝 Используйте /hook чтобы вытащить улов!"
    )

def format_no_fishing_status(username, bait_tokens):
    """Format status when user is not fishing"""
    safe_username = escape_markdown(username) if username else "Рыбак"
    
    return (
        f"🎣 <b>Статус рыбалки {safe_username}:</b>\n\n"
        f"📊 Статус: <i>Не рыбачит</i>\n"
        f"🪱 Токены BAIT: <b>{bait_tokens}</b>\n\n"
        f"🚀 Используйте /cast чтобы начать рыбалку!"
    )

def format_new_user_status(username):
    """Format status for new users"""
    safe_username = escape_markdown(username) if username else "Рыбак"
    
    return (
        f"🎣 <b>Статус рыбалки {safe_username}:</b>\n\n"
        f"🆕 Статус: <b>Новый игрок</b>\n"
        f"🪱 Токены BAIT: <b>10</b> (стартовый бонус)\n\n"
        f"🚀 Используйте /cast чтобы начать рыбалку!"
    )