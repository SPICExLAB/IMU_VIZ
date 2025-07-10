import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import { Activity, Smartphone, Watch, Headphones, Glasses, Wifi, WifiOff } from 'lucide-react';

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
function EnhancedDeviceCard({ device, isSelected, onSelect }) {
  const deviceKey = `${device.device_name}_${device.device_id}`;
  const timeSinceUpdate = Date.now() - device.lastUpdate;
  const isOnline = timeSinceUpdate < 3000;
  
  // Better gyroscope detection - check if device actually has meaningful gyro data
  // iPhone typically doesn't have gyro, only accelerometer and magnetometer
  const hasGyro = device.gyroscopeHistory && 
    device.gyroscopeHistory.length > 10 && // Has some history
    device.gyroscopeHistory.some(entry => 
      entry.data && entry.data.some(val => Math.abs(val) > 0.01) // Any meaningful movement
    );

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

      {/* Acceleration Section */}
      <div className="sensor-section">
        <div className="sensor-header">
          <span className="sensor-title">Acceleration (m/s²) - Raw Data</span>
        </div>
        <div className="sensor-values">
          <span className="axis-x">X: {device.accelerometer?.[0]?.toFixed(2) || '0.00'}</span>
          <span className="axis-y">Y: {device.accelerometer?.[1]?.toFixed(2) || '0.00'}</span>
          <span className="axis-z">Z: {device.accelerometer?.[2]?.toFixed(2) || '0.00'}</span>
        </div>
        <Waveform
          data={device.accelerometerHistory}
          dataKeys={['X', 'Y', 'Z']}
          colors={['#ef4444', '#22c55e', '#3b82f6']}
          height={100}
        />
      </div>

      {/* Rotation Section */}
      <div className="sensor-section">
        <div className="sensor-header">
          <span className="sensor-title">Rotation (°) - Raw Data</span>
        </div>
        <div className="sensor-values">
          <span className="axis-roll">Roll: {device.euler?.[0]?.toFixed(1) || '0.0'}</span>
          <span className="axis-pitch">Pitch: {device.euler?.[1]?.toFixed(1) || '0.0'}</span>
          <span className="axis-yaw">Yaw: {device.euler?.[2]?.toFixed(1) || '0.0'}</span>
        </div>
       
      </div>

      {/* Gyroscope Section (only if device actually has gyroscope data) */}
      {hasGyro && (
        <div className="sensor-section">
          <div className="sensor-header">
            <span className="sensor-title">Gyroscope (rad/s) - Raw Data</span>
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
  stats 
}) {
  const activeDevices = Object.values(devices).filter(device => device.isActive);

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