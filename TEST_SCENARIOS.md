# 🧪 Test Scenarios - Fishing Bot

Полный список тестовых сценариев для Telegram бота виртуальной рыбалки.

**Дата создания:** 2025-10-17
**Версия:** 1.0
**Всего сценариев:** 87

---

## 📑 Содержание

1. [Базовая рыбалка](#1-базовая-рыбалка) (8 сценариев)
2. [Онбординг](#2-онбординг) (7 сценариев)
3. [Платежи (Telegram Stars)](#3-платежи-telegram-stars) (6 сценариев)
4. [Групповые функции](#4-групповые-функции) (8 сценариев)
5. [MiniApp интерфейс](#5-miniapp-интерфейс) (15 сценариев)
6. [Лидерборды](#6-лидерборды) (5 сценариев)
7. [Quick Actions (кнопки)](#7-quick-actions-кнопки) (10 сценариев)
8. [UI System & States](#8-ui-system--states) (8 сценариев)
9. [Система прогрессии](#9-система-прогрессии) (6 сценариев)
10. [API Endpoints](#10-api-endpoints) (14 сценариев)

---

## 1. Базовая рыбалка

### 1.1 Первый заброс новым пользователем

**Preconditions:**
- Пользователь зарегистрирован через /start
- Onboarding пройден или пропущен
- Пользователь имеет >= 1 BAIT токен
- Нет активной позиции

**Steps:**
1. Отправить команду `/cast`
2. Выбрать пруд из списка (кнопка inline keyboard)

**Expected Results:**
- Показывается список доступных прудов с emoji и названиями
- После выбора: анимация заброса (3 сообщения с редактированием)
- Списывается 1 BAIT токен
- Создается активная позиция в БД
- Финальное сообщение: "🔮 Now we wait... the fish will decide"
- State: IDLE → POND_SELECTION → CASTING → FISHING

**Edge Cases:**
- BAIT = 0: показать error block с кнопкой [Buy BAIT]
- Уже есть активная позиция: error block с кнопками [Hook Now] [Status]

---

### 1.2 Выбор пруда (pond selection)

**Preconditions:**
- Команда `/cast` выполнена
- Пользователь видит список прудов

**Steps:**
1. Кликнуть на любой доступный пруд (например, "🏞️ TAC Lake")

**Expected Results:**
- Callback `select_pond_{pond_id}` обработан
- Анимация заброса начинается
- Выбранный пруд записан в position
- Trading pair пруда используется для price fetching

**Edge Cases:**
- Пруд заблокирован по уровню: должен быть disabled в списке или показывать warning
- Групповой пруд: должен показывать специальную метку

---

### 1.3 Анимация заброса (casting animation)

**Preconditions:**
- Пруд выбран
- BAIT списан

**Steps:**
1. Наблюдать анимацию заброса

**Expected Results:**
- Сообщение редактируется 3 раза:
  1. "🎣 Getting ready to cast..."
  2. "💫 Whoosh! Line flies through the air!"
  3. "💦 SPLASH! Perfect landing!"
- Финальное сообщение: "🔮 Now we wait... the fish will decide"
- Пауза между шагами ~2 секунды
- После финала сообщение остается неизменным

**Edge Cases:**
- Сетевая ошибка во время анимации: должен завершиться gracefully
- Пользователь отправляет другую команду: анимация продолжается

---

### 1.4 Проверка статуса во время рыбалки

**Preconditions:**
- Активная позиция существует
- Рыбалка в процессе

**Steps:**
1. Отправить команду `/status`

**Expected Results:**
- InfoBlock с текущими данными:
  - Время в воде (duration)
  - Текущий P&L (с цветовым индикатором 🟢/🔴)
  - Используемая удочка и leverage
  - Trading pair и пруд
- Footer hint: "Pro tip: Use /hook to complete your catch"
- Без кнопок (InfoBlock, не CTA)

**Edge Cases:**
- Позиция только что создана: duration = "0m 0s"
- Очень длительная позиция: корректное отображение времени (>24h)

---

### 1.5 Подсечка рыбы (hook)

**Preconditions:**
- Активная позиция существует
- Время с момента cast > 0

**Steps:**
1. Отправить команду `/hook`

**Expected Results:**
- Анимация подсечки (3 шага):
  1. "🎣 {username} SETS THE HOOK!"
  2. "⚡ Reeling in... almost there!"
  3. "🌊 Something is coming up from the depths!"
- Параллельно: получение текущей цены, расчет P&L
- Параллельно: генерация рыбьей карточки (AI + CDN upload)
- Результат:
  - Изображение рыбы (Bunny CDN URL)
  - Детальная информация о рыбе
  - P&L результат (с цветом)
  - Обновление виртуального баланса
- CTA Block с кнопками:
  - Групповой пруд: [📢 Share in Group] [🎣 Cast Again]
  - Соло пруд: [🎣 Cast Again]
- State: FISHING → HOOKING → CATCH_COMPLETE

**Edge Cases:**
- Нет активной позиции: error "No active fishing position"
- Сетевая ошибка price API: retry logic (3 попытки)
- AI генерация изображения fails: использовать placeholder или cached image
- P&L = 0: показать нейтральную рыбу
- Negative P&L: показать trash fish (Старый Сапог)

---

### 1.6 Повторный заброс после подсечки

**Preconditions:**
- Предыдущая рыбалка завершена (CATCH_COMPLETE state)
- CTA block показан с кнопкой [Cast Again]

**Steps:**
1. Кликнуть кнопку [🎣 Cast Again] или отправить `/cast`

**Expected Results:**
- Предыдущий CTA block очищается (buttons removed)
- Новый flow заброса начинается (pond selection)
- State: CATCH_COMPLETE → IDLE → POND_SELECTION

**Edge Cases:**
- BAIT закончился: показать offer to buy
- Сразу после hook: должно работать без задержек

---

### 1.7 Попытка заброса с активной позицией

**Preconditions:**
- Активная позиция уже существует
- Пользователь в FISHING state

**Steps:**
1. Отправить команду `/cast`

**Expected Results:**
- ErrorBlock с header "❌ Already Fishing!"
- Body: "{username}, complete your current catch first!"
- Buttons: [🪝 Hook Now] [📊 Check Status]
- Предыдущий CTA cleared

**Edge Cases:**
- Одновременные /cast команды: должны обе показать ошибку

---

### 1.8 Попытка подсечки без заброса

**Preconditions:**
- Нет активной позиции
- Пользователь в IDLE state

**Steps:**
1. Отправить команду `/hook`

**Expected Results:**
- Error message: "❌ No active fishing position!"
- Body: "You need to cast first. Click below to start fishing."
- CTA Button: [🎣 Start Fishing]

**Edge Cases:**
- Hook сразу после предыдущего hook: корректная ошибка

---

## 2. Онбординг

### 2.1 Первый запуск /start

**Preconditions:**
- Пользователь первый раз запускает бота
- Нет записи в users table

**Steps:**
1. Отправить команду `/start`

**Expected Results:**
- Создается запись в users table
- Начальные параметры:
  - bait_tokens = 5 (или 10 если указано в коде)
  - level = 1
  - experience = 0
- Создается onboarding_progress запись
- Отправляется intro step message:
  - Приветствие с историей игры
  - Buttons: [🎣 Start Tutorial] [⏭️ Skip]

**Edge Cases:**
- /start от существующего пользователя: показать help или статус
- /start с deep link параметром

---

### 2.2 Прохождение tutorial - Intro step

**Preconditions:**
- Onboarding в STEP_INTRO

**Steps:**
1. Нажать кнопку [🎣 Start Tutorial]

**Expected Results:**
- Callback `ob_start` обработан
- Переход на STEP_JOIN_GROUP или STEP_CAST (в зависимости от конфига)
- Сообщение с объяснением следующего шага

**Edge Cases:**
- Skip tutorial: переход сразу в completed state

---

### 2.3 Join Group step

**Preconditions:**
- Onboarding в STEP_JOIN_GROUP
- GROUP_INVITE_URL настроен в env

**Steps:**
1. Просмотреть сообщение с предложением присоединиться к группе
2. (Опционально) Вступить в группу
3. Нажать [✅ I Joined] или [⏭️ Skip]

**Expected Results:**
- Кнопка с URL invite link
- При клике [I Joined] и verification (если настроена):
  - Бонус: +5 BAIT или другой reward
  - Переход на STEP_CAST
- При Skip: переход без бонуса

**Edge Cases:**
- GROUP_INVITE_URL не настроен: пропустить этот шаг
- Пользователь уже в группе: автоматический bonus

---

### 2.4 Cast instruction step

**Preconditions:**
- Onboarding в STEP_CAST

**Steps:**
1. Прочитать инструкцию о /cast
2. Кликнуть [🎣 Try First Cast]

**Expected Results:**
- Callback `ob_send_cast` вызывает обычную cast команду
- Onboarding не завершается, остается в STEP_CAST до hook

**Edge Cases:**
- Пользователь вручную вызывает /cast: должно работать

---

### 2.5 Hook instruction step

**Preconditions:**
- Onboarding в STEP_HOOK
- Есть активная позиция после первого cast

**Steps:**
1. Прочитать инструкцию о /hook
2. Подождать немного
3. Кликнуть [🪝 Complete First Catch] или отправить `/hook`

**Expected Results:**
- Callback `ob_send_hook` вызывает hook команду
- После успешного hook:
  - Onboarding завершается (completed = true)
  - Бонус за первую рыбу (если настроен)
  - CTA с поздравлением и [🎣 Continue Fishing]

**Edge Cases:**
- Hook без cast в onboarding: показать ошибку

---

### 2.6 Skip onboarding

**Preconditions:**
- В любом onboarding step

**Steps:**
1. Нажать кнопку [⏭️ Skip] или команду `/skip`

**Expected Results:**
- Onboarding помечается как completed
- Сообщение подтверждения
- CTA: [🎣 Start Fishing]
- Доступ ко всем командам

**Edge Cases:**
- /skip когда onboarding уже завершен: нейтральное сообщение

---

### 2.7 Claim Inheritance (MiniApp)

**Preconditions:**
- Новый пользователь открывает MiniApp
- inheritance_claimed = false

**Steps:**
1. Открыть MiniApp через button или web_app_link
2. Увидеть inheritance screen (письмо от дедушки)
3. Кликнуть [Accept Inheritance]

**Expected Results:**
- API call: POST /api/user/{user_id}/claim-inheritance
- inheritance_claimed = true
- bait_tokens += 10
- Telegram notification в чате
- Redirect на lobby screen
- Дедушкина удочка автоматически активна

**Edge Cases:**
- Повторный claim: показывать обычный lobby
- Claim через API и через бота одновременно: idempotency

---

## 3. Платежи (Telegram Stars)

### 3.1 Покупка BAIT - Small Pack (10 tokens)

**Preconditions:**
- Пользователь зарегистрирован
- BAIT < 10 (или любое количество)

**Steps:**
1. Команда `/buy` или кнопка [Buy BAIT]
2. Выбрать пакет "🪱 10 BAIT - ⭐100 Stars"
3. Telegram Stars payment flow:
   - Pre-checkout query
   - User confirms payment
   - Successful payment callback

**Expected Results:**
- Pre-checkout: validation (product exists, price correct)
- Transaction created в БД (status = pending)
- После оплаты:
  - Transaction completed (status = success)
  - bait_tokens += 10
  - Notification: "✅ Purchase successful! +10 BAIT"
  - CTA: [🎣 Start Fishing]

**Edge Cases:**
- Payment cancelled: transaction status = failed
- Payment error: показать error message
- Duplicate payment charge: idempotency check

---

### 3.2 Покупка BAIT - Medium Pack (50 tokens)

**Preconditions:**
- Пользователь имеет доступ к Telegram Stars

**Steps:**
1. `/buy`
2. Выбрать "🪱 50 BAIT - ⭐450 Stars (🔥 BEST VALUE)"
3. Подтвердить оплату

**Expected Results:**
- bait_tokens += 50
- Transaction record с product_id = 2

**Edge Cases:**
- Insufficient Stars balance: Telegram показывает ошибку

---

### 3.3 Покупка BAIT - Large Pack (100 tokens)

**Preconditions:**
- Пользователь может платить

**Steps:**
1. `/buy`
2. Выбрать "🪱 100 BAIT - ⭐800 Stars (Save 20%)"
3. Оплатить

**Expected Results:**
- bait_tokens += 100
- Лучшая цена за токен

**Edge Cases:**
- Concurrent purchases: корректная обработка параллельных транзакций

---

### 3.4 Автоматическое предложение при BAIT = 0

**Preconditions:**
- bait_tokens = 0
- Пользователь пытается /cast

**Steps:**
1. Отправить `/cast`

**Expected Results:**
- ErrorBlock: "❌ Out of BAIT!"
- Body: "You need BAIT tokens to fish. Purchase below:"
- Buttons: все 3 пакета как inline keyboard
- Callback: `buy_bait_{product_id}`

**Edge Cases:**
- User gets BAIT from другого источника: после покупки cast работает

---

### 3.5 Просмотр истории транзакций

**Preconditions:**
- У пользователя есть завершенные транзакции

**Steps:**
1. Команда `/transactions`

**Expected Results:**
- Список всех транзакций:
  - Дата/время
  - Продукт (название)
  - Количество BAIT
  - Цена в Stars
  - Status (✅ success / ❌ failed / ⏳ pending)
- Если нет транзакций: "No purchases yet"

**Edge Cases:**
- Очень много транзакций: pagination или limit (last 10)

---

### 3.6 Purchase через MiniApp

**Preconditions:**
- MiniApp открыт
- Lobby screen показан
- User кликает на BAIT balance

**Steps:**
1. Кликнуть на BAIT balance в lobby
2. Увидеть payment modal
3. Выбрать пакет
4. Оплатить через Telegram

**Expected Results:**
- API: POST /api/user/{user_id}/purchase
- Создается invoice
- Telegram payment flow
- После оплаты: MiniApp обновляет balance

**Edge Cases:**
- MiniApp closed во время payment: payment все равно проходит

---

## 4. Групповые функции

### 4.1 Добавление бота в группу

**Preconditions:**
- Бот не состоит в группе
- Пользователь - админ группы

**Steps:**
1. Добавить бота в группу
2. Дать права (optional: post messages, read messages)

**Expected Results:**
- ChatMemberHandler обрабатывает событие
- Бот отправляет welcome message в группу
- Создается запись group pond (если не существует)
- Показываются инструкции: "Use /gofishing to start!"

**Edge Cases:**
- Бот добавлен, но без прав: показать warning
- Бот удален из группы: очистить group pond?

---

### 4.2 Создание группового пруда

**Preconditions:**
- Бот в группе
- Group pond еще не создан для этой группы

**Steps:**
1. Бот автоматически создает pond при добавлении

**Expected Results:**
- Запись в ponds table:
  - group_chat_id = chat_id группы
  - Название = "Group Name Fishing Spot"
  - Торговая пара (может быть дефолтной или выбранной)
- Члены группы могут видеть этот pond в списке

**Edge Cases:**
- Группа переименована: обновить pond name
- Несколько ботов в одной группе: conflict resolution?

---

### 4.3 /gofishing команда в группе

**Preconditions:**
- Бот в группе
- Group pond создан
- Пользователь - член группы

**Steps:**
1. Отправить `/gofishing` в группу

**Expected Results:**
- Публичное сообщение в группе:
  - "{username} invites everyone to go fishing!"
  - Описание группового пруда
  - Button: [🎣 Join Fishing!]
- Callback: `join_fishing_{pond_id}`

**Edge Cases:**
- /gofishing в приватном чате: показать error "Only in groups"
- Concurrent /gofishing: несколько приглашений могут быть активны

---

### 4.4 Присоединение к групповой рыбалке

**Preconditions:**
- /gofishing сообщение показано
- Пользователь - член группы

**Steps:**
1. Кликнуть [🎣 Join Fishing!]

**Expected Results:**
- Callback обработан в приватном чате пользователя (не в группе!)
- Проверка: пользователь имеет BAIT
- Если да: cast начинается с этим group pond
- Если нет: предложение купить BAIT

**Edge Cases:**
- Пользователь не в группе: показать error
- Уже есть активная позиция: показать error

---

### 4.5 Share cast в группе

**Preconditions:**
- Пользователь завершил /cast в личном чате
- Был выбран групповой пруд

**Steps:**
1. После cast animation закончилась
2. Показывается кнопка [📢 Share Cast]
3. Кликнуть кнопку

**Expected Results:**
- Callback `share_cast`
- Публичное сообщение в группе:
  - "{username} just cast into {pond_name}!"
  - Информация о leveraged position
  - "Watch this space for results!"
- CTA в личном чате: [🎣 Cast Again]

**Edge Cases:**
- Бот удален из группы: показать error "Can't share, bot removed"
- Группа архивирована: graceful error

---

### 4.6 Share hook результата в группе

**Preconditions:**
- Пользователь завершил /hook
- Был выбран групповой пруд
- Рыба поймана

**Steps:**
1. После hook animation и fish card
2. CTA показывает [📢 Share in Group]
3. Кликнуть кнопку

**Expected Results:**
- Callback `share_hook`
- Публичное сообщение в группе:
  - Fish card image
  - "{username} caught {fish_name}!"
  - P&L результат
  - Информация о редкости рыбы
- Reward: +1 BAIT за sharing
- CTA обновляется: [🎣 Cast Again]

**Edge Cases:**
- Повторный share: должен быть blocked "Already shared"
- Negative P&L: все равно можно share

---

### 4.7 Групповой лидерборд

**Preconditions:**
- Пользователь в группе
- Несколько участников ловили рыбу в group pond

**Steps:**
1. Отправить `/leaderboard` в группе

**Expected Results:**
- Топ-10 участников ЭТОЙ ГРУППЫ (не глобальный)
- Privacy: только публичные данные (username, balance)
- Личные данные не показываются в группе

**Edge Cases:**
- Меньше 10 участников: показать всех
- Пользователь не в топ-10: показать "Your rank: #X"

---

### 4.8 Tracking group members

**Preconditions:**
- Бот в группе
- Участники присоединяются/покидают группу

**Steps:**
1. Новый участник присоединяется к группе
2. ChatMemberHandler обрабатывает событие

**Expected Results:**
- Обновление member list (если трекается)
- Welcome message новому участнику (optional)

**Edge Cases:**
- Массовое добавление участников: не спамить
- Бот kicked: очистка данных

---

## 5. MiniApp интерфейс

### 5.1 Открытие MiniApp - первый запуск

**Preconditions:**
- Новый пользователь (inheritance_claimed = false)
- Telegram MiniApp button нажата

**Steps:**
1. Нажать MiniApp button или web_app link
2. GET /webapp возвращает index.html
3. JavaScript инициализируется
4. GET /api/user/{user_id}/inheritance-status

**Expected Results:**
- Inheritance screen показан вместо lobby
- Красивое письмо от дедушки
- Wax seal с ₿
- Кнопка [Accept Inheritance]

**Edge Cases:**
- API unavailable: skeleton loader
- Network error: retry logic

---

### 5.2 Открытие MiniApp - returning user

**Preconditions:**
- inheritance_claimed = true
- Пользователь уже использовал бота

**Steps:**
1. Открыть MiniApp
2. GET /api/user/{user_id}/stats

**Expected Results:**
- Lobby screen показан:
  - Fisherman character SVG
  - Username и уровень
  - BAIT balance (clickable)
  - Virtual balance
- Navigation tabs: [Fish] [Rods] [Leaderboard]

**Edge Cases:**
- Skeleton loaders пока данные грузятся
- API slow: показывать progress

---

### 5.3 Lobby screen - просмотр статистики

**Preconditions:**
- MiniApp открыт на lobby screen

**Steps:**
1. Просмотреть все элементы UI

**Expected Results:**
- Character image (fisherman.svg)
- Stats display:
  - Level: {level} | XP: {experience}/{next_level_xp}
  - 🪱 BAIT: {bait_tokens}
  - 💰 Balance: ${balance}
- Active rod indicator
- Tabs для навигации

**Edge Cases:**
- Level max: показать max level badge
- Balance negative: красный цвет

---

### 5.4 Просмотр коллекции рыб

**Preconditions:**
- MiniApp открыт
- У пользователя есть пойманные рыбы

**Steps:**
1. Кликнуть tab [Fish]
2. GET /api/user/{user_id}/fish

**Expected Results:**
- Grid layout с рыбьими карточками
- Каждая карточка:
  - Fish image (Bunny CDN)
  - Emoji + name
  - Rarity badge (color coded)
  - P&L indicator
- Skeleton loaders до загрузки

**Edge Cases:**
- Нет рыб: empty state "No fish caught yet"
- Много рыб: infinite scroll или pagination
- Image load fail: placeholder image

---

### 5.5 Fish details modal

**Preconditions:**
- Fish collection открыта
- Пользователь видит список рыб

**Steps:**
1. Кликнуть на любую рыбу
2. Modal открывается с деталями

**Expected Results:**
- Full-size fish image
- Детальная информация:
  - Name и emoji
  - Description/story
  - Trading info (entry/exit price, P&L)
  - Rod used, leverage
  - Pond name
  - Timestamp поимки
- Close button

**Edge Cases:**
- Very long description: scrollable
- Missing data: показывать "N/A"

---

### 5.6 Rod selection screen

**Preconditions:**
- MiniApp открыт
- GET /api/user/{user_id}/rods вернул список

**Steps:**
1. Кликнуть tab [Rods]
2. Просмотреть carousel/grid с удочками

**Expected Results:**
- Список доступных удочек:
  - SVG image (long-rod.svg / short-rod.svg)
  - Name
  - Leverage (2x, 5x, etc)
  - Rod type (Long/Short)
  - Rarity badge
- Active rod highlighted
- Button [Set Active] на неактивных

**Edge Cases:**
- Только одна удочка: дедушкина удочка (starter)
- Locked rods: показывать с lock icon и requirements

---

### 5.7 Изменение активной удочки

**Preconditions:**
- Rods screen открыт
- У пользователя >= 2 удочки

**Steps:**
1. Выбрать неактивную удочку
2. Кликнуть [Set Active]
3. POST /api/user/{user_id}/active-rod {rod_id}

**Expected Results:**
- API call успешен
- UI обновляется: новая удочка highlighted как active
- Toast notification: "Rod changed to {rod_name}"
- Lobby обновляет active rod display

**Edge Cases:**
- API error: показать error toast
- Concurrent updates: last write wins

---

### 5.8 Leaderboard в MiniApp

**Preconditions:**
- MiniApp открыт

**Steps:**
1. Кликнуть tab [Leaderboard]
2. GET /api/leaderboard

**Expected Results:**
- Топ-10 игроков:
  - Rank (#1, #2, etc)
  - Username
  - Level badge
  - Balance
- Пользователь highlighted если в топ-10
- "Your rank: #X" внизу если не в топ-10

**Edge Cases:**
- Меньше 10 игроков: показать всех
- User rank very low: показать "Rank: #1543"

---

### 5.9 Casting через MiniApp

**Preconditions:**
- MiniApp открыт
- Пользователь имеет BAIT
- Нет активной позиции

**Steps:**
1. На lobby screen кликнуть [🎣 Cast]
2. GET /api/user/{user_id}/ponds
3. Выбрать pond
4. POST /api/user/{user_id}/cast {pond_id}

**Expected Results:**
- API создает position
- UI показывает animation или notification
- Telegram notification в чате
- MiniApp переключается на fishing state
- Показывается текущий P&L (live updates?)

**Edge Cases:**
- Нет BAIT: предложение купить
- API unavailable: error message

---

### 5.10 Hooking через MiniApp

**Preconditions:**
- Активная позиция существует
- GET /api/user/{user_id}/position возвращает данные

**Steps:**
1. Видеть fishing state в MiniApp
2. Кликнуть [🪝 Hook]
3. POST /api/user/{user_id}/hook

**Expected Results:**
- API закрывает position, выбирает fish
- Fish card показывается в MiniApp
- Animation или transition effect
- Telegram notification с результатом
- CTA: [Cast Again]

**Edge Cases:**
- Network delay: loading indicator
- API error: retry option

---

### 5.11 Live P&L updates (если реализовано)

**Preconditions:**
- Активная позиция
- MiniApp открыт на fishing state

**Steps:**
1. Подождать несколько секунд
2. GET /api/crypto-price/{symbol} периодически

**Expected Results:**
- P&L обновляется real-time
- Color changes (green/red)
- Smooth transitions

**Edge Cases:**
- Price API down: показывать last known price
- WebSocket alternative: push updates

---

### 5.12 Skeleton loaders

**Preconditions:**
- MiniApp делает API call
- Данные еще не загружены

**Steps:**
1. Наблюдать skeleton animations

**Expected Results:**
- Animated loading placeholders
- Сохраняют layout (no layout shift)
- Smooth transition к реальным данным
- Исчезают после загрузки

**Edge Cases:**
- Very slow API: показывать timeout message после 10s

---

### 5.13 Bunny CDN image delivery

**Preconditions:**
- Fish images хранятся на Bunny CDN
- GET /api/fish/{fish_id}/image возвращает CDN URL

**Steps:**
1. Загрузить fish collection
2. Изображения загружаются с CDN

**Expected Results:**
- Быстрая загрузка (edge cache)
- Automatic optimization (WebP, etc)
- Lazy loading для offscreen images

**Edge Cases:**
- CDN unavailable: fallback to direct API
- Image 404: placeholder image

---

### 5.14 Responsive design

**Preconditions:**
- MiniApp открыт на разных устройствах

**Steps:**
1. Открыть на маленьком экране (iPhone SE)
2. Открыть на большом экране (iPad)

**Expected Results:**
- Layout адаптируется
- Все элементы accessible
- No horizontal scroll
- Touch-friendly buttons

**Edge Cases:**
- Very small screen: scrollable content
- Landscape mode: alternative layout

---

### 5.15 Error handling в MiniApp

**Preconditions:**
- API возвращает errors

**Steps:**
1. Симулировать network error
2. Симулировать 500 error

**Expected Results:**
- Toast notifications с ошибками
- Retry buttons
- Graceful degradation
- Не ломается вся страница

**Edge Cases:**
- Multiple errors: показывать в очереди
- Fatal error: reload page option

---

## 6. Лидерборды

### 6.1 Общий лидерборд (/leaderboard)

**Preconditions:**
- Несколько пользователей ловили рыбу

**Steps:**
1. Отправить `/leaderboard` (без параметров)

**Expected Results:**
- Топ-10 игроков по виртуальному балансу
- Для каждого:
  - Rank (#1-10)
  - Username
  - Balance
  - Total catches
  - Win rate (%)
- Если user в топ-10: highlighted
- Если нет: показать "Your rank: #X"

**Edge Cases:**
- Только 1 игрок: показать только его
- User balance = 0: rank by catches

---

### 6.2 Недельный лидерборд

**Preconditions:**
- Есть рыбалка за последние 7 дней

**Steps:**
1. Отправить `/leaderboard week`

**Expected Results:**
- Топ-10 за последнюю неделю
- Сортировка по P&L за 7 дней
- Показывает только catches за этот период

**Edge Cases:**
- Нет catches за неделю: empty leaderboard
- New user: может быть в топе даже с 1 catch

---

### 6.3 Дневной лидерборд

**Preconditions:**
- Есть рыбалка за последние 24 часа

**Steps:**
1. Отправить `/leaderboard day`

**Expected Results:**
- Топ-10 за сегодня
- Сортировка по P&L за 24h

**Edge Cases:**
- Midnight rollover: корректное определение "дня"
- Timezone handling

---

### 6.4 Групповой лидерборд в приватном чате

**Preconditions:**
- Пользователь состоит в группе с group pond
- Команда `/leaderboard` в приватном чате

**Steps:**
1. Отправить `/leaderboard` в личном чате
2. Выбрать группу (если в нескольких)

**Expected Results:**
- Показывает ЛИЧНУЮ статистику пользователя
- Показывает его rank в глобальном лидерборде
- Может показывать stats для каждой группы отдельно

**Edge Cases:**
- В нескольких группах: показать tabs или список

---

### 6.5 Позиция пользователя в лидерборде

**Preconditions:**
- Пользователь вне топ-10

**Steps:**
1. Отправить `/leaderboard`

**Expected Results:**
- Топ-10 показан
- Внизу: "Your rank: #X"
- Показывает собственные stats (balance, catches)

**Edge Cases:**
- User rank > 1000: показывать корректно
- User has no catches: "Not ranked yet"

---

## 7. Quick Actions (кнопки)

### 7.1 Quick Cast button

**Preconditions:**
- CTA block показан с кнопкой [🎣 Cast Again]
- Пользователь в IDLE или CATCH_COMPLETE state

**Steps:**
1. Кликнуть [🎣 Cast Again]

**Expected Results:**
- Callback `quick_cast` обработан
- Старый CTA cleared
- /cast команда выполняется
- Pond selection показывается

**Edge Cases:**
- Double click: должен обработаться только один раз
- No BAIT: показать buy offer

---

### 7.2 Quick Hook button

**Preconditions:**
- ErrorBlock показан с кнопкой [🪝 Hook Now]
- Активная позиция существует

**Steps:**
1. Кликнуть [🪝 Hook Now]

**Expected Results:**
- Callback `quick_hook`
- /hook команда выполняется
- ErrorBlock cleared

**Edge Cases:**
- No active position: показать другую ошибку

---

### 7.3 Show Status button

**Preconditions:**
- ErrorBlock или CTA с кнопкой [📊 Check Status]

**Steps:**
1. Кликнуть [📊 Check Status]

**Expected Results:**
- Callback `show_status`
- /status команда выполняется
- CTA block cleared
- New InfoBlock/CTA с status

**Edge Cases:**
- Idle user: показать idle status CTA

---

### 7.4 Update Status button

**Preconditions:**
- Fishing в процессе
- InfoBlock показан с кнопкой [🔄 Update Status]

**Steps:**
1. Кликнуть [🔄 Update Status]

**Expected Results:**
- Callback `update_status`
- Текущий status обновляется (re-fetch price, recalculate P&L)
- InfoBlock обновляется с новыми данными

**Edge Cases:**
- Position just closed: показать appropriate message

---

### 7.5 Quick Buy button

**Preconditions:**
- ErrorBlock с кнопкой [💰 Buy BAIT]
- User out of BAIT

**Steps:**
1. Кликнуть [💰 Buy BAIT]

**Expected Results:**
- Callback `quick_buy`
- /buy команда выполняется
- Product selection показывается

**Edge Cases:**
- Payment cancelled: return to previous state

---

### 7.6 Quick PnL button

**Preconditions:**
- CTA с кнопкой [📊 My P&L]

**Steps:**
1. Кликнуть [📊 My P&L]

**Expected Results:**
- Callback `quick_pnl`
- /pnl команда выполняется
- Статистика показывается

**Edge Cases:**
- No catches yet: показать empty stats

---

### 7.7 Quick Help button

**Preconditions:**
- CTA с кнопкой [❓ Help]

**Steps:**
1. Кликнуть [❓ Help]

**Expected Results:**
- Callback `quick_help`
- /help команда выполняется
- Help message с инструкциями

**Edge Cases:**
- New user: может показать onboarding option

---

### 7.8 Cancel Action button

**Preconditions:**
- CTA/ErrorBlock с кнопкой [❌ Cancel]

**Steps:**
1. Кликнуть [❌ Cancel]

**Expected Results:**
- Callback `cancel_action`
- CTA block cleared (buttons removed)
- Neutral message или просто очистка

**Edge Cases:**
- No previous message to cancel: silent fail

---

### 7.9 Multiple button presses

**Preconditions:**
- CTA block показан с несколькими кнопками

**Steps:**
1. Быстро нажать несколько кнопок подряд

**Expected Results:**
- Только первое нажатие обрабатывается
- Остальные игнорируются или показывают "Action in progress"
- Telegram callback answering предотвращает duplicates

**Edge Cases:**
- Race condition: state machine должен предотвратить invalid transitions

---

### 7.10 Button callback errors

**Preconditions:**
- Callback handler выбрасывает exception

**Steps:**
1. Кликнуть кнопку, которая вызовет ошибку

**Expected Results:**
- Exception logged
- User видит error toast/message
- CTA не ломается
- Можно попробовать снова

**Edge Cases:**
- Database unavailable: показать retry option

---

## 8. UI System & States

### 8.1 CTA Block после успешного hook

**Preconditions:**
- Рыба поймана
- hook завершен успешно

**Steps:**
1. Наблюдать UI после hook

**Expected Results:**
- CTA Block показан с:
  - Header: "🎉 Great Catch!" (или подобное)
  - Body: описание результата
  - Buttons: [📢 Share] [🎣 Cast Again] (или только Cast для solo)
  - Footer: optional tip
- Предыдущие CTA cleared

**Edge Cases:**
- Group pond: Share button присутствует
- Solo pond: Share button отсутствует

---

### 8.2 Error Block при попытке cast с активной позицией

**Preconditions:**
- Активная позиция существует

**Steps:**
1. Попытаться /cast

**Expected Results:**
- ErrorBlock:
  - Header: "❌ Already Fishing!"
  - Body: explanation
  - Buttons: [🪝 Hook Now] [📊 Status]
- Red/warning styling (если применимо)

**Edge Cases:**
- Multiple error conditions: приоритизация

---

### 8.3 InfoBlock для status во время fishing

**Preconditions:**
- Fishing в процессе

**Steps:**
1. Команда /status

**Expected Results:**
- InfoBlock (без главных action buttons):
  - Body: current P&L, time, rod info
  - Footer: "Pro tip: Use /hook to complete"
- Не CTA, так как основное действие - /hook через команду

**Edge Cases:**
- Может иметь [🔄 Update] button

---

### 8.4 Animation → CTA transition

**Preconditions:**
- Animation (cast или hook) в процессе

**Steps:**
1. Дождаться завершения анимации
2. Наблюдать transition

**Expected Results:**
- Animation message редактируется финальным шагом
- Затем новый CTA block отправляется
- Smooth transition, без задержек
- Старая анимация не удаляется (остается в истории)

**Edge Cases:**
- Animation fail: все равно показать CTA
- Network delay: пользователь не должен ждать долго

---

### 8.5 State machine: IDLE → FISHING → CATCH_COMPLETE

**Preconditions:**
- Пользователь в IDLE state

**Steps:**
1. /cast → POND_SELECTION → CASTING → FISHING
2. /hook → HOOKING → CATCH_COMPLETE
3. Click Cast Again → IDLE

**Expected Results:**
- Все transitions валидны
- State correctly записан в context.user_data
- Invalid transitions blocked

**Edge Cases:**
- Пытаться перейти в invalid state: exception или block

---

### 8.6 State machine: NO_BAIT state

**Preconditions:**
- bait_tokens = 0

**Steps:**
1. Попытаться /cast
2. State → NO_BAIT

**Expected Results:**
- ErrorBlock с buy options
- После покупки: state → IDLE
- Can cast после восстановления BAIT

**Edge Cases:**
- BAIT восстановлен другим способом (reward): state transition work

---

### 8.7 Only one active CTA at a time

**Preconditions:**
- CTA block активен

**Steps:**
1. Вызвать другую команду, которая показывает новый CTA
2. Проверить, что старый CTA cleared

**Expected Results:**
- ViewController tracks active_cta_message_id
- Перед показом нового CTA: старый buttons removed
- Только один набор buttons активен

**Edge Cases:**
- Очень быстрые команды: race condition handling

---

### 8.8 State persistence across bot restarts

**Preconditions:**
- Пользователь в FISHING state
- Бот перезапускается

**Steps:**
1. Restart bot
2. Пользователь отправляет команду

**Expected Results:**
- State восстанавливается из БД (если используется persistence)
- Активная позиция остается валидной
- User может продолжить с /hook

**Edge Cases:**
- Persistence не настроено: state сбрасывается (приемлемо, так как position в БД)

---

## 9. Система прогрессии

### 9.1 Получение опыта за рыбалку

**Preconditions:**
- Пользователь поймал рыбу

**Steps:**
1. Завершить /hook

**Expected Results:**
- experience += calculated amount (зависит от fish rarity/P&L)
- Запись обновлена в БД
- Notification: "+X XP"

**Edge Cases:**
- Negative P&L: все равно получить XP (меньше)
- Max level reached: XP не растет

---

### 9.2 Level up

**Preconditions:**
- experience >= next_level_threshold

**Steps:**
1. Catch fish, gain XP
2. Threshold превышен

**Expected Results:**
- level += 1
- experience reset или overflow на следующий уровень
- Congratulations message: "🎉 Level Up! Now level {level}"
- Может разблокировать новые ponds/rods

**Edge Cases:**
- Multiple levels в одном catch: обработать корректно

---

### 9.3 Разблокировка прудов по уровню

**Preconditions:**
- Pond требует level > current_level

**Steps:**
1. Reach required level
2. Проверить /cast pond list

**Expected Results:**
- Новый pond появляется в списке
- Notification о разблокировке (optional)

**Edge Cases:**
- Multiple ponds unlock одновременно

---

### 9.4 Разблокировка удочек

**Preconditions:**
- User level увеличился
- Новая удочка доступна

**Steps:**
1. Level up
2. Автоматическая разблокировка или purchase

**Expected Results:**
- Новая удочка в user_rods
- Показывается в MiniApp rods screen

**Edge Cases:**
- Starter rod всегда доступна

---

### 9.5 Виртуальный баланс calculation

**Preconditions:**
- User имеет catches

**Steps:**
1. Запросить /pnl или GET /api/user/{id}/balance

**Expected Results:**
- Formula: balance = 10000 + SUM(1000 * pnl_percent / 100)
- Корректный расчет всех P&L
- Отображение с $ и decimal places

**Edge Cases:**
- No catches: balance = $10,000
- Negative P&L sum: balance < $10,000
- Very high P&L: balance can go very high

---

### 9.6 Progression stats (/pnl command)

**Preconditions:**
- User имеет history

**Steps:**
1. Отправить /pnl

**Expected Results:**
- Полная статистика:
  - Current balance
  - Total catches
  - Win rate %
  - Average P&L per catch
  - Best catch (max P&L)
  - Worst catch
  - Total profit/loss
- Formatted красиво с emoji и colors

**Edge Cases:**
- No catches: показать initial balance и "No catches yet"

---

## 10. API Endpoints

### 10.1 GET /api/user/{user_id}

**Preconditions:**
- User exists в БД

**Steps:**
1. GET /api/user/123456789

**Expected Results:**
- 200 OK
- JSON response:
  ```json
  {
    "id": 123456789,
    "username": "player1",
    "level": 5,
    "experience": 240,
    "bait_tokens": 15,
    "created_at": "2025-01-15T10:30:00Z"
  }
  ```

**Edge Cases:**
- User not found: 404 с error message
- Invalid user_id: 400 Bad Request

---

### 10.2 GET /api/user/{user_id}/stats

**Preconditions:**
- User exists

**Steps:**
1. GET /api/user/123/stats

**Expected Results:**
- 200 OK
- Extended stats:
  - User info
  - Total catches
  - Unique fish count
  - Active rods
  - Current balance

**Edge Cases:**
- New user: stats with zeros

---

### 10.3 GET /api/user/{user_id}/fish

**Preconditions:**
- User caught fish

**Steps:**
1. GET /api/user/123/fish

**Expected Results:**
- 200 OK
- Array of fish:
  ```json
  [
    {
      "id": 1,
      "name": "Golden Dragon",
      "emoji": "🐉",
      "rarity": "legendary",
      "pnl_percent": 150.5,
      "caught_at": "2025-01-15T12:00:00Z",
      "image_url": "https://cdn.bunny.net/..."
    }
  ]
  ```

**Edge Cases:**
- No fish: empty array []
- Pagination: implement if needed

---

### 10.4 GET /api/user/{user_id}/rods

**Preconditions:**
- User has rods (at least starter)

**Steps:**
1. GET /api/user/123/rods

**Expected Results:**
- 200 OK
- Array of rods:
  ```json
  [
    {
      "id": 1,
      "name": "Grandfather's Rod",
      "leverage": 2.0,
      "rod_type": "long",
      "rarity": "common",
      "is_active": true
    }
  ]
  ```

**Edge Cases:**
- No rods: should not happen (starter rod)

---

### 10.5 GET /api/user/{user_id}/active-rod

**Preconditions:**
- User has active rod set

**Steps:**
1. GET /api/user/123/active-rod

**Expected Results:**
- 200 OK
- Single rod object (active one)

**Edge Cases:**
- No active rod: return default or error

---

### 10.6 POST /api/user/{user_id}/active-rod

**Preconditions:**
- User owns the rod

**Steps:**
1. POST /api/user/123/active-rod
   ```json
   {"rod_id": 2}
   ```

**Expected Results:**
- 200 OK
- user_settings updated
- Response: {"success": true, "active_rod_id": 2}

**Edge Cases:**
- Rod not owned: 403 Forbidden
- Invalid rod_id: 400 Bad Request

---

### 10.7 GET /api/fish/{fish_id}/image

**Preconditions:**
- Fish exists
- Image cached в БД или CDN

**Steps:**
1. GET /api/fish/42/image

**Expected Results:**
- 302 Redirect to Bunny CDN URL
- Or 200 OK with image data

**Edge Cases:**
- Image not generated yet: generate on-demand
- CDN unavailable: serve from local cache

---

### 10.8 POST /api/user/{user_id}/claim-inheritance

**Preconditions:**
- New user, inheritance_claimed = false

**Steps:**
1. POST /api/user/123/claim-inheritance

**Expected Results:**
- 200 OK
- inheritance_claimed = true
- bait_tokens += 10
- Response: {"success": true, "bait_added": 10}

**Edge Cases:**
- Already claimed: 400 "Already claimed"
- Idempotency: повторный request не дает BAIT дважды

---

### 10.9 GET /api/user/{user_id}/inheritance-status

**Preconditions:**
- User exists

**Steps:**
1. GET /api/user/123/inheritance-status

**Expected Results:**
- 200 OK
- {"inheritance_claimed": true/false}

**Edge Cases:**
- New user: false

---

### 10.10 GET /api/user/{user_id}/balance

**Preconditions:**
- User exists

**Steps:**
1. GET /api/user/123/balance

**Expected Results:**
- 200 OK
- ```json
  {
    "balance": 11500.50,
    "total_pnl": 1500.50,
    "catch_count": 15
  }
  ```

**Edge Cases:**
- No catches: balance = 10000, pnl = 0

---

### 10.11 GET /api/leaderboard

**Preconditions:**
- Multiple users exist

**Steps:**
1. GET /api/leaderboard?period=all

**Expected Results:**
- 200 OK
- Array of top 10 users with stats

**Edge Cases:**
- period=week: filter by last 7 days
- period=day: filter by last 24h

---

### 10.12 GET /api/user/{user_id}/ponds

**Preconditions:**
- Ponds exist для user level

**Steps:**
1. GET /api/user/123/ponds

**Expected Results:**
- 200 OK
- Array of available ponds (unlocked by level + group ponds)

**Edge Cases:**
- No ponds available: should not happen (default pond)

---

### 10.13 POST /api/user/{user_id}/cast

**Preconditions:**
- User has BAIT
- No active position

**Steps:**
1. POST /api/user/123/cast
   ```json
   {"pond_id": 1}
   ```

**Expected Results:**
- 200 OK
- Position created
- BAIT -= 1
- Response: {"position_id": 42, "entry_price": 1.234}

**Edge Cases:**
- No BAIT: 400 "Insufficient BAIT"
- Already fishing: 409 Conflict

---

### 10.14 POST /api/user/{user_id}/hook

**Preconditions:**
- Active position exists

**Steps:**
1. POST /api/user/123/hook

**Expected Results:**
- 200 OK
- Position closed
- Fish selected
- Response: full fish catch details

**Edge Cases:**
- No position: 400 "No active position"
- Price fetch fail: retry logic

---

## Дополнительные сценарии для рассмотрения

### Edge Cases & Error Handling

1. **Network failures** - retry logic, timeout handling
2. **Database unavailable** - graceful degradation
3. **Concurrent requests** - race conditions
4. **Rate limiting** - 10 commands/min enforcement
5. **Invalid user input** - validation и error messages
6. **Bot permissions** - handling removed bot, no permissions
7. **Telegram API errors** - flood control, message too long

### Performance

1. **High load** - connection pooling, async processing
2. **Many concurrent users** - semaphore limits (AI generation)
3. **Large leaderboards** - pagination
4. **Image loading** - CDN performance, lazy loading

### Security

1. **Payment validation** - amount verification, idempotency
2. **User authorization** - can't modify other users' data
3. **API authentication** - Telegram WebApp validation
4. **SQL injection** - parameterized queries (asyncpg)

---

## Как использовать этот документ

### Для тестировщиков:
1. Пройти все сценарии последовательно
2. Отмечать PASS/FAIL для каждого
3. Документировать найденные баги с reference на номер сценария

### Для разработчиков:
1. Использовать как checklist при реализации features
2. Писать unit tests для edge cases
3. Обновлять документ при добавлении нового функционала

### Приоритеты тестирования:
- **P0 (Critical)**: Базовая рыбалка (1.1-1.8), платежи (3.1-3.6)
- **P1 (High)**: Онбординг (2.1-2.7), MiniApp core (5.1-5.10)
- **P2 (Medium)**: Групповые функции, UI system
- **P3 (Low)**: Edge cases, performance tests

---

**Конец документа**
Для вопросов или дополнений обращайтесь к команде разработки.
