import { useEffect, useRef, useState, useCallback } from 'react';
import { notifications } from '@mantine/notifications';

const WEBSOCKET_URL = 'ws://localhost:3001';
const RECONNECT_DELAY = 3000;

export function useWebSocket(onMessage) {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [stats, setStats] = useState({
    ios: 0,
    ar_glasses: 0,
    unknown: 0,
    errors: 0,
    clients: 0
  });
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Send message through WebSocket
  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    try {
      console.log('🔗 Connecting to WebSocket server...');
      const websocket = new WebSocket(WEBSOCKET_URL);
      wsRef.current = websocket;

      websocket.onopen = () => {
        console.log('✅ WebSocket connected');
        setConnectionStatus('connected');
        notifications.show({
          title: 'Connected',
          message: 'Successfully connected to IMU server',
          color: 'green',
        });
      };

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Handle connection stats
          if (message.type === 'connection' && message.stats) {
            setStats(message.stats);
          }
          
          // Pass message to handler
          if (onMessage) {
            onMessage(message);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      websocket.onclose = () => {
        console.log('❌ WebSocket disconnected');
        setConnectionStatus('disconnected');
        
        notifications.show({
          title: 'Disconnected',
          message: 'Lost connection to server. Reconnecting...',
          color: 'orange',
        });
        
        // Auto-reconnect
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('🔄 Attempting to reconnect...');
          setConnectionStatus('reconnecting');
          connect();
        }, RECONNECT_DELAY);
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('error');
      notifications.show({
        title: 'Connection Error',
        message: 'Failed to connect to IMU server',
        color: 'red',
      });
    }
  }, [onMessage]);

  // Initialize connection
  useEffect(() => {
    connect();

    // Cleanup
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    connectionStatus,
    stats,
    sendMessage,
    isConnected: connectionStatus === 'connected'
  };
}