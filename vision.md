# 🎣 Crypto Fishing - Игровая концепция и токеномика

## 🎮 **Общая концепция**

### **Игровая метафора:**
Пользователь = рыбак, который делает ставки на криптовалютные движения через интуитивную механику рыбалки. Каждый "заброс удочки" = leveraged позиция на реальном рынке, результат которой определяет какую "рыбу" поймает игрок.

### **Core Loop:**
```
1. Выбираешь снасти (leverage + пара)
2. Закидываешь удочку (открываешь позицию)  
3. Ждешь поклевку (наблюдаешь за ценой)
4. Подсекаешь (закрываешь позицию)
5. Получаешь рыбу NFT (результат торговли)
6. Продаешь рыбу за новые снасти
```

---

## 🎣 **Игровая механика**
### **MiniApp:**
Играть можно в боте и в Telegram MiniApp. В TMA доступны дополнительные игровые механики и косметика.

### **Процесс рыбалки:**
```
🎣 FISHING SETUP
┌─────────────────────────────────┐
│ Водоем: TAC Lake 🏞️            │
│ Leverage: [2x] [5x] [10x] [20x] │
│ Требуется: 1 🦐 PREMIUM_BAIT    │
│ Ваши снасти: 🪱×15 🦐×3 🐠×1    │
│                                 │
│ Прогноз: 🌊 Высокая волатильность│
│ Время суток: 🌅 Bull Hour       │
│                                 │
│ [🎣 ЗАБРОСИТЬ УДОЧКУ]           │
└─────────────────────────────────┘
```

### **Фаза ожидания:**
```
🎣 РЫБАЛКА В ПРОЦЕССЕ...
┌─────────────────────────────────┐
│      🌊🌊🌊🌊🌊🌊🌊             │
│     🌊             🌊           │
│    🌊     🎣        🌊          │
│   🌊       |         🌊         │
│  🌊     🐟  |  🦈     🌊        │
│ 🌊         👤        🌊         │
│                                 │
│ Глубина: 127m (-5.2% PnL) 📉    │
│ Время в воде: 1m 34s ⏰         │
│ Активность: Средняя 📊          │
│                                 │
│ [🐟 ПОДСЕЧЬ СЕЙЧАС] [⏰ ЖДАТЬ]  │
└─────────────────────────────────┘
```

### **Результат:**
```
🎉 ПОЙМАЛИ РЫБУ!
┌─────────────────────────────────┐
│         🐠 TROPICAL FISH        │
│                                 │
│ Стоимость: $34.50 (+72.5% ROI)  │
│ Редкость: Uncommon 🟡           │
│ Время ловли: 2m 17s             │
│ Leverage: 5x TAC/USDT           │
│                                 │
│ [🛒 ПРОДАТЬ] [💎 ОСТАВИТЬ]      │
│ [🎣 ЛОВИТЬ ЕЩЕ] [📊 СТАТИСТИКА] │
└─────────────────────────────────┘
```

---

## 🪙 **Токеномика**

### **Два основных токена:**

#### **🎣 BAIT Token (ERC-20)**
```
Назначение: Расходуемый ресурс для доступа к leverage
Механика: Burn-to-play модель

Типы наживки:
🪱 BASIC_BAIT    → 2x leverage доступ
🦐 PREMIUM_BAIT  → 5x leverage доступ  
🐠 RARE_BAIT     → 10x leverage доступ
🦑 LEGENDARY_BAIT → 20x leverage + эксклюзивные пары
```

#### **🐟 FISH NFT (ERC-721)**
```
Назначение: Результат рыбалки, торгуемый актив
Механика: Mint-on-success модель

Виды рыб (по результату торговли):
💀 Old Boot     → Loss (-100%)      → Мусор
🐟 Small Fish   → +5-20% profit     → 5 BASIC_BAIT
🐠 Tropical Fish → +20-50% profit   → 15 PREMIUM_BAIT
🦈 Shark        → +50-100% profit   → 50 RARE_BAIT  
🐋 Whale        → +100-300% profit  → 150 RARE_BAIT
🐙 Kraken       → +300%+ profit     → 500 LEGENDARY_BAIT
```

### **Token Flow:**
```
BAIT Acquisition:
💰 Purchase: $1 = 5 BASIC_BAIT
🎁 Daily login: 3 BASIC_BAIT
🏆 First win: 1 PREMIUM_BAIT
👥 Referral: 10 PREMIUM_BAIT per friend
🛒 Sell FISH NFT: Variable BAIT amount

BAIT Consumption:
🎣 Each fishing session burns corresponding BAIT
🔥 Burn rate = Leverage level requirement

FISH Generation:
🐟 Minted upon closing profitable position
💀 Minted even on losses (Old Boot)
🎯 Rarity based on % profit achieved
```

---

## 📊 **Транзакционная структура**

### **Одна игровая сессия:**

#### **Подготовка к рыбалке:**
```
1. Buy BAIT (если нужно) → 1 tx
   - User покупает недостающие BAIT токены
   - Payment → BAIT tokens mint
```

