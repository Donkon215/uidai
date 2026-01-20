// Production Environment Configuration
// =====================================

const config = {
  // API Configuration
  API_BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  API_TIMEOUT: process.env.REACT_APP_API_TIMEOUT || 30000, // 30 seconds
  
  // Environment
  ENVIRONMENT: process.env.NODE_ENV || 'development',
  IS_PRODUCTION: process.env.NODE_ENV === 'production',
  
  // Feature Flags
  ENABLE_ANALYTICS: process.env.REACT_APP_ENABLE_ANALYTICS === 'true',
  ENABLE_ERROR_REPORTING: process.env.REACT_APP_ENABLE_ERROR_REPORTING === 'true',
  ENABLE_DEBUG_MODE: process.env.REACT_APP_DEBUG_MODE === 'true',
  
  // Performance
  ENABLE_SERVICE_WORKER: process.env.REACT_APP_ENABLE_SW === 'true',
  CACHE_DURATION: parseInt(process.env.REACT_APP_CACHE_DURATION || '300000'), // 5 minutes
  
  // Map Configuration
  MAP_DEFAULT_CENTER: { lat: 20.5937, lng: 78.9629 }, // India center
  MAP_DEFAULT_ZOOM: 5,
  MAP_MAX_ZOOM: 18,
  MAP_MIN_ZOOM: 4,
  
  // UI Configuration
  REFRESH_INTERVAL: parseInt(process.env.REACT_APP_REFRESH_INTERVAL || '60000'), // 1 minute
  MAX_RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 2000, // 2 seconds
  
  // Data Limits
  MAX_PINCODES_DISPLAY: 10000,
  PAGINATION_SIZE: 50,
  
  // Error Messages
  ERROR_MESSAGES: {
    NETWORK_ERROR: 'Network error. Please check your connection.',
    API_ERROR: 'Server error. Please try again later.',
    DATA_LOAD_ERROR: 'Failed to load data. Please refresh the page.',
    TIMEOUT_ERROR: 'Request timed out. Please try again.',
    UNKNOWN_ERROR: 'An unexpected error occurred.',
  },
};

// Validate configuration
const validateConfig = () => {
  if (!config.API_BASE_URL) {
    console.error('API_BASE_URL is not configured!');
  }
  
  if (config.IS_PRODUCTION && config.ENABLE_DEBUG_MODE) {
    console.warn('Debug mode enabled in production!');
  }
  
  return true;
};

validateConfig();

export default config;
