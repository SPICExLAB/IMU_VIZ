// App.js - Final fixed implementation with proper naming and AR glasses handling

import React, { useState, useEffect, useRef } from 'react';
import ThreeJSScene from './components/ThreeJSScene';
import IMUOverlay from './components/IMUOverlay';
import ConnectionStatus from './components/ConnectionStatus';
import CalibrationPanel from './components/CalibrationPanel';
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
  const [showCalibration, setShowCalibration] = useState(false);
  
  // Calibration state
  const [calibrationParams, setCalibrationParams] = useState({
    smpl2imu: null,
    referenceDeviceId: null,
    isCalibrated: false
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
        linearAccelerationHistory: [],
        gyroscopeHistory: [],
        eulerHistory: [],
        quaternionHistory: [],
        worldFrameAccelerometerHistory: [],
        worldFrameLinearAccelerationHistory: [],
        worldFrameQuaternionHistory: []
      };

      // Update device data
      const updatedDevice = {
        ...currentDevice,
        accelerometer: data.accelerometer,
        quaternion: data.quaternion,
        euler: data.euler,
        has_gyro: !!data.has_gyro,
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
      
      // Apply calibration if available - process all incoming data
      if (calibrationParams.isCalibrated && calibrationParams.smpl2imu) {
        // Process regular acceleration
        const calibratedData = applyCalibrationToDevice(
          updatedDevice.quaternion, 
          updatedDevice.accelerometer, 
          calibrationParams.smpl2imu
        );
        
        if (calibratedData) {
          // Use "worldFrame" naming instead of "calibrated"
          updatedDevice.worldFrameQuaternion = calibratedData.quaternion;
          updatedDevice.worldFrameAccelerometer = calibratedData.acceleration;
          updatedDevice.worldFrameEuler = quaternionToEuler(calibratedData.quaternion);
        }
        
        // Also process linear acceleration for AR glasses
        if (data.linear_acceleration) {
          const linearAccelWorld = matrixVectorMultiply(
            calibrationParams.smpl2imu, 
            updatedDevice.linear_acceleration
          );
          
          updatedDevice.worldFrameLinearAcceleration = linearAccelWorld;
        }
      }

      // Add to history buffers (keep last 300 samples ~10 seconds at 30Hz)
      const maxHistory = 300;
      const addToHistory = (history, newData) => {
        const updated = [...history, { timestamp, data: newData }];
        return updated.slice(-maxHistory);
      };

      // Always track raw data
      updatedDevice.accelerometerHistory = addToHistory(
        currentDevice.accelerometerHistory, 
        data.accelerometer
      );
      
      updatedDevice.eulerHistory = addToHistory(
        currentDevice.eulerHistory, 
        data.euler
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
        
        // Track world frame linear acceleration if available
        if (updatedDevice.worldFrameLinearAcceleration) {
          updatedDevice.worldFrameLinearAccelerationHistory = addToHistory(
            currentDevice.worldFrameLinearAccelerationHistory || [],
            updatedDevice.worldFrameLinearAcceleration
          );
        }
      }
      
      // Track world frame data if available
      if (updatedDevice.worldFrameAccelerometer) {
        updatedDevice.worldFrameAccelerometerHistory = addToHistory(
          currentDevice.worldFrameAccelerometerHistory || [],
          updatedDevice.worldFrameAccelerometer
        );
      }
      
      if (updatedDevice.worldFrameQuaternion) {
        updatedDevice.worldFrameQuaternionHistory = addToHistory(
          currentDevice.worldFrameQuaternionHistory || [],
          updatedDevice.worldFrameQuaternion
        );
      }
      
      // Only add gyroscope data to history if the device has a gyroscope
      if (data.has_gyro) {
        updatedDevice.gyroscopeHistory = addToHistory(
          currentDevice.gyroscopeHistory, 
          data.gyroscope
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

  // Convert quaternion to Euler angles in degrees
  const quaternionToEuler = (quaternion) => {
    const [x, y, z, w] = quaternion;
    
    // Roll (x-axis rotation)
    const sinr_cosp = 2 * (w * x + y * z);
    const cosr_cosp = 1 - 2 * (x * x + y * y);
    const roll = Math.atan2(sinr_cosp, cosr_cosp) * 180 / Math.PI;

    // Pitch (y-axis rotation)
    const sinp = 2 * (w * y - z * x);
    let pitch;
    if (Math.abs(sinp) >= 1) {
      pitch = Math.sign(sinp) * 90; // Use 90 degrees if out of range
    } else {
      pitch = Math.asin(sinp) * 180 / Math.PI;
    }

    // Yaw (z-axis rotation)
    const siny_cosp = 2 * (w * z + x * y);
    const cosy_cosp = 1 - 2 * (y * y + z * z);
    const yaw = Math.atan2(siny_cosp, cosy_cosp) * 180 / Math.PI;

    return [roll, pitch, yaw];
  };

  // Apply calibration to a device's data
  const applyCalibrationToDevice = (quaternion, acceleration, smpl2imu) => {
    try {
      // Convert quaternion to rotation matrix
      const rotMatrix = quaternionToRotationMatrix(quaternion);
      
      // Apply smpl2imu transformation
      const worldRotMatrix = matrixMultiply(smpl2imu, rotMatrix);
      
      // Convert back to quaternion
      const worldQuaternion = rotationMatrixToQuaternion(worldRotMatrix);
      
      // Apply transformation to acceleration
      const worldAcceleration = matrixVectorMultiply(smpl2imu, acceleration);
      
      return {
        quaternion: worldQuaternion,
        acceleration: worldAcceleration
      };
    } catch (error) {
      console.error('Error applying calibration:', error);
      return null;
    }
  };

  // Matrix/quaternion utility functions
  const quaternionToRotationMatrix = (q) => {
    const [x, y, z, w] = q;
    
    return [
      [1 - 2 * (y*y + z*z), 2 * (x*y - w*z), 2 * (x*z + w*y)],
      [2 * (x*y + w*z), 1 - 2 * (x*x + z*z), 2 * (y*z - w*x)],
      [2 * (x*z - w*y), 2 * (y*z + w*x), 1 - 2 * (x*x + y*y)]
    ];
  };
  
  const rotationMatrixToQuaternion = (m) => {
    const trace = m[0][0] + m[1][1] + m[2][2];
    
    if (trace > 0) {
      const S = Math.sqrt(trace + 1.0) * 2;
      return [
        (m[2][1] - m[1][2]) / S,
        (m[0][2] - m[2][0]) / S,
        (m[1][0] - m[0][1]) / S,
        0.25 * S
      ];
    } else if (m[0][0] > m[1][1] && m[0][0] > m[2][2]) {
      const S = Math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2;
      return [
        0.25 * S,
        (m[0][1] + m[1][0]) / S,
        (m[0][2] + m[2][0]) / S,
        (m[2][1] - m[1][2]) / S
      ];
    } else if (m[1][1] > m[2][2]) {
      const S = Math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2;
      return [
        (m[0][1] + m[1][0]) / S,
        0.25 * S,
        (m[1][2] + m[2][1]) / S,
        (m[0][2] - m[2][0]) / S
      ];
    } else {
      const S = Math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2;
      return [
        (m[0][2] + m[2][0]) / S,
        (m[1][2] + m[2][1]) / S,
        0.25 * S,
        (m[1][0] - m[0][1]) / S
      ];
    }
  };
  
  const matrixMultiply = (a, b) => {
    const result = Array(3).fill().map(() => Array(3).fill(0));
    
    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) {
        for (let k = 0; k < 3; k++) {
          result[i][j] += a[i][k] * b[k][j];
        }
      }
    }
    
    return result;
  };
  
  const matrixVectorMultiply = (m, v) => {
    return [
      m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
      m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
      m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2]
    ];
  };

  // Handle calibration completion
  const handleCalibrationComplete = (calibrationData) => {
    console.log('Calibration complete:', calibrationData);
    setCalibrationParams(calibrationData);
  };
  
  // Handle calibration reset
  const handleCalibrationReset = () => {
    setCalibrationParams({
      smpl2imu: null,
      referenceDeviceId: null,
      isCalibrated: false
    });
    
    // Clear world frame data from all devices
    setDevices(prevDevices => {
      const updatedDevices = {};
      
      Object.entries(prevDevices).forEach(([key, device]) => {
        updatedDevices[key] = {
          ...device,
          worldFrameQuaternion: undefined,
          worldFrameAccelerometer: undefined,
          worldFrameEuler: undefined,
          worldFrameLinearAcceleration: undefined,
          worldFrameAccelerometerHistory: [],
          worldFrameQuaternionHistory: [],
          worldFrameLinearAccelerationHistory: []
        };
      });
      
      return updatedDevices;
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
          onCalibrationReset={handleCalibrationReset}
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