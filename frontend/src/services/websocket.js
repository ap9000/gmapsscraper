import { useAppStore } from '../store/appStore';

let ws = null;

export const connectWebSocket = () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    return ws;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//localhost:8000/ws`;

  ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      // Get the store and handle the message
      const { handleWebSocketMessage } = useAppStore.getState();
      handleWebSocketMessage(message);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  };

  // Keep connection alive with ping/pong
  const pingInterval = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
    } else {
      clearInterval(pingInterval);
    }
  }, 30000); // Ping every 30 seconds

  return ws;
};

export const sendWebSocketMessage = (message) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
};

export const closeWebSocket = () => {
  if (ws) {
    ws.close();
    ws = null;
  }
};