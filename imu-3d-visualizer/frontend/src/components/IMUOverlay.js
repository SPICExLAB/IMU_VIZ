import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import { Activity, Smartphone, Watch, Headphones, Glasses, Wifi, WifiOff, ArrowRight } from 'lucide-react';

// Device Icon Component
function DeviceIcon({ deviceName, className = "w-4 h-4" }) {
  switch (deviceName) {
    case 'phone':
    case 'iphone':
      return <Smartphone className={className} />;
    case 'watch':
    case 'applewatch':
      return <Watch className={className} />;
    case 'headphone':
    case 'airpods':
      return <Headphones className={className} />;
    case 'glasses':
    case 'arglasses':
      return <Glasses className={className} />;
    default:
      return <Activity className={className} />;
  }
}

// Waveform Component - For Accelerometer and Gyroscope only
function Waveform({ data, dataKeys, colors, height = 100 }) {
  if (!data || data.length === 0) {
    return (
      <div className="waveform-container" style={{ height }}>
        <div className="waveform-placeholder">
          <Activity className="waveform-placeholder-icon" />
          <span>No data</span>
        </div>
      </div>
    );
  }

  // Prepare chart data with last 50 samples
  const chartData = data.slice(-50).map((item, index) => {
    const relativeTime = index;
    const dataPoint = { time: relativeTime };
    
    dataKeys.forEach((key, keyIndex) => {
      dataPoint[key] = item.data[keyIndex] || 0;
    });
    
    return dataPoint;
  });

  return (
    <div className="waveform-container" style={{ height }}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <XAxis dataKey="time" hide />
          <YAxis hide />
          {dataKeys.map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colors[index]}
              strokeWidth={1.5}
              dot={false}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// Enhanced Device Card Component
function EnhancedDeviceCard({ device, isSelected, onSelect, calibrationParams }) {
  const deviceKey = `${device.device_name}_${device.device_id}`;
  const timeSinceUpdate = Date.now() - device.lastUpdate;
  const isOnline = timeSinceUpdate < 3000;
  
  // Use the has_gyro flag from the backend
  const hasGyro = !!device.has_gyro;
  
  // Check if this is an AR glasses device (which will have linear_acceleration)
  const isARGlasses = device.device_type === 'ar_glasses' && device.linear_acceleration;
  
  // Check if we have calibration and world frame data
  const isCalibrated = !!calibrationParams?.isCalibrated;
  
  // More explicit check for world frame data - with fallback condition
  const hasWorldFrameQuaternion = device.worldFrameQuaternion !== undefined;
  const hasWorldFrameAccelerometer = device.worldFrameAccelerometer !== undefined;
  const hasWorldFrameEuler = device.worldFrameEuler !== undefined;
  
  const hasWorldFrame = isCalibrated && (hasWorldFrameQuaternion || hasWorldFrameAccelerometer || hasWorldFrameEuler);

  // Debug world frame data detection
  console.log(`Device ${deviceKey} world frame data detection:`, {
    isCalibrated,
    hasWorldFrameQuaternion,
    hasWorldFrameAccelerometer,
    hasWorldFrameEuler,
    hasWorldFrame,
    worldFrameQuaternion: device.worldFrameQuaternion,
    worldFrameAccelerometer: device.worldFrameAccelerometer,
    worldFrameEuler: device.worldFrameEuler
  });

  return (
    <div 
      className={`enhanced-device-card ${isSelected ? 'selected' : ''} ${isOnline ? 'online' : 'offline'}`}
      onClick={() => onSelect(deviceKey)}
    >
      {/* Header Row */}
      <div className="device-card-header">
        <div className="device-info-row">
          <DeviceIcon deviceName={device.device_name} className="device-icon" />
          <div className="device-details">
            <span className="device-name">
              {device.device_name.charAt(0).toUpperCase() + device.device_name.slice(1)}
            </span>
            <span className="device-meta">
              ID: {device.device_id} • IP: {device.clientIP} • {device.frequency}Hz
              {hasGyro && <span> • Gyroscope Available</span>}
              {isARGlasses && <span> • Linear Acc Available</span>}
            </span>
          </div>
        </div>
        <div className="device-status-indicator">
          {isOnline ? (
            <Wifi className="status-icon online" />
          ) : (
            <WifiOff className="status-icon offline" />
          )}
        </div>
      </div>

      {/* Raw Acceleration Section */}
      <div className="sensor-section">
        <div className="sensor-header">
          <span className="sensor-title">Raw Acceleration (m/s²)</span>
        </div>
        <div className="sensor-values">
          <span className="axis-x">X: {device.accelerometer?.[0]?.toFixed(2) || '0.00'}</span>
          <span className="axis-y">Y: {device.accelerometer?.[1]?.toFixed(2) || '0.00'}</span>
          <span className="axis-z">Z: {device.accelerometer?.[2]?.toFixed(2) || '0.00'}</span>
        </div>
        
        {/* Display raw waveform */}
        <Waveform
          data={device.accelerometerHistory}
          dataKeys={['X', 'Y', 'Z']}
          colors={['#ef4444', '#22c55e', '#3b82f6']}
          height={100}
        />
      </div>
      
      {/* World Frame Acceleration Section */}
      {hasWorldFrame && hasWorldFrameAccelerometer && (
        <div className="sensor-section">
          <div className="sensor-header">
            <span className="sensor-title">World Frame Acceleration (m/s²)</span>
            <span className="calibrated-indicator">
              <ArrowRight size={12} color="#10b981" />
              <span>World Frame</span>
            </span>
          </div>
          <div className="sensor-values">
            <span className="axis-x">X: {device.worldFrameAccelerometer?.[0]?.toFixed(2) || '0.00'}</span>
            <span className="axis-y">Y: {device.worldFrameAccelerometer?.[1]?.toFixed(2) || '0.00'}</span>
            <span className="axis-z">Z: {device.worldFrameAccelerometer?.[2]?.toFixed(2) || '0.00'}</span>
          </div>
          
          {/* Display world frame acceleration waveform */}
          <Waveform
            data={device.worldFrameAccelerometerHistory || []}
            dataKeys={['X', 'Y', 'Z']}
            colors={['#ef4444', '#22c55e', '#3b82f6']}
            height={100}
          />
        </div>
      )}

      {/* Linear Acceleration Section (only for AR glasses) */}
      {isARGlasses && (
        <div className="sensor-section">
          <div className="sensor-header">
            <span className="sensor-title">Linear Acceleration (m/s²) - Raw</span>
          </div>
          <div className="sensor-values">
            <span className="axis-x">X: {device.linear_acceleration?.[0]?.toFixed(2) || '0.00'}</span>
            <span className="axis-y">Y: {device.linear_acceleration?.[1]?.toFixed(2) || '0.00'}</span>
            <span className="axis-z">Z: {device.linear_acceleration?.[2]?.toFixed(2) || '0.00'}</span>
          </div>
          <Waveform
            data={device.linearAccelerationHistory || []}
            dataKeys={['X', 'Y', 'Z']}
            colors={['#ef4444', '#22c55e', '#3b82f6']}
            height={100}
          />
        </div>
      )}
      
      {/* World Frame Linear Acceleration Section (only for AR glasses with calibration) */}
      {isARGlasses && hasWorldFrame && device.worldFrameLinearAcceleration && (
        <div className="sensor-section">
          <div className="sensor-header">
            <span className="sensor-title">Linear Acceleration (m/s²) - World Frame</span>
            <span className="calibrated-indicator">
              <ArrowRight size={12} color="#10b981" />
              <span>World Frame</span>
            </span>
          </div>
          <div className="sensor-values">
            <span className="axis-x">X: {device.worldFrameLinearAcceleration?.[0]?.toFixed(2) || '0.00'}</span>
            <span className="axis-y">Y: {device.worldFrameLinearAcceleration?.[1]?.toFixed(2) || '0.00'}</span>
            <span className="axis-z">Z: {device.worldFrameLinearAcceleration?.[2]?.toFixed(2) || '0.00'}</span>
          </div>
          <Waveform
            data={device.worldFrameLinearAccelerationHistory || []}
            dataKeys={['X', 'Y', 'Z']}
            colors={['#ef4444', '#22c55e', '#3b82f6']}
            height={100}
          />
        </div>
      )}

      {/* Raw Rotation Section */}
      <div className="sensor-section">
        <div className="sensor-header">
          <span className="sensor-title">Rotation (°) - Raw</span>
        </div>
        <div className="sensor-values">
          <span className="axis-roll">Roll: {device.euler?.[0]?.toFixed(1) || '0.0'}</span>
          <span className="axis-pitch">Pitch: {device.euler?.[1]?.toFixed(1) || '0.0'}</span>
          <span className="axis-yaw">Yaw: {device.euler?.[2]?.toFixed(1) || '0.0'}</span>
        </div>
      </div>
      
      {/* World Frame Rotation Section */}
      {hasWorldFrame && hasWorldFrameEuler && (
        <div className="sensor-section">
          <div className="sensor-header">
            <span className="sensor-title">Rotation (°) - World Frame</span>
            <span className="calibrated-indicator">
              <ArrowRight size={12} color="#10b981" />
              <span>World Frame</span>
            </span>
          </div>
          <div className="sensor-values">
            <span className="axis-roll">Roll: {device.worldFrameEuler?.[0]?.toFixed(1) || '0.0'}</span>
            <span className="axis-pitch">Pitch: {device.worldFrameEuler?.[1]?.toFixed(1) || '0.0'}</span>
            <span className="axis-yaw">Yaw: {device.worldFrameEuler?.[2]?.toFixed(1) || '0.0'}</span>
          </div>
        </div>
      )}

      {/* Gyroscope Section (only if device actually has gyroscope data) */}
      {hasGyro && (
        <div className="sensor-section">
          <div className="sensor-header">
            <span className="sensor-title">Gyroscope (rad/s)</span>
          </div>
          <div className="sensor-values">
            <span className="axis-x">X: {device.gyroscope?.[0]?.toFixed(3) || '0.000'}</span>
            <span className="axis-y">Y: {device.gyroscope?.[1]?.toFixed(3) || '0.000'}</span>
            <span className="axis-z">Z: {device.gyroscope?.[2]?.toFixed(3) || '0.000'}</span>
          </div>
          <Waveform
            data={device.gyroscopeHistory}
            dataKeys={['X', 'Y', 'Z']}
            colors={['#ef4444', '#22c55e', '#3b82f6']}
            height={100}
          />
        </div>
      )}
    </div>
  );
}

// Main IMU Overlay Component
export default function IMUOverlay({ 
  devices, 
  selectedDevice, 
  onDeviceSelect, 
  connectionStatus,
  stats,
  calibrationParams
}) {
  const activeDevices = Object.values(devices).filter(device => device.isActive);
  const isCalibrated = !!calibrationParams?.isCalibrated;

  return (
    <div className="imu-overlay">
      {/* Header */}
      <div className="overlay-header">
        <h2>IMU Data Monitor</h2>
        <div className="connection-indicator">
          <div className={`connection-dot ${connectionStatus}`}></div>
          <span className="connection-text">
            {connectionStatus === 'connected' ? 'Connected' : 
             connectionStatus === 'reconnecting' ? 'Reconnecting...' : 
             'Disconnected'}
          </span>
          {isCalibrated && (
            <span className="calibration-status">• World Frame Calibrated</span>
          )}
        </div>
      </div>

      {/* Single Tab */}
      <div className="overlay-tabs">
        <div className="tab active">
          Devices ({activeDevices.length})
        </div>
      </div>

      {/* Content */}
      <div className="overlay-content">
        <div className="devices-tab">
          {activeDevices.length === 0 ? (
            <div className="empty-state">
              <Activity className="empty-icon" />
              <h3>No Active Devices</h3>
              <p>Connect your IMU devices to see them here.</p>
              <div className="connection-help">
                <p>Make sure your devices are sending UDP packets to port 8001.</p>
              </div>
            </div>
          ) : (
            <div className="enhanced-devices-list">
              {activeDevices.map(device => {
                const deviceKey = `${device.device_name}_${device.device_id}`;
                return (
                  <EnhancedDeviceCard
                    key={deviceKey}
                    device={device}
                    isSelected={selectedDevice === deviceKey}
                    onSelect={onDeviceSelect}
                    calibrationParams={calibrationParams}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}