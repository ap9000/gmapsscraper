import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// Create axios instance with default configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Search API
export const searchAPI = {
  single: (searchData) => api.post('/api/search/single', searchData),
  jobs: (limit = 50) => api.get(`/api/search/jobs?limit=${limit}`),
  getJob: (jobId) => api.get(`/api/search/job/${jobId}`),
};

// Batch API
export const batchAPI = {
  upload: (formData) => api.post('/api/batch/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  getStatus: (batchId) => api.get(`/api/batch/${batchId}`),
};

// Costs API
export const costsAPI = {
  getSummary: (days = 30, currentMonth = false) => 
    api.get(`/api/costs/summary?days=${days}&current_month=${currentMonth}`),
  exportReport: (days = 30, currentMonth = false) =>
    api.post('/api/costs/export-report', { days, current_month: currentMonth }),
  getUsage: (apiName, days = 7) => 
    api.get(`/api/costs/usage/${apiName}?days=${days}`),
};

// Status API
export const statusAPI = {
  getConfig: () => api.get('/api/status/config'),
  getLimits: () => api.get('/api/status/limits'),
  getDatabase: () => api.get('/api/status/database'),
  getSystem: () => api.get('/api/status/system'),
};

// Export API
export const exportAPI = {
  businesses: (exportData) => api.post('/api/export/businesses', exportData),
  download: (filename) => api.get(`/api/export/download/${filename}`, {
    responseType: 'blob',
  }),
  listFiles: () => api.get('/api/export/files'),
};

// Health check
export const healthAPI = {
  check: () => api.get('/api/health'),
};

// Error handling interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // Request was made but no response received
      console.error('Network Error:', error.request);
    } else {
      // Something else happened
      console.error('Request Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default api;