# 🧪 Test Scenarios - Fishing Bot

Краткий каталог тестовых сценариев для Telegram бота виртуальной рыбалки.

**Версия:** 2.0
**Всего сценариев:** 87

---

## 1. Базовая рыбалка (8 сценариев)

**1.1 Первый заброс новым пользователем**
Новый пользователь выполняет /cast, выбирает пруд из списка, видит анимацию заброса (3 шага), тратит 1 BAIT токен, создается активная позиция.

**1.2 Выбор пруда (pond selection)**
После команды /cast пользователь видит список доступных прудов, выбирает один, начинается анимация заброса с выбранной торговой парой.

**1.3 Анимация заброса (casting animation)**
После выбора пруда показывается 3-шаговая анимация с редактированием сообщения (~2 сек между шагами), заканчивается текстом "Now we wait...".

**1.4 Проверка статуса во время рыбалки**
Команда /status во время активной позиции показывает InfoBlock с текущим P&L, временем в воде, удочкой и leverage.

**1.5 Подсечка рыбы (hook)**
Команда /hook запускает анимацию подсечки (3 шага), параллельно получает цену и генерирует рыбью карточку, показывает результат с P&L и кнопками действий.

**1.6 Повторный заброс после подсечки**
После завершения рыбалки кнопка [Cast Again] или /cast начинают новый цикл заброса с pond selection.

**1.7 Попытка заброса с активной позицией**
При попытке /cast с активной позицией показывается ErrorBlock с кнопками [Hook Now] и [Check Status].

**1.8 Попытка подсечки без заброса**
Команда /hook без активной позиции показывает ошибку с кнопкой [Start Fishing].

---

## 2. Онбординг (7 сценариев)

**2.1 Первый запуск /start**
Создание нового пользователя в БД с начальными параметрами (5-10 BAIT, level 1), отправка приветственного сообщения с кнопками [Start Tutorial] и [Skip].

**2.2 Прохождение tutorial - Intro step**
Нажатие [Start Tutorial] переводит на следующий шаг онбординга с объяснением механики.

**2.3 Join Group step**
Предложение вступить в группу с invite link, при вступлении дается бонус (+5 BAIT).

**2.4 Cast instruction step**
Инструкция по использованию /cast с кнопкой [Try First Cast], которая запускает реальную команду заброса.

**2.5 Hook instruction step**
После первого cast показывается инструкция по /hook с кнопкой [Complete First Catch], после успешного hook онбординг завершается.

**2.6 Skip onboarding**
Кнопка [Skip] или команда /skip пропускает онбординг, помечает как completed, дает доступ ко всем командам.

**2.7 Claim Inheritance (MiniApp)**
При первом открытии MiniApp новый пользователь видит письмо от дедушки, нажимает [Accept Inheritance], получает +10 BAIT и дедушкину удочку.

---

## 3. Платежи (Telegram Stars) (6 сценариев)

**3.1 Покупка BAIT - Small Pack (10 tokens)**
Команда /buy или кнопка [Buy BAIT], выбор пакета "10 BAIT - ⭐100 Stars", оплата через Telegram Stars, получение токенов.

**3.2 Покупка BAIT - Medium Pack (50 tokens)**
Покупка среднего пакета "50 BAIT - ⭐450 Stars (BEST VALUE)" с лучшим соотношением цены.

**3.3 Покупка BAIT - Large Pack (100 tokens)**
Покупка большого пакета "100 BAIT - ⭐800 Stars (Save 20%)" с максимальной скидкой.

**3.4 Автоматическое предложение при BAIT = 0**
При попытке /cast с нулевым балансом BAIT показывается ErrorBlock с тремя пакетами для покупки.

**3.5 Просмотр истории транзакций**
Команда /transactions показывает список всех покупок с датой, продуктом, количеством BAIT, ценой и статусом.

**3.6 Purchase через MiniApp**
Клик на BAIT balance в MiniApp открывает payment modal, позволяет купить BAIT через Telegram payment flow.

---

## 4. Групповые функции (8 сценариев)

**4.1 Добавление бота в группу**
Добавление бота в группу, обработка события ChatMemberHandler, отправка welcome message, создание записи group pond.

**4.2 Создание группового пруда**
Автоматическое создание pond при добавлении бота в группу с названием "{Group Name} Fishing Spot" и дефолтной торговой парой.

**4.3 /gofishing команда в группе**
Команда /gofishing в группе публикует приглашение на рыбалку с кнопкой [Join Fishing!] для всех участников.

