# Изменения системы начисления бонусов и балансов

## 📋 Краткое резюме

Система начисления бонусов и балансов была полностью переработана в соответствии с новыми требованиями.

## ✅ Что было исправлено

### 1. При регистрации пользователя
**Было:**
- 10 BAIT tokens
- 2 стартовые удочки (Long + Short)
- Баланс $10,000

**Стало:**
- 0 BAIT tokens
- 1 стартовая удочка (Long)
- Баланс $0 (сохраняется в таблице `user_balances`)

### 2. За добавление в группу (онбординг)
- ✅ +10 BAIT (работало корректно, без изменений)

### 3. За первый /cast
**Было:**
- Не работало (удочки уже давались при регистрации)

**Стало:**
- +1 удочка Short (теперь у пользователя Long + Short)

### 4. За первый улов (/hook)
**Было:**
- +$1000 в поле `balance_bonus`

**Стало:**
- +$10,000 к балансу в таблице `user_balances` (стартовый капитал)

### 5. Система баланса
**Было:**
- Баланс рассчитывался динамически: `10000 + SUM(1000 * pnl_percent / 100) + balance_bonus`

**Стало:**
- Баланс хранится статично в таблице `user_balances`
- Начальный баланс: $0
- После каждого /hook баланс обновляется: `balance += 1000 * pnl_percent / 100`

### 6. Удалены устаревшие поля
- `balance_bonus` из таблицы `users` (теперь используется `user_balances`)
- `inheritance_claimed` из таблицы `users` (устаревшая функциональность)

## 📊 Изменения в базе данных

### Новая таблица
```sql
CREATE TABLE user_balances (
    user_id BIGINT PRIMARY KEY REFERENCES users(telegram_id),
    balance NUMERIC(18, 2) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Изменения в users
```sql
-- Было: bait_tokens INTEGER DEFAULT 10
-- Стало: bait_tokens INTEGER DEFAULT 0

-- Удалены устаревшие поля:
-- balance_bonus NUMERIC(18, 2) DEFAULT 0  -- удалено
-- inheritance_claimed BOOLEAN DEFAULT FALSE  -- удалено
```

## 🔧 Изменения в коде

### src/database/db_manager.py
1. ✅ Добавлена таблица `user_balances` в `init_database()`
2. ✅ Изменено начальное значение BAIT: 10 → 0
3. ✅ Создана функция `give_single_starter_rod()` для выдачи одной удочки
4. ✅ Изменена `create_user()` - выдает 0 BAIT, создает баланс, дает 1 Long удочку
5. ✅ Добавлены функции работы с балансом:
   - `get_user_balance()` - получить баланс из таблицы
   - `update_user_balance_after_hook()` - обновить баланс после улова
   - `add_balance_bonus()` - добавить бонус к балансу
6. ✅ Обновлена `get_user_virtual_balance()` - читает из `user_balances`
7. ✅ Обновлена `award_first_cast_reward()` - дает Short удочку
8. ✅ Обновлена `award_first_catch_reward()` - использует `user_balances`
9. ✅ Обновлена `get_flexible_leaderboard()` - использует `user_balances.balance`
10. ✅ Добавлена `migrate_user_balances()` - миграция существующих пользователей

### src/bot/commands/hook.py
1. ✅ Добавлен импорт `update_user_balance_after_hook`
2. ✅ После `close_position()` добавлен вызов `update_user_balance_after_hook()`

### src/bot/commands/start.py
1. ✅ Убран `give_starter_rod()` для существующих пользователей
2. ✅ Убран неиспользуемый импорт `give_starter_rod`

## 🚀 Миграция

Создан скрипт `migrate_balances.py` для миграции существующих пользователей:

```bash
python3 migrate_balances.py
```

Скрипт:
1. Инициализирует базу данных (создает таблицу `user_balances`)
2. Для каждого пользователя рассчитывает баланс по старой формуле
3. Сохраняет баланс в таблицу `user_balances`

**Статус:** ✅ Миграция выполнена успешно (0 пользователей мигрировано - база пустая)

## 📝 Итоговая логика для новых пользователей

1. **Регистрация** → 0 BAIT, 1 Long удочка, $0 баланс
2. **Добавление в группу** → +10 BAIT
3. **Первый /cast** → +1 Short удочка (бесплатный cast)
4. **Первый /hook** → +$10,000 к балансу (стартовый капитал)
5. **Каждый последующий /hook** → баланс изменяется на основе PnL: `delta = $1000 * pnl% / 100`

## 🔍 Тестирование

Рекомендуется протестировать:
1. ✅ Регистрация нового пользователя (0 BAIT, 1 удочка)
2. ✅ Добавление в группу (+10 BAIT)
3. ✅ Первый cast (получение Short удочки)
4. ✅ Первый hook (+$1000)
5. ✅ Второй hook (изменение баланса по PnL)
6. ✅ Leaderboard (корректное отображение балансов)

## 📦 Файлы с изменениями

- `src/database/db_manager.py` - основные изменения
- `src/bot/commands/hook.py` - обновление баланса после hook
- `src/bot/commands/start.py` - убрана автоматическая выдача удочек
- `migrate_balances.py` - скрипт миграции (новый файл)
- `BALANCE_MIGRATION_NOTES.md` - эта документация (новый файл)
