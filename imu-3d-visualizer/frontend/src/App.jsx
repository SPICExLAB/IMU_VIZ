import React, { useEffect, useCallback } from 'react';
import { MantineProvider, AppShell, Box, LoadingOverlay } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

// Components
import ConnectionStatus from './components/Layout/ConnectionStatus';
import ThreeJSScene from './components/Scene/ThreeJSScene';
import IMUOverlay from './components/Overlay/IMUOverlay';
import CalibrationPanel from './components/Calibration/CalibrationPanel';
import EmptyStateInstructions from './components/Layout/EmptyStateInstructions';

// Hooks
import { useWebSocket } from './hooks/useWebSocket';
import { useDeviceData } from './hooks/useDeviceData';
import { useCalibration } from './hooks/useCalibration';

// Theme
const theme = {
  colorScheme: 'dark',
  colors: {
    dark: [
      '#d5d7e0',
      '#acaebf',
      '#8c8fa3',
      '#666980',
      '#4d4f66',
      '#34354a',
      '#2b2c3d',
      '#1d1e30',
      '#0c0d21',
      '#01010a',
    ],
  },
  primaryColor: 'green',
  fontFamily: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
};

function App() {
  // Device data management
  const { 
    devices, 
    selectedDevice, 
    setSelectedDevice, 
    processIMUData, 
    activeDevices,
    deviceCount 
  } = useDeviceData();
  
  // WebSocket message handler
  const handleWebSocketMessage = useCallback((message) => {
    processIMUData(message);
  }, [processIMUData]);
  
  // WebSocket connection
  const { 
    connectionStatus, 
    stats, 
    sendMessage, 
    isConnected 
  } = useWebSocket(handleWebSocketMessage);
  
  // Calibration management
  const {
    calibrationParams,
    handleCalibrationComplete,
    handleTPoseCalibrationComplete,
    handleCalibrationReset
  } = useCalibration(sendMessage);

  // Show calibration panel when device is selected
  const showCalibration = selectedDevice && isConnected;
  
  // Show empty state when connected but no devices
  const showEmptyState = isConnected && deviceCount === 0;

  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <Notifications position="top-right" />
      <AppShell
        header={{ height: 48 }}
        navbar={{ 
          width: 384, 
          breakpoint: 'md',
          collapsed: { mobile: true, desktop: false }
        }}
        padding={0}
      >
        <AppShell.Header>
          <ConnectionStatus 
            status={connectionStatus}
            deviceCount={deviceCount}
            stats={stats}
          />
        </AppShell.Header>

        <AppShell.Main style={{ display: 'flex' }}>
          <Box style={{ position: 'relative', flex: 1, height: '100%', overflow: 'hidden' }}>
            {/* 3D Scene */}
            <ThreeJSScene 
              devices={devices}
              selectedDevice={selectedDevice}
              onDeviceSelect={setSelectedDevice}
              calibrationParams={calibrationParams}
            />
            
            {/* Calibration Panel */}
            {showCalibration && (
              <CalibrationPanel
                selectedDevice={selectedDevice}
                devices={devices}
                onCalibrationComplete={handleCalibrationComplete}
                onTPoseCalibrationComplete={handleTPoseCalibrationComplete}
                onCalibrationReset={handleCalibrationReset}
                calibrationParams={calibrationParams}
              />
            )}
            
            {/* Empty State */}
            {showEmptyState && <EmptyStateInstructions />}
            
            {/* Loading Overlay */}
            <LoadingOverlay 
              visible={connectionStatus === 'reconnecting'} 
              overlayProps={{ radius: "sm", blur: 2 }}
              loaderProps={{ color: 'green' }}
            />
          </Box>
        </AppShell.Main>

        <AppShell.Navbar>
          <IMUOverlay 
            devices={devices}
            selectedDevice={selectedDevice}
            onDeviceSelect={setSelectedDevice}
            calibrationParams={calibrationParams}
          />
        </AppShell.Navbar>
      </AppShell>
    </MantineProvider>
  );
}

export default App;