import { useState, useEffect, useCallback, useRef } from 'react';
import { quaternionToEuler } from '../utils/mathUtils';

const MAX_HISTORY_LENGTH = 300; // ~10 seconds at 30Hz
const DEVICE_TIMEOUT = 5000; // 5 seconds

export function useDeviceData() {
  const [devices, setDevices] = useState({});
  const [selectedDevice, setSelectedDevice] = useState(null);
  const devicesRef = useRef({});

  // Process IMU data message
  const processIMUData = useCallback((message) => {
    if (message.type !== 'imu_data') return;
    
    const { deviceType, data, clientIP } = message;
    
    if (!data || data.device_id === null || data.device_id === undefined) {
      return;
    }

    const deviceKey = `${data.device_name}_${data.device_id}`;
    const timestamp = Date.now();

    setDevices(prevDevices => {
      const currentDevice = prevDevices[deviceKey] || createNewDevice(data, deviceType, clientIP, timestamp);
      
      // Update device data
      const updatedDevice = {
        ...currentDevice,
        ...extractDeviceData(data),
        lastUpdate: timestamp,
        sampleCount: currentDevice.sampleCount + 1,
        isActive: true,
        clientIP: clientIP
      };
      
      // Update history buffers
      updatedDevice.accelerometerHistory = addToHistory(
        currentDevice.accelerometerHistory, 
        data.accelerometer, 
        timestamp
      );
      
      updatedDevice.eulerHistory = addToHistory(
        currentDevice.eulerHistory, 
        data.euler || updatedDevice.euler, 
        timestamp
      );
      
      updatedDevice.quaternionHistory = addToHistory(
        currentDevice.quaternionHistory, 
        data.quaternion, 
        timestamp
      );
      
      // Handle optional data
      if (data.has_gyro) {
        updatedDevice.gyroscopeHistory = addToHistory(
          currentDevice.gyroscopeHistory, 
          data.gyroscope, 
          timestamp
        );
      }
      
      if (data.linear_acceleration) {
        updatedDevice.linearAccelerationHistory = addToHistory(
          currentDevice.linearAccelerationHistory || [], 
          data.linear_acceleration, 
          timestamp
        );
      }
      
      // Handle world frame data
      if (data.worldFrameAccelerometer) {
        updatedDevice.worldFrameAccelerometerHistory = addToHistory(
          currentDevice.worldFrameAccelerometerHistory || [], 
          data.worldFrameAccelerometer, 
          timestamp
        );
      }
      
      if (data.worldFrameLinearAcceleration) {
        updatedDevice.worldFrameLinearAccelerationHistory = addToHistory(
          currentDevice.worldFrameLinearAccelerationHistory || [], 
          data.worldFrameLinearAcceleration, 
          timestamp
        );
      }
      
      // Calculate frequency
      if (updatedDevice.sampleCount % 30 === 0) {
        updatedDevice.frequency = calculateFrequency(updatedDevice.accelerometerHistory);
      }
      
      const newDevices = {
        ...prevDevices,
        [deviceKey]: updatedDevice
      };
      
      devicesRef.current = newDevices;
      return newDevices;
    });
  }, []);

  // Check for inactive devices
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      setDevices(prevDevices => {
        const updated = { ...prevDevices };
        let hasChanges = false;

        Object.keys(updated).forEach(deviceKey => {
          if (now - updated[deviceKey].lastUpdate > DEVICE_TIMEOUT) {
            updated[deviceKey].isActive = false;
            hasChanges = true;
          }
        });

        return hasChanges ? updated : prevDevices;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Get active devices
  const getActiveDevices = useCallback(() => {
    return Object.values(devices).filter(device => device.isActive);
  }, [devices]);

  return {
    devices,
    selectedDevice,
    setSelectedDevice,
    processIMUData,
    activeDevices: getActiveDevices(),
    deviceCount: getActiveDevices().length
  };
}

// Helper functions
function createNewDevice(data, deviceType, clientIP, timestamp) {
  return {
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
}

function extractDeviceData(data) {
  return {
    // Raw data
    accelerometer: data.accelerometer,
    quaternion: data.quaternion,
    euler: data.euler || quaternionToEuler(data.quaternion),
    has_gyro: !!data.has_gyro,
    gyroscope: data.gyroscope || [0, 0, 0],
    
    // Optional data
    linear_acceleration: data.linear_acceleration,
    
    // World frame data
    worldFrameQuaternion: data.worldFrameQuaternion,
    worldFrameQuatForViz: data.worldFrameQuatForViz,
    worldFrameAccelerometer: data.worldFrameAccelerometer,
    worldFrameEuler: data.worldFrameEuler,
    worldFrameLinearAcceleration: data.worldFrameLinearAcceleration,
    
    // Calibration status
    isCalibrated: !!data.isCalibrated,
    hasAccOffset: !!data.hasAccOffset,
    hasLinearAccOffset: !!data.hasLinearAccOffset,
  };
}

function addToHistory(history, newData, timestamp) {
  if (!newData) return history || [];
  const updated = [...(history || []), { timestamp, data: newData }];
  return updated.slice(-MAX_HISTORY_LENGTH);
}

function calculateFrequency(history) {
  if (!history || history.length < 2) return 0;
  const timeSpan = history[history.length - 1].timestamp - history[0].timestamp;
  if (timeSpan > 0) {
    return Math.round((history.length / timeSpan) * 1000);
  }
  return 0;
}