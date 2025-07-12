// App.js - Updated T-pose calibration handler
import React, { useState, useEffect, useRef } from 'react';
import ThreeJSScene from './components/ThreeJSScene';
import IMUOverlay from './components/IMUOverlay';
import ConnectionStatus from './components/ConnectionStatus';
import CalibrationPanel from './components/CalibrationPanel';
import { quaternionToEuler } from './utils/mathUtils';
import './App.css';

const WEBSOCKET_URL = 'ws://localhost:3001';

function App() {
  // ... (previous state and effects remain the same until handleTPoseCalibrationComplete)

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
  const [showCalibration, setShowCalibration] = useState(false);
  
  // Calibration state (simplified - server handles the math)
  const [calibrationParams, setCalibrationParams] = useState({
    isCalibrated: false,
    referenceDeviceId: null
  });

  // Initialize WebSocket connection
  useEffect(() => {
    let reconnectTimer;

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
  }, []);

  // Handle device selection
  useEffect(() => {
    if (selectedDevice) {
      setShowCalibration(true);
    } else {
      setShowCalibration(false);
    }
  }, [selectedDevice]);

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

      case 'calibration_confirmed':
        console.log('✅ Calibration confirmed by server');
        break;

      case 'tpose_calibration_confirmed':
        console.log('✅ T-pose calibration confirmed by server');
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
        device_type: data.device_type || deviceType,
        clientIP: clientIP,
        isActive: true,
        lastUpdate: timestamp,
        sampleCount: 0,
        frequency: 0,
        accelerometerHistory: [],
        linearAccelerationHistory: [],
        gyroscopeHistory: [],
        eulerHistory: [],
        quaternionHistory: [],
        worldFrameAccelerometerHistory: [],
        worldFrameLinearAccelerationHistory: [],
        worldFrameQuaternionHistory: [],
        worldFrameEulerHistory: []
      };

      // Update device data with all data from server (including world frame if present)
      const updatedDevice = {
        ...currentDevice,
        // Raw data
        accelerometer: data.accelerometer,
        quaternion: data.quaternion,
        euler: data.euler || quaternionToEuler(data.quaternion),
        has_gyro: !!data.has_gyro,
        
        // World frame data (if server calculated it)
        worldFrameQuaternion: data.worldFrameQuaternion,
        worldFrameQuatForViz: data.worldFrameQuatForViz,
        worldFrameAccelerometer: data.worldFrameAccelerometer,
        worldFrameEuler: data.worldFrameEuler,
        worldFrameLinearAcceleration: data.worldFrameLinearAcceleration,
        isCalibrated: !!data.isCalibrated,
        hasAccOffset: !!data.hasAccOffset,
        hasLinearAccOffset: !!data.hasLinearAccOffset,
        
        // Metadata
        lastUpdate: timestamp,
        sampleCount: currentDevice.sampleCount + 1,
        isActive: true,
        clientIP: clientIP
      };
      
      // Handle gyroscope data if available
      if (data.has_gyro) {
        updatedDevice.gyroscope = data.gyroscope || [0, 0, 0];
      }
      
      // Handle linear acceleration data for AR glasses
      if (data.linear_acceleration) {
        updatedDevice.linear_acceleration = data.linear_acceleration;
      }

      // Add to history buffers (keep last 300 samples ~10 seconds at 30Hz)
      const maxHistory = 300;
      const addToHistory = (history, newData) => {
        if (!newData) return history || [];
        const updated = [...(history || []), { timestamp, data: newData }];
        return updated.slice(-maxHistory);
      };

      // Always track raw data
      updatedDevice.accelerometerHistory = addToHistory(
        currentDevice.accelerometerHistory, 
        data.accelerometer
      );
      
      updatedDevice.eulerHistory = addToHistory(
        currentDevice.eulerHistory, 
        data.euler || updatedDevice.euler
      );
      
      updatedDevice.quaternionHistory = addToHistory(
        currentDevice.quaternionHistory, 
        data.quaternion
      );
      
      // Track linear acceleration for AR glasses
      if (data.linear_acceleration) {
        updatedDevice.linearAccelerationHistory = addToHistory(
          currentDevice.linearAccelerationHistory || [],
          data.linear_acceleration
        );
      }
      
      // Only add gyroscope data to history if the device has a gyroscope
      if (data.has_gyro) {
        updatedDevice.gyroscopeHistory = addToHistory(
          currentDevice.gyroscopeHistory, 
          data.gyroscope
        );
      }
      
      // Track world frame data if available from server
      if (data.worldFrameAccelerometer) {
        updatedDevice.worldFrameAccelerometerHistory = addToHistory(
          currentDevice.worldFrameAccelerometerHistory || [],
          data.worldFrameAccelerometer
        );
      }
      
      if (data.worldFrameQuaternion) {
        updatedDevice.worldFrameQuaternionHistory = addToHistory(
          currentDevice.worldFrameQuaternionHistory || [],
          data.worldFrameQuaternion
        );
      }
      
      if (data.worldFrameEuler) {
        updatedDevice.worldFrameEulerHistory = addToHistory(
          currentDevice.worldFrameEulerHistory || [],
          data.worldFrameEuler
        );
      }
      
      // Track world frame linear acceleration if available
      if (data.worldFrameLinearAcceleration) {
        updatedDevice.worldFrameLinearAccelerationHistory = addToHistory(
          currentDevice.worldFrameLinearAccelerationHistory || [],
          data.worldFrameLinearAcceleration
        );
      }

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

  // Handle calibration completion - send to server
  const handleCalibrationComplete = (calibrationData) => {
    console.log('Calibration complete, sending to server:', calibrationData);
    
    // Send calibration data to server
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'calibration',
        data: calibrationData
      }));
    }
    
    // Update local state to reflect calibration is active
    setCalibrationParams({
      isCalibrated: true,
      referenceDeviceId: calibrationData.referenceDeviceId,
      referenceWorldQuat: calibrationData.referenceWorldQuat
    });
  };
  
  // Handle T-pose calibration completion - Updated to include acceleration offsets
  const handleTPoseCalibrationComplete = (tposeData) => {
    console.log('T-pose calibration complete, sending to server:', tposeData);
    
    // Log offset information
    if (tposeData.accOffsets) {
      console.log('Acceleration offsets:', tposeData.accOffsets);
    }
    if (tposeData.linearAccOffsets) {
      console.log('Linear acceleration offsets (AR glasses):', tposeData.linearAccOffsets);
    }
    
    // Send T-pose calibration data to server
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'tpose_calibration',
        data: tposeData
      }));
    }
    
    // Update local state
    setCalibrationParams(prev => ({
      ...prev,
      isTPoseCalibrated: true,
      device2boneMatrices: tposeData.device2boneMatrices,
      accOffsets: tposeData.accOffsets,
      linearAccOffsets: tposeData.linearAccOffsets
    }));
  };
  
  // Handle calibration reset - notify server
  const handleCalibrationReset = () => {
    // Notify server to clear calibration
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'reset_calibration'
      }));
    }
    
    // Reset local state
    setCalibrationParams({
      isCalibrated: false,
      isTPoseCalibrated: false,
      referenceDeviceId: null
    });
    
    console.log('Calibration reset');
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
            calibrationParams={calibrationParams}
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
              calibrationParams={calibrationParams}
            />
          </div>
        )}
      </div>

      {/* Calibration Panel */}
      {showCalibration && selectedDevice && (
        <CalibrationPanel
          selectedDevice={selectedDevice}
          devices={devices}
          onCalibrationComplete={handleCalibrationComplete}
          onTPoseCalibrationComplete={handleTPoseCalibrationComplete}
          onCalibrationReset={handleCalibrationReset}
          showOverlay={showOverlay}
          calibrationParams={calibrationParams}
        />
      )}

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