#### **Начало рыбалки:**
```
2. Burn BAIT + Open position → 2 tx
   - Burn required BAIT tokens → 1 tx
   - Open leveraged position on DEX → 1 tx
```

#### **Завершение рыбалки:**
```
3. Close position + Mint FISH → 2 tx  
   - Close leveraged position on DEX → 1 tx
   - Mint FISH NFT with result → 1 tx
```

#### **Опциональные действия:**
```
4a. Sell FISH NFT → 1 tx
    - List on marketplace or instant sell
    
4b. Buy more BAIT → 1 tx
    - Convert earnings to new BAIT
    
4c. Next fishing session → повтор цикла
```

### **Транзакции за сессию:**
```
Базовый цикл: 4-5 транзакций
├─ Обязательные: 4 tx (burn, open, close, mint)
├─ Покупка BAIT: +1 tx (если нужно)
└─ Продажа FISH: +1 tx (опционально)

Средний показатель: 5 транзакций на игровую сессию
```

---

## 🏊 **Виды водоемов (торговые пары)**

### **Доступные локации:**
```
🏞️ TAC Lake (TAC/USDT)
├─ Волатильность: Средняя
├─ Рыба: Классические виды
└─ Leverage: до 20x

🌊 BTC Ocean (BTC/USDT)  
├─ Волатильность: Умеренная
├─ Рыба: Крупные хищники
└─ Leverage: до 10x

🔥 Altcoin Rapids (SOL/USDT)
├─ Волатильность: Высокая  
├─ Рыба: Экзотические виды
└─ Leverage: до 25x

💀 Meme Swamp (DOGE/USDT)
├─ Волатильность: Экстремальная
├─ Рыба: Мутанты и легенды  
└─ Leverage: до 50x

👑 Whale Sanctuary (только для VIP)
├─ Волатильность: Переменная
├─ Рыба: Эксклюзивные виды
└─ Leverage: до 100x
```

---

## 💰 **Экономическая модель**

### **Revenue Streams:**
```
💸 BAIT Token Sales:
├─ Direct purchase: $1 = 5 BASIC_BAIT
├─ Booster packs: $5, $10, $25 bundles
├─ VIP subscription: $20/month unlimited BASIC_BAIT
└─ Tournament entries: Premium BAIT cost

🏪 Marketplace Fees:
├─ FISH NFT trading: 5% platform fee
├─ BAIT token trading: 3% platform fee  
└─ Rare fish auctions: 10% platform fee

🎮 Premium Features:
├─ Advanced fishing tools: $15/month
├─ Exclusive waterways: $10 access
├─ Fishing insurance: $3 per session
└─ Auto-fishing bot: $25/month
```

### **Token Economy Balance:**
```
📈 BAIT Token Pressure:
Supply: Daily login, FISH sales, purchases
Demand: Every fishing session burns BAIT
Balance: Burning rate = 60-70% of generation

📊 FISH NFT Circulation:
Generation: Every fishing session creates 1 NFT
Destruction: Old Boots can be burned for small BAIT
Trading: Active marketplace with rarity premiums
```

---

## 📈 **Projected Transaction Volume**

### **Player Activity Assumptions:**
```
🎯 Active Player Profile:
├─ 3-5 fishing sessions per day
├─ 2-3 FISH NFT sales per week  
├─ 1-2 BAIT purchases per week
└─ 20 days active per month

📊 Transaction Breakdown per Active Player/Day:
├─ Fishing sessions: 4 sessions × 5 tx = 20 tx
├─ BAIT purchases: 0.3 × 1 tx = 0.3 tx
├─ FISH sales: 0.4 × 1 tx = 0.4 tx
└─ Total: ~21 transactions per player per day
```

### **Scaling Projections:**
```
📅 Daily Metrics:
├─ 100 players: 2,100 transactions/day
├─ 500 players: 10,500 transactions/day  
├─ 1,000 players: 21,000 transactions/day
├─ 5,000 players: 105,000 transactions/day
└─ 10,000 players: 210,000 transactions/day

📈 Monthly Metrics (1,000 active players):
├─ Base transactions: 630,000 tx/month
├─ Marketplace activity: +150,000 tx/month
├─ Social features: +50,000 tx/month
└─ Total: ~830,000 transactions/month

🚀 Annual Projection (5,000 avg players):
~12.5 million transactions per year
```

---

## 🎯 **Success Metrics**

### **Engagement KPIs:**
```
🎮 Gameplay:
├─ Average sessions per player per day: 3-5
├─ Session duration: 2-4 minutes
├─ Player retention: 70% day 7, 40% day 30
└─ Average profit per session: +15-25%

💰 Economic:
├─ BAIT purchase conversion: 30% of players
├─ FISH NFT trading volume: $10k+/day
├─ Average revenue per user: $15/month
└─ Transaction fee revenue: $500+/day

🔗 Network:
├─ Daily transactions: 20,000+
├─ Unique daily addresses: 1,000+
├─ Gas fee contribution: $2,000+/day
└─ Smart contract interactions: 95%+ success rate
```

Эта модель обеспечивает **высокую on-chain активность** через **простой и понятный** игровой процесс с **устойчивой экономикой**! 🎣💰