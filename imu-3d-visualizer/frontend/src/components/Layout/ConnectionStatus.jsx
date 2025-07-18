import React from 'react';
import { Group, Text, Badge, Box, Flex } from '@mantine/core';
import { Wifi, WifiOff, RotateCcw } from 'lucide-react';

export default function ConnectionStatus({ status, deviceCount, stats }) {
  const getStatusIcon = () => {
    const props = { size: 16 };
    switch (status) {
      case 'connected':
        return <Wifi {...props} color="#10b981" />;
      case 'reconnecting':
        return <RotateCcw {...props} color="#f59e0b" style={{ animation: 'spin 1s linear infinite' }} />;
      default:
        return <WifiOff {...props} color="#ef4444" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'connected': return 'green';
      case 'reconnecting': return 'yellow';
      default: return 'red';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected': return 'Connected to WebSocket Server';
      case 'reconnecting': return 'Reconnecting...';
      case 'error': return 'Connection Error';
      default: return 'Disconnected from Server';
    }
  };

  const totalPackets = (stats.ios || 0) + (stats.ar_glasses || 0) + (stats.unknown || 0);

  return (
    <Box 
      h="100%" 
      px="md" 
      style={{ 
        backgroundColor: status === 'connected' ? '#065f46' : 
                         status === 'reconnecting' ? '#92400e' : '#7f1d1d'
      }}
    >
      <Flex h="100%" align="center" justify="space-between">
        <Group gap="sm">
          {getStatusIcon()}
          <Text size="sm" fw={500} c="white">
            {getStatusText()}
          </Text>
          {status === 'connected' && (
            <Text size="xs" c="gray.3">
              • {deviceCount} device{deviceCount !== 1 ? 's' : ''} active
              • {totalPackets.toLocaleString()} packets received
            </Text>
          )}
        </Group>
        
        <Group gap="xl">
          <Group gap="xs">
            <Text size="xs" c="gray.4">WebSocket:</Text>
            <Badge 
              size="sm" 
              color={getStatusColor()} 
              variant="light"
            >
              {status === 'connected' ? 'ws://localhost:3001' : 'Offline'}
            </Badge>
          </Group>
          
          {status === 'connected' && (
            <Group gap="xs">
              <Text size="xs" c="gray.4">UDP Listener:</Text>
              <Badge size="sm" color="green" variant="light">
                Port 8001
              </Badge>
            </Group>
          )}
        </Group>
      </Flex>
    </Box>
  );
}

// CSS for spin animation
const style = document.createElement('style');
style.textContent = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);