**4.4 Присоединение к групповой рыбалке**
Клик на [Join Fishing!] обрабатывается в приватном чате пользователя, проверяется BAIT, начинается cast в выбранный group pond.

**4.5 Share cast в группе**
После заброса в групповом пруду кнопка [Share Cast] публикует сообщение в группу о начале рыбалки с информацией о leveraged position.

**4.6 Share hook результата в группе**
После успешного hook в групповом пруду кнопка [Share in Group] публикует fish card и результат P&L, дает +1 BAIT за sharing.

**4.7 Групповой лидерборд**
Команда /leaderboard в группе показывает топ-10 участников этой группы с публичными данными (username, balance), без личной информации.

**4.8 Tracking group members**
ChatMemberHandler отслеживает присоединение/уход участников, обновляет member list, опционально отправляет welcome message.

---

## 5. MiniApp интерфейс (15 сценариев)

**5.1 Открытие MiniApp - первый запуск**
Новый пользователь (inheritance_claimed = false) открывает MiniApp, видит inheritance screen с письмом от дедушки вместо lobby.

**5.2 Открытие MiniApp - returning user**
Пользователь с inheritance_claimed = true видит lobby screen с fisherman avatar, статистикой, BAIT balance и navigation tabs.

**5.3 Lobby screen - просмотр статистики**
Lobby отображает character image, level/XP, BAIT balance (clickable), виртуальный баланс, active rod indicator и tabs для навигации.

**5.4 Просмотр коллекции рыб**
Tab [Fish] показывает grid с рыбьими карточками (image, emoji, name, rarity badge, P&L) со skeleton loaders до загрузки.

**5.5 Fish details modal**
Клик на рыбу открывает modal с full-size изображением, description/story, trading info, rod/leverage, pond name, timestamp поимки.

**5.6 Rod selection screen**
Tab [Rods] показывает carousel/grid с доступными удочками (SVG image, name, leverage, rod type, rarity), active rod highlighted.

**5.7 Изменение активной удочки**
Выбор неактивной удочки и клик [Set Active] отправляет POST /api/user/{user_id}/active-rod, обновляет UI с toast notification.

**5.8 Leaderboard в MiniApp**
Tab [Leaderboard] показывает топ-10 игроков с rank, username, level badge, balance, подсвечивает текущего пользователя.

**5.9 Casting через MiniApp**
Кнопка [Cast] на lobby открывает pond selection, после выбора POST /api/user/{user_id}/cast создает позицию, показывает fishing state.

**5.10 Hooking через MiniApp**
В fishing state кнопка [Hook] отправляет POST /api/user/{user_id}/hook, показывает fish card с animation, отправляет Telegram notification.

**5.11 Live P&L updates**
При активной позиции периодический GET /api/crypto-price/{symbol} обновляет P&L real-time с цветовыми индикаторами и smooth transitions.

**5.12 Skeleton loaders**
Во время API calls показываются animated loading placeholders, сохраняющие layout, плавно переходят к реальным данным.

**5.13 Bunny CDN image delivery**
Fish images загружаются с Bunny CDN с automatic optimization (WebP), edge cache, lazy loading для offscreen images.

**5.14 Responsive design**
MiniApp адаптируется под разные размеры экранов (iPhone SE, iPad), без horizontal scroll, с touch-friendly buttons.

**5.15 Error handling в MiniApp**
При API errors показываются toast notifications с retry buttons, graceful degradation без поломки всей страницы.

---

## 6. Лидерборды (5 сценариев)

**6.1 Общий лидерборд (/leaderboard)**
Команда /leaderboard показывает топ-10 по виртуальному балансу с rank, username, balance, total catches, win rate, позицией текущего пользователя.

**6.2 Недельный лидерборд**
Команда /leaderboard week показывает топ-10 за последнюю неделю, сортировка по P&L за 7 дней.

**6.3 Дневной лидерборд**
Команда /leaderboard day показывает топ-10 за последние 24 часа, сортировка по P&L за день.

**6.4 Групповой лидерборд в приватном чате**
Команда /leaderboard в личном чате показывает личную статистику пользователя и его rank в глобальном лидерборде.

**6.5 Позиция пользователя в лидерборде**
Для пользователей вне топ-10 показывается "Your rank: #X" с собственными stats (balance, catches).

---

## 7. Quick Actions (кнопки) (10 сценариев)

**7.1 Quick Cast button**
Кнопка [Cast Again] в CTA block вызывает callback quick_cast, очищает старый CTA, запускает команду /cast с pond selection.

