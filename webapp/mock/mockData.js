// Mock data for development without database connection

const mockData = {
  // Test user data
  users: {
    123456789: {
      id: 123456789,
      username: 'TestFisherman',
      level: 5,
      experience: 2500,
      bait_tokens: 10,
      created_at: '2024-01-15T10:00:00Z'
    }
  },

  // User statistics
  userStats: {
    123456789: {
      rods_count: 4,
      fish_caught: 15,
      fish_total: 87,
      fish_display: '15/87'
    }
  },

  // User balance data
  userBalance: {
    123456789: {
      balance: 12500,
      profit_loss: 2500,
      profit_loss_percent: 25.0,
      total_trades: 45,
      winning_trades: 28,
      win_rate: 62.22,
      avg_pnl: 2.8
    }
  },

  // Fish collection
  fishCollection: [
    {
      id: 1,
      name: 'Золотой Дракон',
      emoji: '🐉',
      description: 'Мифическая рыба с золотой чешуей',
      rarity: 'legendary',
      pnl_percent: 150.5,
      caught_at: '2024-03-10T14:30:00Z',
      rod_name: 'Титановая удочка',
      pond_name: 'Криптовые Воды',
      cdn_url: null,
      thumbnail_url: null
    },
    {
      id: 2,
      name: 'NFT-Обезьяна',
      emoji: '🐵',
      description: 'Скупила все NFT на распродаже',
      rarity: 'rare',
      pnl_percent: 45.2,
      caught_at: '2024-03-09T10:15:00Z',
      rod_name: 'Лонг удочка',
      pond_name: 'Озеро Профита',
      cdn_url: null,
      thumbnail_url: null
    },
    {
      id: 3,
      name: 'Скам-Лягушка',
      emoji: '🐸',
      description: 'Обещала 1000% APY',
      rarity: 'rare',
      pnl_percent: -35.7,
      caught_at: '2024-03-08T16:45:00Z',
      rod_name: 'Шорт удочка',
      pond_name: 'Море Волатильности',
      cdn_url: null,
      thumbnail_url: null
    },
    {
      id: 4,
      name: 'Деген-Русалка',
      emoji: '🧜‍♀️',
      description: 'Торгует с плечом 100x',
      rarity: 'epic',
      pnl_percent: 89.3,
      caught_at: '2024-03-07T12:00:00Z',
      rod_name: 'Эпическая удочка',
      pond_name: 'Лунные Пруды',
      cdn_url: null,
      thumbnail_url: null
    },
    {
      id: 5,
      name: 'Старый Сапог',
      emoji: '👢',
      description: 'Классический улов начинающего рыбака',
      rarity: 'trash',
      pnl_percent: -15.2,
      caught_at: '2024-03-06T09:30:00Z',
      rod_name: 'Стартовая удочка',
      pond_name: 'Криптовые Воды',
      cdn_url: null,
      thumbnail_url: null
    },
    {
      id: 6,
      name: 'Кибер-Карась',
      emoji: '🤖',
      description: 'Апгрейдил себя на блокчейне',
      rarity: 'common',
      pnl_percent: 12.8,
      caught_at: '2024-03-05T15:20:00Z',
      rod_name: 'Лонг удочка',
      pond_name: 'Вулканические Источники',
      cdn_url: null,
      thumbnail_url: null
    },
    {
      id: 7,
      name: 'Гопник Сомик',
      emoji: '🐟',
      description: 'Сидит на корточках, щелкает семечки',
      rarity: 'common',
      pnl_percent: 8.5,
      caught_at: '2024-03-04T11:10:00Z',
      rod_name: 'Шорт удочка',
      pond_name: 'Ледяные Глубины',
      cdn_url: null,
      thumbnail_url: null
    },
    {
      id: 8,
      name: 'Акула Профита',
      emoji: '🦈',
      description: 'Всегда в плюсе',
      rarity: 'epic',
      pnl_percent: 95.7,
      caught_at: '2024-03-03T14:45:00Z',
      rod_name: 'Титановая удочка',
      pond_name: 'Радужные Заводи',
      cdn_url: null,
      thumbnail_url: null
    },
    {
      id: 1,
      name: 'Золотой Дракон',
      emoji: '🐉',
      description: 'Мифическая рыба с золотой чешуей',
      rarity: 'legendary',
      pnl_percent: 125.3,
      caught_at: '2024-03-02T08:30:00Z',
      rod_name: 'Лонг удочка',
      pond_name: 'Горные Озёра',
      cdn_url: null,
      thumbnail_url: null
    },
    {
      id: 9,
      name: 'Пластиковая Бутылка',
      emoji: '🍶',
      description: 'Плавает тут с 2008 года',
      rarity: 'trash',
      pnl_percent: -22.1,
      caught_at: '2024-03-01T13:15:00Z',
      rod_name: 'Стартовая удочка',
      pond_name: 'Криптовые Воды',
      cdn_url: null,
      thumbnail_url: null
    }
  ],

  // User rods
  userRods: [
    {
      id: 1,
      name: 'Стартовая удочка',
      leverage: 1.0,
      price: 0,
      rarity: 'common',
      rod_type: 'neutral',
      visual_id: 'starter'
    },
    {
      id: 2,
      name: 'Лонг удочка',
      leverage: 2.0,
      price: 100,
      rarity: 'common',
      rod_type: 'long',
      visual_id: 'long_basic'
    },
    {
      id: 3,
      name: 'Шорт удочка',
      leverage: -2.0,
      price: 100,
      rarity: 'common',
      rod_type: 'short',
      visual_id: 'short_basic'
    },
    {
      id: 4,
      name: 'Титановая удочка',
      leverage: 5.0,
      price: 1000,
      rarity: 'epic',
      rod_type: 'long',
      visual_id: 'long_titanium'
    }
  ],

  // Active rod for user
  activeRod: {
    123456789: 2 // Long rod is active
  },

  // Leaderboard data
  leaderboard: {
    top: [
      {
        telegram_id: 111111,
        username: 'CryptoWhale',
        level: 12,
        balance: 58750,
        total_trades: 234,
        avg_pnl: 15.8,
        best_trade: 280.5,
        worst_trade: -45.2
      },
      {
        telegram_id: 222222,
        username: 'DeFiMaster',
        level: 10,
        balance: 42300,
        total_trades: 189,
        avg_pnl: 12.3,
        best_trade: 195.7,
        worst_trade: -38.9
      },
      {
        telegram_id: 333333,
        username: 'LuckyFisher',
        level: 9,
        balance: 35600,
        total_trades: 156,
        avg_pnl: 10.2,
        best_trade: 165.3,
        worst_trade: -42.1
      },
      {
        telegram_id: 444444,
        username: 'TradingPro',
        level: 8,
        balance: 28900,
        total_trades: 142,
        avg_pnl: 8.5,
        best_trade: 142.8,
        worst_trade: -35.6
      },
      {
        telegram_id: 555555,
        username: 'FishHunter',
        level: 7,
        balance: 22100,
        total_trades: 128,
        avg_pnl: 6.8,
        best_trade: 118.9,
        worst_trade: -29.3
      },
      {
        telegram_id: 123456789,
        username: 'TestFisherman',
        level: 5,
        balance: 12500,
        total_trades: 45,
        avg_pnl: 2.8,
        best_trade: 150.5,
        worst_trade: -35.7
      },
      {
        telegram_id: 666666,
        username: 'Beginner',
        level: 3,
        balance: 10800,
        total_trades: 32,
        avg_pnl: 1.2,
        best_trade: 45.6,
        worst_trade: -28.9
      },
      {
        telegram_id: 777777,
        username: 'CasualPlayer',
        level: 2,
        balance: 9500,
        total_trades: 18,
        avg_pnl: -1.5,
        best_trade: 32.1,
        worst_trade: -22.8
      },
      {
        telegram_id: 888888,
        username: 'Newbie',
        level: 1,
        balance: 8200,
        total_trades: 12,
        avg_pnl: -3.2,
        best_trade: 15.3,
        worst_trade: -18.7
      },
      {
        telegram_id: 999999,
        username: 'LastPlace',
        level: 1,
        balance: 5500,
        total_trades: 8,
        avg_pnl: -8.9,
        best_trade: 8.2,
        worst_trade: -45.3
      }
    ],
    bottom: [],
    user_position: 6,
    total_players: 1247,
    filters_applied: {
      time_period: 'all'
    }
  },

  // Mock fish images (base64 encoded 1x1 pixel images of different colors)
  fishImages: {
    legendary: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==', // Gold
    epic: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==', // Purple
    rare: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', // Blue
    common: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA0e7daQAAAABJRU5ErkJggg==', // Green
    trash: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg==' // Gray
  }
};

// Helper function to get mock image for fish
function getMockFishImage(rarity) {
  return mockData.fishImages[rarity] || mockData.fishImages.common;
}

// Export for Node.js (mock server)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { mockData, getMockFishImage };
}

// Export for browser (if needed)
if (typeof window !== 'undefined') {
  window.mockData = mockData;
  window.getMockFishImage = getMockFishImage;
}