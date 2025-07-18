import React from 'react';
import { Modal, Stack, Text, List, ThemeIcon, Title } from '@mantine/core';
import { Activity } from 'lucide-react';

export default function EmptyStateInstructions() {
  return (
    <Modal
      opened={true}
      onClose={() => {}} // Can't close - no devices
      size="md"
      centered
      withCloseButton={false}
      overlayProps={{
        backgroundOpacity: 0.8,
        blur: 4,
      }}
      styles={{
        content: {
          backgroundColor: '#1f2937',
          border: '2px solid #10b981',
        }
      }}
    >
      <Stack align="center" gap="lg">
        <ThemeIcon size={60} radius="xl" color="green" variant="light">
          <Activity size={30} />
        </ThemeIcon>
        
        <Title order={2} c="green">Ready for IMU Data!</Title>
        
        <Text c="dimmed" ta="center">
          WebSocket server is connected and waiting for device data.
        </Text>
        
        <List
          spacing="sm"
          size="sm"
          center
          icon={
            <ThemeIcon color="green" size={24} radius="xl">
              <Text size="xs" fw={700}>→</Text>
            </ThemeIcon>
          }
        >
          <List.Item>Start your iOS app with devices</List.Item>
          <List.Item>Launch Unity app on AR glasses</List.Item>
          <List.Item>Devices will appear in 3D automatically!</List.Item>
        </List>
        
        <Text size="xs" c="dimmed" ta="center">
          Listening on UDP port 8001...
        </Text>
      </Stack>
    </Modal>
  );
}