**7.2 Quick Hook button**
Кнопка [Hook Now] в ErrorBlock вызывает callback quick_hook, выполняет команду /hook, очищает ErrorBlock.

**7.3 Show Status button**
Кнопка [Check Status] вызывает callback show_status, выполняет команду /status, очищает CTA, показывает новый InfoBlock.

**7.4 Update Status button**
Кнопка [Update Status] в InfoBlock вызывает callback update_status, обновляет текущий P&L с re-fetch price, обновляет InfoBlock.

**7.5 Quick Buy button**
Кнопка [Buy BAIT] в ErrorBlock вызывает callback quick_buy, выполняет команду /buy, показывает product selection.

**7.6 Quick PnL button**
Кнопка [My P&L] вызывает callback quick_pnl, выполняет команду /pnl, показывает статистику пользователя.

**7.7 Quick Help button**
Кнопка [Help] вызывает callback quick_help, выполняет команду /help, показывает help message с инструкциями.

**7.8 Cancel Action button**
Кнопка [Cancel] вызывает callback cancel_action, очищает CTA block (удаляет buttons), показывает нейтральное сообщение или просто очищает.

**7.9 Multiple button presses**
При быстром нажатии нескольких кнопок подряд обрабатывается только первое, остальные игнорируются через Telegram callback answering.

**7.10 Button callback errors**
При exception в callback handler ошибка логируется, пользователь видит error message, CTA не ломается, можно повторить действие.

---

## 8. UI System & States (8 сценариев)

**8.1 CTA Block после успешного hook**
После успешного hook показывается CTA Block с header "Great Catch!", описанием результата, кнопками [Share]/[Cast Again], optional footer tip.

**8.2 Error Block при попытке cast с активной позицией**
При попытке /cast с активной позицией показывается ErrorBlock с header "Already Fishing!", explanation, кнопками [Hook Now]/[Status].

**8.3 InfoBlock для status во время fishing**
При /status во время fishing показывается InfoBlock (без главных action buttons) с current P&L, time, rod info, footer hint.

**8.4 Animation → CTA transition**
После завершения animation (cast/hook) animation message редактируется финальным шагом, затем отправляется новый CTA block, smooth transition.

**8.5 State machine: IDLE → FISHING → CATCH_COMPLETE**
Корректные transitions через states: /cast → POND_SELECTION → CASTING → FISHING, /hook → HOOKING → CATCH_COMPLETE, Cast Again → IDLE.

**8.6 State machine: NO_BAIT state**
При bait_tokens = 0 и попытке /cast state переходит в NO_BAIT, показывается ErrorBlock с buy options, после покупки → IDLE.

**8.7 Only one active CTA at a time**
ViewController tracks active_cta_message_id, перед показом нового CTA старый buttons removed, только один набор buttons активен.

**8.8 State persistence across bot restarts**
При рестарте бота state восстанавливается из БД (если persistence настроен), активная позиция остается валидной, user может продолжить.

---

## 9. Система прогрессии (6 сценариев)

**9.1 Получение опыта за рыбалку**
После завершения /hook начисляется experience (зависит от fish rarity/P&L), обновляется запись в БД, показывается notification "+X XP".

**9.2 Level up**
При experience >= next_level_threshold происходит level += 1, experience reset/overflow, показывается congratulations message, разблокируются новые ponds/rods.

**9.3 Разблокировка прудов по уровню**
При достижении required level новый pond появляется в списке /cast, показывается notification о разблокировке.

**9.4 Разблокировка удочек**
При level up новые удочки добавляются в user_rods (автоматически или через purchase), показываются в MiniApp rods screen.

**9.5 Виртуальный баланс calculation**
Формула: balance = 10000 + SUM(1000 * pnl_percent / 100), корректный расчет всех P&L, отображение с $ и decimal places.

**9.6 Progression stats (/pnl command)**
Команда /pnl показывает полную статистику: current balance, total catches, win rate %, average P&L, best/worst catch, total profit/loss.

---

## Приоритеты тестирования

- **P0 (Critical)**: Базовая рыбалка (1.1-1.8), платежи (3.1-3.6)
- **P1 (High)**: Онбординг (2.1-2.7), MiniApp core (5.1-5.10)
- **P2 (Medium)**: Групповые функции (4.1-4.8), UI system (8.1-8.8)
- **P3 (Low)**: Quick actions (7.1-7.10), progression (9.1-9.6), API endpoints (10.1-10.14)

---

**Конец документа**
Для подробностей каждого сценария см. git history (версия 1.0) или обращайтесь к команде разработки.
