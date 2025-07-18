import React from 'react';
import { ScrollArea, Stack, Text, Title, Center, ThemeIcon, Box } from '@mantine/core';
import { Activity } from 'lucide-react';
import DeviceCard from './DeviceCard';

// Empty State Component
const EmptyState = () => (
  <Center h="100%" p="xl">
    <Stack align="center" gap="md">
      <ThemeIcon size={60} radius="xl" color="gray" variant="light">
        <Activity size={30} />
      </ThemeIcon>
      <Title order={3} c="gray.5">No Active Devices</Title>
      <Text size="sm" c="dimmed" ta="center">
        Connect your IMU devices to see them here.
      </Text>
      <Text size="xs" c="dimmed" ta="center">
        Make sure your devices are sending UDP packets to port 8001.
      </Text>
    </Stack>
  </Center>
);

// Main IMU Overlay Component
const IMUOverlay = ({ 
  devices, 
  selectedDevice, 
  onDeviceSelect, 
  calibrationParams
}) => {
  const activeDevices = Object.values(devices).filter(device => device.isActive);
  const isCalibrated = !!calibrationParams?.isCalibrated;

  return (
    <Box h="100%" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box p="md" style={{ borderBottom: '1px solid #374151', backgroundColor: '#111827' }}>
        <Title order={4} c="gray.2">IMU Data Monitor</Title>
        <Text size="xs" c="dimmed" mt={4}>
          {activeDevices.length} active device{activeDevices.length !== 1 ? 's' : ''}
          {isCalibrated && ' • World Frame Calibrated'}
        </Text>
      </Box>

      {/* Content */}
      <ScrollArea style={{ flex: 1 }} p="md">
        {activeDevices.length === 0 ? (
          <EmptyState />
        ) : (
          <Stack gap="md">
            {activeDevices.map(device => (
              <DeviceCard
                key={`${device.device_name}_${device.device_id}`}
                device={device}
                isSelected={selectedDevice === `${device.device_name}_${device.device_id}`}
                onSelect={onDeviceSelect}
                calibrationParams={calibrationParams}
              />
            ))}
          </Stack>
        )}
      </ScrollArea>
    </Box>
  );
};

export default IMUOverlay;