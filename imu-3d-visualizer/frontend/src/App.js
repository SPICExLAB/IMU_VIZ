import React, { useState, useEffect, useRef } from 'react';
import ThreeJSScene from './components/ThreeJSScene';
import IMUOverlay from './components/IMUOverlay';
import ConnectionStatus from './components/ConnectionStatus';
import './App.css';

const WEBSOCKET_URL = 'ws://localhost:3001';

function App() {
  // WebSocket connection
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const wsRef = useRef(null);

  // Device data state
  const [devices, setDevices] = useState({});
  const [stats, setStats] = useState({
    ios: 0,
    ar_glasses: 0,
    unknown: 0,
    errors: 0,
    clients: 0
  });

  // UI state
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showOverlay, setShowOverlay] = useState(true);

  // Initialize WebSocket connection
  useEffect(() => {
    let reconnectTimer;

    const handleWebSocketMessage = (message) => {
      switch (message.type) {
        case 'connection':
          console.log('📱 Server connection message:', message.message);
          if (message.stats) {
            setStats(message.stats);
          }
          break;

        case 'imu_data':
          handleIMUData(message);
          break;

        default:
          console.log('Unknown message type:', message.type);
      }
    };

    const connectWebSocket = () => {
      try {
        console.log('🔗 Connecting to WebSocket server...');
        const websocket = new WebSocket(WEBSOCKET_URL);
        wsRef.current = websocket;

        websocket.onopen = () => {
          console.log('✅ WebSocket connected');
          setConnectionStatus('connected');
        };

        websocket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        websocket.onclose = () => {
          console.log('❌ WebSocket disconnected');
          setConnectionStatus('disconnected');
          
          // Auto-reconnect after 3 seconds
          reconnectTimer = setTimeout(() => {
            console.log('🔄 Attempting to reconnect...');
            setConnectionStatus('reconnecting');
            connectWebSocket();
          }, 3000);
        };

        websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
          setConnectionStatus('error');
        };

      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        setConnectionStatus('error');
      }
    };

    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []); // Empty dependency array is correct here

  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'connection':
        console.log('📱 Server connection message:', message.message);
        if (message.stats) {
          setStats(message.stats);
        }
        break;

      case 'imu_data':
        handleIMUData(message);
        break;

      default:
        console.log('Unknown message type:', message.type);
    }
  };

  const handleIMUData = (message) => {
    const { deviceType, data, clientIP } = message;
    
    if (!data || data.device_id === null || data.device_id === undefined) {
      return;
    }

    const deviceKey = `${data.device_name}_${data.device_id}`;
    const timestamp = Date.now();

    setDevices(prevDevices => {
      const currentDevice = prevDevices[deviceKey] || {
        device_id: data.device_id,
        device_name: data.device_name,
        device_type: data.device_type,
        clientIP: clientIP,
        isActive: true,
        lastUpdate: timestamp,
        sampleCount: 0,
        frequency: 0,
        accelerometerHistory: [],
        gyroscopeHistory: [],
        eulerHistory: [],
        quaternionHistory: []
      };

      // Update device data
      const updatedDevice = {
        ...currentDevice,
        accelerometer: data.accelerometer,
        gyroscope: data.gyroscope,
        quaternion: data.quaternion,
        euler: data.euler,
        lastUpdate: timestamp,
        sampleCount: currentDevice.sampleCount + 1,
        isActive: true,
        clientIP: clientIP
      };

      // Add to history buffers (keep last 300 samples ~10 seconds at 30Hz)
      const maxHistory = 300;
      const addToHistory = (history, newData) => {
        const updated = [...history, { timestamp, data: newData }];
        return updated.slice(-maxHistory);
      };

      updatedDevice.accelerometerHistory = addToHistory(
        currentDevice.accelerometerHistory, 
        data.accelerometer
      );
      updatedDevice.gyroscopeHistory = addToHistory(
        currentDevice.gyroscopeHistory, 
        data.gyroscope
      );
      updatedDevice.eulerHistory = addToHistory(
        currentDevice.eulerHistory, 
        data.euler
      );
      updatedDevice.quaternionHistory = addToHistory(
        currentDevice.quaternionHistory, 
        data.quaternion
      );

      // Calculate frequency (approximate)
      if (updatedDevice.sampleCount % 30 === 0) {
        const timeSpan = timestamp - (updatedDevice.accelerometerHistory[0]?.timestamp || timestamp);
        if (timeSpan > 0) {
          updatedDevice.frequency = Math.round((updatedDevice.accelerometerHistory.length / timeSpan) * 1000);
        }
      }

      return {
        ...prevDevices,
        [deviceKey]: updatedDevice
      };
    });

    // Update stats
    setStats(prevStats => ({
      ...prevStats,
      [deviceType]: (prevStats[deviceType] || 0) + 1
    }));
  };

  // Clean up inactive devices
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      setDevices(prevDevices => {
        const updated = { ...prevDevices };
        let hasChanges = false;

        Object.keys(updated).forEach(deviceKey => {
          if (now - updated[deviceKey].lastUpdate > 5000) { // 5 seconds timeout
            updated[deviceKey].isActive = false;
            hasChanges = true;
          }
        });

        return hasChanges ? updated : prevDevices;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const activeDevices = Object.values(devices).filter(device => device.isActive);
  const deviceCount = activeDevices.length;

  return (
    <div className="app">
      {/* Connection Status Bar */}
      <ConnectionStatus 
        status={connectionStatus}
        deviceCount={deviceCount}
        stats={stats}
      />

      {/* Main Layout */}
      <div className="main-layout">
        {/* 3D Scene */}
        <div className={`scene-container ${showOverlay ? 'with-overlay' : 'full-width'}`}>
          <ThreeJSScene 
            devices={devices}
            selectedDevice={selectedDevice}
            onDeviceSelect={setSelectedDevice}
          />
          
          {/* Scene Controls */}
          <div className="scene-controls">
            <button 
              onClick={() => setShowOverlay(!showOverlay)}
              className="toggle-overlay-btn"
              title={showOverlay ? 'Hide Overlay' : 'Show Overlay'}
            >
              {showOverlay ? '◀' : '▶'}
            </button>
          </div>
        </div>

        {/* IMU Data Overlay */}
        {showOverlay && (
          <div className="overlay-container">
            <IMUOverlay 
              devices={devices}
              selectedDevice={selectedDevice}
              onDeviceSelect={setSelectedDevice}
              connectionStatus={connectionStatus}
              stats={stats}
            />
          </div>
        )}
      </div>

      {/* Instructions Overlay */}
      {deviceCount === 0 && connectionStatus === 'connected' && (
        <div className="instructions-overlay">
          <div className="instructions-content">
            <h2>🎯 Ready for IMU Data!</h2>
            <p>WebSocket server is connected and waiting for device data.</p>
            <div className="instruction-steps">
              <div className="step">
                <span className="step-number">1</span>
                <span>Start your Python IMU sender</span>
              </div>
              <div className="step">
                <span className="step-number">2</span>
                <span>Send UDP packets to port 8001</span>
              </div>
              <div className="step">
                <span className="step-number">3</span>
                <span>Watch your devices appear in 3D!</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;