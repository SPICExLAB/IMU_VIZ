import React from 'react';
import { Card, Group, Text, Badge, Stack, Box, ThemeIcon, Divider } from '@mantine/core';
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
const DeviceIcon = ({ deviceName, size = 20 }) => {
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
  return <Icon size={size} />;
};

// Waveform Component
const Waveform = ({ data, dataKeys, colors, height = 80 }) => {
  if (!data || data.length === 0) {
    return (
      <Box h={height} style={{ 
        backgroundColor: '#1f2937', 
        borderRadius: '8px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <Text size="xs" c="dimmed">No data</Text>
      </Box>
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
    <Box h={height} style={{ backgroundColor: '#1f2937', borderRadius: '8px', padding: '8px' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
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
    </Box>
  );
};

// Sensor Section Component
const SensorSection = ({ title, values, history, showWaveform = false, isWorldFrame = false }) => {
  const dataKeys = ['X', 'Y', 'Z'];
  const colors = [AXIS_COLORS.x, AXIS_COLORS.y, AXIS_COLORS.z];
  
  return (
    <Box>
      <Group justify="space-between" mb={8}>
        <Text size="sm" fw={600} c="gray.3">{title}</Text>
        {isWorldFrame && (
          <Badge size="xs" color="green" variant="light" leftSection={<ArrowRight size={10} />}>
            World Frame
          </Badge>
        )}
      </Group>
      
      <Group gap="lg" mb={8}>
        {values.map((value, index) => {
          const axis = ['x', 'y', 'z'][index];
          const label = ['X', 'Y', 'Z'][index];
          const decimals = title.includes('Gyroscope') ? 3 : 2;
          
          return (
            <Text key={axis} size="xs" ff="monospace" c={`axis-${axis}`}>
              {label}: {value?.toFixed(decimals) || '0'.padEnd(decimals + 2, '0')}
            </Text>
          );
        })}
      </Group>
      
      {showWaveform && (
        <Waveform
          data={history}
          dataKeys={dataKeys}
          colors={colors}
          height={80}
        />
      )}
    </Box>
  );
};

// Rotation Section Component  
const RotationSection = ({ title, euler, isWorldFrame = false }) => {
  const rotationLabels = ['Roll', 'Pitch', 'Yaw'];
  const rotationColors = ['#ef4444', '#22c55e', '#3b82f6']; // Red, Green, Blue
  
  return (
    <Box>
      <Group justify="space-between" mb={8}>
        <Text size="sm" fw={600} c="gray.3">{title}</Text>
        {isWorldFrame && (
          <Badge size="xs" color="green" variant="light" leftSection={<ArrowRight size={10} />}>
            World Frame
          </Badge>
        )}
      </Group>
      
      <Group gap="lg">
        {euler?.map((value, index) => (
          <Text key={index} size="xs" ff="monospace" style={{ color: rotationColors[index] }}>
            {rotationLabels[index]}: {value?.toFixed(1) || '0.0'}°
          </Text>
        )) || <Text size="xs" c="dimmed">No rotation data</Text>}
      </Group>
    </Box>
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
    <Card 
      shadow="sm" 
      p="lg" 
      radius="md" 
      withBorder
      onClick={() => onSelect(deviceKey)}
      style={{
        cursor: 'pointer',
        borderColor: isSelected ? '#10b981' : '#374151',
        backgroundColor: isSelected ? 'rgba(16, 185, 129, 0.1)' : '#374151',
        opacity: isOnline ? 1 : 0.6,
      }}
    >
      {/* Header */}
      <Group justify="space-between" mb="md">
        <Group gap="sm">
          <ThemeIcon color="green" variant="light" size="lg">
            <DeviceIcon deviceName={device.device_name} />
          </ThemeIcon>
          <div>
            <Text fw={600} size="md" c="gray.2">
              {device.device_name.charAt(0).toUpperCase() + device.device_name.slice(1)}
            </Text>
            <Text size="xs" c="dimmed">
              ID: {device.device_id} • IP: {device.clientIP} • {device.frequency}Hz
              {hasGyro && ' • Gyro'}
              {isARGlasses && ' • Linear Acc'}
            </Text>
          </div>
        </Group>
        <ThemeIcon color={isOnline ? 'green' : 'red'} variant="light" size="sm">
          {isOnline ? <Wifi size={16} /> : <WifiOff size={16} />}
        </ThemeIcon>
      </Group>

      <Stack gap="md">
        {/* Acceleration Sections */}
        <SensorSection
          title="Raw Acceleration (m/s²)"
          values={device.accelerometer || [0, 0, 0]}
          history={device.accelerometerHistory}
          showWaveform={true}
        />
        
        {hasWorldFrame && device.worldFrameAccelerometer && (
          <>
            <Divider />
            <SensorSection
              title="World Frame Acceleration (m/s²)"
              values={device.worldFrameAccelerometer}
              history={device.worldFrameAccelerometerHistory || []}
              showWaveform={true}
              isWorldFrame={true}
            />
          </>
        )}

        {/* Linear Acceleration for AR Glasses */}
        {isARGlasses && (
          <>
            <Divider />
            <SensorSection
              title="Linear Acceleration (m/s²)"
              values={device.linear_acceleration}
              history={device.linearAccelerationHistory || []}
              showWaveform={true}
            />
            
            {hasWorldFrame && device.worldFrameLinearAcceleration && (
              <>
                <Divider />
                <SensorSection
                  title="World Linear Acceleration (m/s²)"
                  values={device.worldFrameLinearAcceleration}
                  history={device.worldFrameLinearAccelerationHistory || []}
                  showWaveform={true}
                  isWorldFrame={true}
                />
              </>
            )}
          </>
        )}

        {/* Rotation Sections */}
        <Divider />
        <RotationSection
          title="Rotation (°)"
          euler={device.euler}
        />
        
        {hasWorldFrame && device.worldFrameEuler && (
          <>
            <Divider />
            <RotationSection
              title="World Rotation (°)"
              euler={device.worldFrameEuler}
              isWorldFrame={true}
            />
          </>
        )}

        {/* Gyroscope Section */}
        {hasGyro && (
          <>
            <Divider />
            <SensorSection
              title="Gyroscope (rad/s)"
              values={device.gyroscope || [0, 0, 0]}
              history={device.gyroscopeHistory}
              showWaveform={true}
            />
          </>
        )}
      </Stack>
    </Card>
  );
};

export default DeviceCard;