#!/usr/bin/env python3
"""
Пример скрипта для управления AI-промптами рыб
Использует обновленную систему генерации изображений с поддержкой промптов из БД

Установка зависимостей:
pip install -r requirements.txt

Использование:
python example_prompt_management.py
"""

import asyncio
import sys
import os

# Добавить путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.generators.fish_card_generator import prompt_manager
from src.database.db_manager import init_database

def print_header(title):
    """Красивый заголовок"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_fish_prompt(fish_data):
    """Форматированный вывод данных рыбы"""
    fish_id, name, emoji, rarity, ai_prompt = fish_data
    print(f"ID: {fish_id}")
    print(f"Название: {emoji} {name}")
    print(f"Редкость: {rarity}")
    if ai_prompt:
        print(f"AI Промпт: {ai_prompt[:100]}...")
    else:
        print("AI Промпт: НЕ УСТАНОВЛЕН")
    print("-" * 60)

async def main():
    """Главная функция демонстрации"""
    
    # Инициализируем базу данных
    print_header("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    init_database()
    print("✅ База данных инициализирована с новым полем ai_prompt")
    
    # 1. Показать все текущие промпты
    print_header("ТЕКУЩИЕ AI-ПРОМПТЫ ВСЕХ РЫБ")
    all_prompts = prompt_manager.list_all_prompts()
    
    for fish_data in all_prompts:
        print_fish_prompt(fish_data)
    
    print(f"Всего рыб в базе: {len(all_prompts)}")
    
    # 2. Получить конкретный промпт
    print_header("ПОЛУЧЕНИЕ ПРОМПТА КОНКРЕТНОЙ РЫБЫ")
    fish_name = "Золотой Дракон"
    prompt = prompt_manager.get_prompt(fish_name)
    if prompt:
        print(f"🐲 {fish_name}: {prompt}")
    else:
        print(f"❌ Промпт для '{fish_name}' не найден")
    
    # 3. Обновить промпт одной рыбы
    print_header("ОБНОВЛЕНИЕ ПРОМПТА ОДНОЙ РЫБЫ")
    new_prompt = "An ancient golden dragon fish with crystalline scales, swimming through molten lava underwater, epic cinematic lighting, mystical fire effects, 4K quality"
    
    success = prompt_manager.update_prompt(fish_name, new_prompt)
    if success:
        print(f"✅ Промпт для '{fish_name}' успешно обновлен")
        
        # Проверим обновление
        updated_prompt = prompt_manager.get_prompt(fish_name)
        print(f"Новый промпт: {updated_prompt}")
    else:
        print(f"❌ Не удалось обновить промпт для '{fish_name}'")
    
    # 4. Массовое обновление промптов
    print_header("МАССОВОЕ ОБНОВЛЕНИЕ ПРОМПТОВ")
    
    bulk_prompts = {
        "Счастливая Плотва": "A cheerful small silver fish with sparkling fins, swimming in crystal clear water, bright natural lighting, joyful underwater scene",
        "Акула Профита": "A powerful shark with golden fin tips, swimming through treasure-filled waters, dramatic lighting with coin sparkles, success and prosperity theme"
    }
    
    updated_count = prompt_manager.bulk_update_prompts(bulk_prompts)
    print(f"✅ Массово обновлено промптов: {updated_count}")
    
    # 5. Генерация дефолтного промпта
    print_header("ГЕНЕРАЦИЯ ДЕФОЛТНОГО ПРОМПТА")
    
    default_prompt = prompt_manager.generate_default_prompt("Лунный Единорог")
    print(f"Сгенерированный дефолтный промпт для 'Лунный Единорог':")
    print(default_prompt)
    
    # 6. Очистка кеша изображений
    print_header("УПРАВЛЕНИЕ КЕШЕМ ИЗОБРАЖЕНИЙ")
    print("💡 Для очистки кеша используйте:")
    print("prompt_manager.clear_image_cache()  # Очистить весь кеш")
    print("prompt_manager.clear_image_cache('Название рыбы')  # Очистить кеш конкретной рыбы")
    print("\n⚠️  После изменения промптов рекомендуется очистить кеш для перегенерации изображений")
    
    # 7. Тестирование генерации карточки (требует OPENROUTER_API_KEY)
    print_header("ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ КАРТОЧКИ")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        from src.generators.fish_card_generator import generate_fish_card_from_db
        from src.database.db_manager import get_fish_by_name
        
        # Получим данные рыбы из БД
        fish_data = get_fish_by_name("Золотой Дракон")
        
        if fish_data:
            print(f"🧪 Тестируем генерацию карточки для '{fish_name}'...")
            try:
                # Генерируем карточку рыбы
                card_image = await generate_fish_card_from_db(fish_data, 125.5, "3мин 45с")
                
                # Сохраняем тестовое изображение
                test_image_path = f"test_card_{fish_name.replace(' ', '_')}.png"
                with open(test_image_path, 'wb') as f:
                    f.write(card_image)
                
                print(f"✅ Карточка успешно сгенерирована: {test_image_path}")
                print(f"📊 Размер изображения: {len(card_image)} байт")
                
            except Exception as e:
                print(f"❌ Ошибка генерации карточки: {e}")
        else:
            print(f"❌ Рыба '{fish_name}' не найдена в базе данных")
    else:
        print("⚠️  OPENROUTER_API_KEY не установлен - пропускаем тест генерации")
        print("   Установите переменную окружения для полного тестирования:")
        print("   export OPENROUTER_API_KEY='your_api_key_here'")
    
    # 8. Полезные советы
    print_header("ПОЛЕЗНЫЕ СОВЕТЫ ПО РАБОТЕ С ПРОМПТАМИ")
    print("""
📝 РЕКОМЕНДАЦИИ ПО СОЗДАНИЮ ПРОМПТОВ:

1. Структура хорошего промпта:
   - Описание рыбы (цвет, форма, особенности)
   - Окружение (underwater, deep sea, coral reef)
   - Качество (high quality, 4K, professional)
   - Стиль (realistic, digital art, cinematic)

2. Модификаторы по редкости:
   - trash: "murky water, low quality, dull colors"
   - common: "clear water, natural lighting" 
   - rare: "beautiful lighting, vibrant colors"
   - epic: "dramatic lighting, magical effects"
   - legendary: "epic lighting, divine aura, mystical atmosphere"

3. Примеры качественных промптов:
   - "A majestic golden whale with crystalline fins, swimming through sunbeams in deep blue ocean, epic cinematic lighting, high quality digital art"
   - "A small colorful tropical fish with iridescent scales, coral reef background, bright natural lighting, underwater photography style"

4. После изменения промптов:
   - Очистите кеш: prompt_manager.clear_image_cache()
   - Протестируйте генерацию новых изображений
   - Проверьте качество результатов

5. Массовые операции:
   - Используйте bulk_update_prompts() для обновления нескольких рыб
   - Сохраняйте резервную копию базы данных перед массовыми изменениями
    """)
    
    print_header("ГОТОВО!")
    print("🎣 Система управления AI-промптами готова к использованию!")
    print("📖 Изучите код этого примера для понимания всех возможностей")

if __name__ == "__main__":
    # Запускаем асинхронную функцию
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()