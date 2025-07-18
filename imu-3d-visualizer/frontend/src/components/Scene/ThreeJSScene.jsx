import React, { useRef, useEffect, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Text, Box, Sphere, Cylinder } from '@react-three/drei';
import { ActionIcon, Group } from '@mantine/core';
import { Eye, EyeOff } from 'lucide-react';

// Device Models
import { PhoneModel, WatchModel, HeadphoneModel } from './DeviceModels';
import { CoordinateAxes, DeviceLocalFrame } from './CoordinateSystem';

// Camera Controls Component
function CameraController() {
  const { camera } = useThree();
  
  useEffect(() => {
    camera.position.set(2, 6, -10);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  return null;
}

// Helper function to get device position in 3D space
function getDevicePosition(deviceName, deviceId) {
  const positions = {
    'phone': [3, 0, 0],
    'watch': [0, 0, 0], 
    'headphone': [-3, 0, 0],
    'glasses': [-3, 0, 0]
  };
  
  return positions[deviceName] || [deviceId * 2 - 3, 0, 0];
}

// Main Scene Component
function Scene({ devices, selectedDevice, onDeviceSelect, calibrationParams, showAxes }) {
  const activeDevices = Object.values(devices).filter(device => device.isActive);

  const handleDeviceClick = (deviceKey) => {
    onDeviceSelect(selectedDevice === deviceKey ? null : deviceKey);
  };

  return (
    <>
      <CameraController />
      <OrbitControls 
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={3}
        maxDistance={20}
        maxPolarAngle={Math.PI / 2 + 0.5}
      />

      {/* Lighting */}
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 10, 5]} intensity={1} />
      <directionalLight position={[-10, 5, -5]} intensity={0.5} />
      <pointLight position={[0, 10, 0]} intensity={0.8} color="#ffffff" />
      <pointLight position={[5, -5, 5]} intensity={0.4} color="#4f46e5" />

      {/* World Grid */}
      <Grid 
        position={[0, -2, 0]} 
        args={[20, 20]} 
        cellSize={1} 
        cellThickness={0.5} 
        cellColor="#374151" 
        sectionSize={5} 
        sectionThickness={1} 
        sectionColor="#6b7280" 
        fadeDistance={25} 
        fadeStrength={1} 
      />

      {/* Coordinate System */}
      {showAxes && <CoordinateAxes position={[0, 0, 3]} scale={2} />}

      {/* Device Models */}
      {activeDevices.map(device => {
        const deviceKey = `${device.device_name}_${device.device_id}`;
        const position = getDevicePosition(device.device_name, device.device_id);
        const isSelected = selectedDevice === deviceKey;

        switch (device.device_name) {
          case 'phone':
          case 'iphone':
            return (
              <PhoneModel
                key={deviceKey}
                position={position}
                device={device}
                isSelected={isSelected}
                onClick={() => handleDeviceClick(deviceKey)}
                calibrationParams={calibrationParams}
              />
            );
          
          case 'watch':
          case 'applewatch':
            return (
              <WatchModel
                key={deviceKey}
                position={position}
                device={device}
                isSelected={isSelected}
                onClick={() => handleDeviceClick(deviceKey)}
                calibrationParams={calibrationParams}
              />
            );
          
          case 'headphone':
          case 'glasses':
          case 'airpods':
          case 'arglasses':
            return (
              <HeadphoneModel
                key={deviceKey}
                position={position}
                device={device}
                isSelected={isSelected}
                onClick={() => handleDeviceClick(deviceKey)}
                calibrationParams={calibrationParams}
              />
            );
          
          default:
            return (
              <Sphere
                key={deviceKey}
                position={position}
                args={[0.5]}
                onClick={() => handleDeviceClick(deviceKey)}
              >
                <meshStandardMaterial 
                  color={isSelected ? '#10b981' : '#6b7280'} 
                />
              </Sphere>
            );
        }
      })}
    </>
  );
}

// Main ThreeJS Scene Component
export default function ThreeJSScene({ devices, selectedDevice, onDeviceSelect, calibrationParams }) {
  const [showAxes, setShowAxes] = useState(true);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <Canvas
        camera={{ position: [8, 6, -8], fov: 60 }}
        style={{ background: '#111827' }}
      >
        <Scene 
          devices={devices}
          selectedDevice={selectedDevice}
          onDeviceSelect={onDeviceSelect}
          calibrationParams={calibrationParams}
          showAxes={showAxes}
        />
      </Canvas>
      
      {/* Scene Controls */}
      <Group 
        style={{ 
          position: 'absolute', 
          top: 16, 
          right: 16,
          zIndex: 100
        }}
      >
        <ActionIcon 
          size="lg" 
          variant="filled" 
          color="dark.5"
          onClick={() => setShowAxes(!showAxes)}
          title={showAxes ? 'Hide Axes' : 'Show Axes'}
        >
          {showAxes ? <EyeOff size={20} /> : <Eye size={20} />}
        </ActionIcon>
      </Group>
    </div>
  );
}