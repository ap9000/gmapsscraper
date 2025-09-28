import { healthAPI } from './api';

// Import log store - we'll get it dynamically to avoid circular imports
let logStore = null;
const getLogStore = () => {
  if (!logStore) {
    // Dynamic import to avoid circular dependency
    import('../store/logStore').then(module => {
      logStore = module.useLogStore.getState();
    });
  }
  return logStore;
};

class BackendHealthService {
  constructor() {
    this.isConnected = false;
    this.retryCount = 0;
    this.maxRetries = 10; // 10 retries = ~10 seconds with 1 second intervals
    this.retryInterval = 1000; // 1 second
    this.healthCheckInterval = null;
    this.onStatusChange = null;
    
    // Try to get log store and log initialization
    setTimeout(() => {
      const logger = getLogStore();
      if (logger) {
        logger.info('BackendHealthService initialized', 'HealthService');
      }
      console.log('🏥 BackendHealthService initialized');
    }, 100);
  }

  async checkHealth() {
    const logger = getLogStore();
    try {
      if (logger) logger.debug('Checking backend health...', 'HealthService');
      console.log('🩺 Checking backend health...');
      
      await healthAPI.check();
      if (!this.isConnected) {
        if (logger) logger.success('Backend health check passed - connected!', 'HealthService');
        console.log('✅ Backend health check passed - connected!');
        this.isConnected = true;
        this.retryCount = 0;
        this.onStatusChange?.(true);
      }
      return true;
    } catch (error) {
      if (logger) logger.error(`Backend health check failed: ${error.message}`, 'HealthService');
      console.log('❌ Backend health check failed:', error.message);
      
      if (this.isConnected) {
        if (logger) logger.warn('Backend status changed from connected to disconnected', 'HealthService');
        console.log('📡 Backend status changed from connected to disconnected');
        this.isConnected = false;
        this.onStatusChange?.(false);
      }
      return false;
    }
  }

  async waitForBackend() {
    console.log('🔄 Waiting for backend to start...');
    
    return new Promise((resolve, reject) => {
      const tryConnect = async () => {
        const isHealthy = await this.checkHealth();
        
        if (isHealthy) {
          console.log('✅ Backend is ready!');
          resolve(true);
          return;
        }

        this.retryCount++;
        
        if (this.retryCount >= this.maxRetries) {
          console.error(`❌ Backend failed to start after ${this.maxRetries} attempts`);
          reject(new Error('Backend startup timeout'));
          return;
        }

        console.log(`⏳ Backend not ready yet... (${this.retryCount}/${this.maxRetries})`);
        setTimeout(tryConnect, this.retryInterval);
      };

      tryConnect();
    });
  }

  startPeriodicHealthCheck(interval = 10000) {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    this.healthCheckInterval = setInterval(() => {
      this.checkHealth();
    }, interval);
  }

  stopPeriodicHealthCheck() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }

  setStatusChangeCallback(callback) {
    this.onStatusChange = callback;
  }

  getConnectionStatus() {
    return this.isConnected;
  }
}

export const backendHealthService = new BackendHealthService();
export default backendHealthService;