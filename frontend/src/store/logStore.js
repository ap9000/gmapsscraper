import { create } from 'zustand';

export const useLogStore = create((set, get) => ({
  logs: [],
  
  addLog: (level, message, source = 'App') => {
    const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
    const logEntry = {
      id: Date.now() + Math.random(),
      timestamp,
      level,
      source,
      message,
    };
    
    set((state) => ({
      logs: [...state.logs.slice(-999), logEntry] // Keep last 1000 logs
    }));
    
    // Also log to console with emoji
    const emoji = {
      error: '❌',
      warn: '⚠️',
      info: 'ℹ️',
      debug: '🐛',
      success: '✅'
    };
    
    console.log(`${emoji[level] || '📝'} [${source}] ${message}`);
  },
  
  clearLogs: () => set({ logs: [] }),
  
  exportLogs: () => {
    const logs = get().logs;
    const logText = logs.map(log => 
      `${log.timestamp} [${log.level.toUpperCase()}] [${log.source}] ${log.message}`
    ).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gmaps-logs-${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
  
  // Helper methods for different log levels
  info: (message, source) => get().addLog('info', message, source),
  error: (message, source) => get().addLog('error', message, source),
  warn: (message, source) => get().addLog('warn', message, source),
  debug: (message, source) => get().addLog('debug', message, source),
  success: (message, source) => get().addLog('success', message, source),
}));