import React, { useEffect } from 'react';
import { Layout, ConfigProvider, theme, Spin, Alert } from 'antd';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import Dashboard from './components/Dashboard/Dashboard';
import Search from './components/Search/Search';
import Batch from './components/Batch/Batch';
import Analytics from './components/Analytics/Analytics';
import Settings from './components/Settings/Settings';
import Debug from './components/Debug/Debug';
import { useAppStore } from './store/appStore';
import { useLogStore } from './store/logStore';
import { connectWebSocket } from './services/websocket';
import { backendHealthService } from './services/backendHealth';
import './App.css';

const { Content } = Layout;

function App() {
  const { darkMode, setConnected, backendLoading, setBackendLoading } = useAppStore();
  const { info, error, success } = useLogStore();

  useEffect(() => {
    info(`App starting, backend loading: ${backendLoading}`, 'App');
    
    // Setup backend health monitoring
    backendHealthService.setStatusChangeCallback((isConnected) => {
      info(`Backend status changed: ${isConnected ? 'Connected' : 'Disconnected'}`, 'HealthService');
      setConnected(isConnected);
      setBackendLoading(false);
      if (isConnected) {
        success('Backend connection established', 'HealthService');
      } else {
        error('Backend connection lost', 'HealthService');
      }
    });

    // Failsafe timeout - stop loading screen after 15 seconds no matter what
    const failsafeTimeout = setTimeout(() => {
      error('Failsafe timeout - stopping loading screen after 15 seconds', 'App');
      setBackendLoading(false);
    }, 15000);

    // Start backend health monitoring
    const initializeBackend = async () => {
      try {
        info('Starting backend initialization...', 'App');
        
        // Wait for backend to be ready (with timeout)
        await backendHealthService.waitForBackend();
        success('Backend wait completed successfully', 'App');
        
        // Clear failsafe timeout since we connected
        clearTimeout(failsafeTimeout);
        
        // Ensure loading state is updated
        setBackendLoading(false);
        
        // Once backend is ready, start periodic health checks
        backendHealthService.startPeriodicHealthCheck();
        info('Periodic health checks started', 'App');
        
        // Connect to WebSocket for real-time updates
        const ws = connectWebSocket();
        
        ws.onopen = () => {
          success('Connected to WebSocket', 'WebSocket');
        };
        
        ws.onclose = () => {
          error('Disconnected from WebSocket', 'WebSocket');
        };
        
        ws.onerror = (wsError) => {
          error(`WebSocket error: ${wsError.message || 'Unknown error'}`, 'WebSocket');
        };
        
        return () => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
          }
        };
      } catch (initError) {
        error(`Failed to initialize backend connection: ${initError.message}`, 'App');
        clearTimeout(failsafeTimeout);
        setConnected(false);
        setBackendLoading(false);
      }
    };

    initializeBackend();

    return () => {
      info('App cleanup - stopping health checks', 'App');
      backendHealthService.stopPeriodicHealthCheck();
    };
  }, [setConnected, setBackendLoading]);

  return (
    <ConfigProvider
      theme={{
        algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
        },
      }}
    >
      {backendLoading ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          background: darkMode ? '#141414' : '#fff'
        }}>
          <Spin size="large" style={{ marginBottom: 16 }} />
          <h2 style={{ color: darkMode ? '#fff' : '#000', margin: 0 }}>Starting Backend...</h2>
          <p style={{ color: darkMode ? '#999' : '#666', marginTop: 8 }}>
            Please wait while the application initializes
          </p>
        </div>
      ) : (
        <Router>
          <Layout style={{ minHeight: '100vh' }}>
            <Sidebar />
            <Layout>
              <Header />
              <Content style={{ margin: '16px', overflow: 'initial' }}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/search" element={<Search />} />
                  <Route path="/batch" element={<Batch />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/debug" element={<Debug />} />
                </Routes>
              </Content>
            </Layout>
          </Layout>
        </Router>
      )}
    </ConfigProvider>
  );
}

export default App
