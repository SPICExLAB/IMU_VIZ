// IMUOverlay.js - Cleaned and optimized version
import React from 'react';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import { 
  Activity, 
  Smartphone, 
  Watch, 
  Headphones, 
  Glasses, 
  Wifi, 
  WifiOff, 
  ArrowRight 
} from 'lucide-react';

// Constants
const WAVEFORM_SAMPLES = 50;
const AXIS_COLORS = {
  x: '#ef4444',
  y: '#22c55e', 
  z: '#3b82f6'
};

// Device Icon Component
const DeviceIcon = ({ deviceName, className = "w-4 h-4" }) => {
  const iconMap = {
    'phone': Smartphone,
    'iphone': Smartphone,
    'watch': Watch,
    'applewatch': Watch,
    'headphone': Headphones,
    'airpods': Headphones,
    'glasses': Glasses,
    'arglasses': Glasses
  };
  
  const Icon = iconMap[deviceName] || Activity;
  return <Icon className={className} />;
};

// Waveform Component
const Waveform = ({ data, dataKeys, colors, height = 100 }) => {
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

  // Prepare chart data
  const chartData = data.slice(-WAVEFORM_SAMPLES).map((item, index) => {
    const dataPoint = { time: index };
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
};

// Sensor Section Component
const SensorSection = ({ title, values, history, showWaveform = false, isWorldFrame = false }) => {
  const dataKeys = ['X', 'Y', 'Z'];
  const colors = [AXIS_COLORS.x, AXIS_COLORS.y, AXIS_COLORS.z];
  
  return (
    <div className="sensor-section">
      <div className="sensor-header">
        <span className="sensor-title">{title}</span>
        {isWorldFrame && (
          <span className="calibrated-indicator">
            <ArrowRight size={12} color="#10b981" />
            <span>World Frame</span>
          </span>
        )}
      </div>
      
      <div className="sensor-values">
        {values.map((value, index) => {
          const axis = ['x', 'y', 'z'][index];
          const label = ['X', 'Y', 'Z'][index];
          const decimals = title.includes('Gyroscope') ? 3 : 2;
          
          return (
            <span key={axis} className={`axis-${axis}`}>
              {label}: {value?.toFixed(decimals) || '0'.padEnd(decimals + 2, '0')}
            </span>
          );
        })}
      </div>
      
      {showWaveform && (
        <Waveform
          data={history}
          dataKeys={dataKeys}
          colors={colors}
          height={100}
        />
      )}
    </div>
  );
};

// Rotation Section Component  
const RotationSection = ({ title, euler, isWorldFrame = false }) => {
  const rotationLabels = ['Roll', 'Pitch', 'Yaw'];
  const rotationClasses = ['axis-roll', 'axis-pitch', 'axis-yaw'];
  
  return (
    <div className="sensor-section">
      <div className="sensor-header">
        <span className="sensor-title">{title}</span>
        {isWorldFrame && (
          <span className="calibrated-indicator">
            <ArrowRight size={12} color="#10b981" />
            <span>World Frame</span>
          </span>
        )}
      </div>
      
      <div className="sensor-values">
        {euler?.map((value, index) => (
          <span key={index} className={rotationClasses[index]}>
            {rotationLabels[index]}: {value?.toFixed(1) || '0.0'}°
          </span>
        )) || <span>No rotation data</span>}
      </div>
    </div>
  );
};

// Device Card Component
const DeviceCard = ({ device, isSelected, onSelect, calibrationParams }) => {
  const deviceKey = `${device.device_name}_${device.device_id}`;
  const timeSinceUpdate = Date.now() - device.lastUpdate;
  const isOnline = timeSinceUpdate < 3000;
  
  // Device capabilities
  const hasGyro = !!device.has_gyro;
  const isARGlasses = device.device_type === 'ar_glasses' && device.linear_acceleration;
  
  // Calibration status
  const isCalibrated = !!calibrationParams?.isCalibrated;
  const hasWorldFrame = isCalibrated && (
    device.worldFrameQuaternion || 
    device.worldFrameAccelerometer || 
    device.worldFrameEuler
  );

  return (
    <div 
      className={`enhanced-device-card ${isSelected ? 'selected' : ''} ${isOnline ? 'online' : 'offline'}`}
      onClick={() => onSelect(deviceKey)}
    >
      {/* Header */}
      <div className="device-card-header">
        <div className="device-info-row">
          <DeviceIcon deviceName={device.device_name} className="device-icon" />
          <div className="device-details">
            <span className="device-name">
              {device.device_name.charAt(0).toUpperCase() + device.device_name.slice(1)}
            </span>
            <span className="device-meta">
              ID: {device.device_id} • IP: {device.clientIP} • {device.frequency}Hz
              {hasGyro && <span> • Gyro</span>}
              {isARGlasses && <span> • Linear Acc</span>}
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

      {/* Acceleration Sections */}
      <SensorSection
        title="Raw Acceleration (m/s²)"
        values={device.accelerometer || [0, 0, 0]}
        history={device.accelerometerHistory}
        showWaveform={true}
      />
      
      {hasWorldFrame && device.worldFrameAccelerometer && (
        <SensorSection
          title="World Frame Acceleration (m/s²)"
          values={device.worldFrameAccelerometer}
          history={device.worldFrameAccelerometerHistory || []}
          showWaveform={true}
          isWorldFrame={true}
        />
      )}

      {/* Linear Acceleration for AR Glasses */}
      {isARGlasses && (
        <>
          <SensorSection
            title="Linear Acceleration (m/s²) - Raw"
            values={device.linear_acceleration}
            history={device.linearAccelerationHistory || []}
            showWaveform={true}
          />
          
          {hasWorldFrame && device.worldFrameLinearAcceleration && (
            <SensorSection
              title="Linear Acceleration (m/s²) - World Frame"
              values={device.worldFrameLinearAcceleration}
              history={device.worldFrameLinearAccelerationHistory || []}
              showWaveform={true}
              isWorldFrame={true}
            />
          )}
        </>
      )}

      {/* Rotation Sections */}
      <RotationSection
        title="Rotation (°) - Raw"
        euler={device.euler}
      />
      
      {hasWorldFrame && device.worldFrameEuler && (
        <RotationSection
          title="Rotation (°) - World Frame"
          euler={device.worldFrameEuler}
          isWorldFrame={true}
        />
      )}

      {/* Gyroscope Section */}
      {hasGyro && (
        <SensorSection
          title="Gyroscope (rad/s)"
          values={device.gyroscope || [0, 0, 0]}
          history={device.gyroscopeHistory}
          showWaveform={true}
        />
      )}
    </div>
  );
};

// Empty State Component
const EmptyState = () => (
  <div className="empty-state">
    <Activity className="empty-icon" />
    <h3>No Active Devices</h3>
    <p>Connect your IMU devices to see them here.</p>
    <div className="connection-help">
      <p>Make sure your devices are sending UDP packets to port 8001.</p>
    </div>
  </div>
);

// Main IMU Overlay Component
const IMUOverlay = ({ 
  devices, 
  selectedDevice, 
  onDeviceSelect, 
  connectionStatus,
  stats,
  calibrationParams
}) => {
  const activeDevices = Object.values(devices).filter(device => device.isActive);
  const isCalibrated = !!calibrationParams?.isCalibrated;

  return (
    <div className="imu-overlay">
      {/* Header */}
      <div className="overlay-header">
        <h2>IMU Data Monitor</h2>
        <div className="connection-indicator">
          <div className={`connection-dot ${connectionStatus}`} />
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

      {/* Tabs */}
      <div className="overlay-tabs">
        <div className="tab active">
          Devices ({activeDevices.length})
        </div>
      </div>

      {/* Content */}
      <div className="overlay-content">
        <div className="devices-tab">
          {activeDevices.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="enhanced-devices-list">
              {activeDevices.map(device => (
                <DeviceCard
                  key={`${device.device_name}_${device.device_id}`}
                  device={device}
                  isSelected={selectedDevice === `${device.device_name}_${device.device_id}`}
                  onSelect={onDeviceSelect}
                  calibrationParams={calibrationParams}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default IMUOverlay;