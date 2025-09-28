import { create } from 'zustand';

export const useAppStore = create((set, get) => ({
  // Connection status
  connected: false,
  setConnected: (connected) => set({ connected }),
  
  // Loading state
  backendLoading: true,
  setBackendLoading: (loading) => set({ backendLoading: loading }),

  // UI state
  darkMode: false,
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),

  // Search state
  searchHistory: [],
  addToSearchHistory: (search) => set((state) => ({
    searchHistory: [search, ...state.searchHistory.slice(0, 49)] // Keep last 50
  })),

  currentSearch: null,
  setCurrentSearch: (search) => set({ currentSearch: search }),

  searchResults: [],
  setSearchResults: (results) => set({ searchResults: results }),

  searchProgress: {
    jobId: null,
    progress: 0,
    status: 'idle',
    details: ''
  },
  setSearchProgress: (progress) => set({ searchProgress: progress }),

  // Batch state
  batchJobs: [],
  addBatchJob: (job) => set((state) => ({
    batchJobs: [job, ...state.batchJobs]
  })),
  updateBatchJob: (jobId, updates) => set((state) => ({
    batchJobs: state.batchJobs.map(job => 
      job.id === jobId ? { ...job, ...updates } : job
    )
  })),

  // Analytics state
  costSummary: null,
  setCostSummary: (summary) => set({ costSummary: summary }),

  systemStatus: null,
  setSystemStatus: (status) => set({ systemStatus: status }),

  // Configuration state
  config: {
    scrapingdog: { configured: false },
    hunter: { configured: false, enabled: false },
    hubspot: { configured: false, enabled: false }
  },
  setConfig: (config) => set({ config }),

  // WebSocket event handlers
  handleWebSocketMessage: (message) => {
    const { type, data } = message;
    
    switch (type) {
      case 'search.progress':
        set((state) => ({
          searchProgress: {
            jobId: data.job_id,
            progress: data.progress,
            status: data.status,
            details: data.details
          }
        }));
        break;
        
      case 'enrichment.status':
        // Update enrichment progress
        console.log('Enrichment status:', data);
        break;
        
      case 'export.complete':
        // Handle export completion
        console.log('Export complete:', data);
        break;
        
      case 'error':
        // Handle error notifications
        console.error('WebSocket error:', data);
        break;
        
      default:
        console.log('Unknown WebSocket message type:', type, data);
    }
  },

  // Utility functions
  reset: () => set({
    searchHistory: [],
    currentSearch: null,
    searchResults: [],
    searchProgress: {
      jobId: null,
      progress: 0,
      status: 'idle',
      details: ''
    },
    batchJobs: [],
    costSummary: null,
    systemStatus: null
  })
}));