// Configuration for webapp - switches between development and production modes

const config = {
  // Check if we're in development mode
  isDevelopment: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
  
  // API configuration
  get API_BASE_URL() {
    // In development, use mock server
    if (this.isDevelopment) {
      return 'http://localhost:3001';
    }
    // In production, use relative URLs (same origin)
    return '';
  },
  
  // Mock mode configuration
  get USE_MOCK_DATA() {
    // Enable mock data in development or if explicitly set
    return this.isDevelopment || window.USE_MOCK_DATA === true;
  },
  
  // Telegram WebApp configuration
  get TELEGRAM_ENABLED() {
    // Disable Telegram integration in development unless explicitly enabled
    return !this.isDevelopment || window.ENABLE_TELEGRAM === true;
  },
  
  // Default user for development
  DEFAULT_USER_ID: 123456789,
  DEFAULT_USERNAME: 'TestFisherman',
  
  // Image loading configuration
  IMAGE_LOAD_TIMEOUT: 5000, // 5 seconds
  
  // API request configuration
  API_TIMEOUT: 10000, // 10 seconds
  API_RETRY_COUNT: 2,
  API_RETRY_DELAY: 1000, // 1 second
  
  // Animation delays
  ANIMATION_DURATION: 300, // milliseconds
  TOAST_DURATION: 2000, // milliseconds
  
  // Debug mode
  get DEBUG() {
    return this.isDevelopment || window.DEBUG === true;
  }
};

// Log configuration in development
if (config.isDevelopment) {
  console.log('🎣 Fishing WebApp Configuration:', {
    mode: 'development',
    apiUrl: config.API_BASE_URL,
    mockData: config.USE_MOCK_DATA,
    telegram: config.TELEGRAM_ENABLED
  });
}

// Make config globally available
window.appConfig = config;

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
  module.exports = config;
}