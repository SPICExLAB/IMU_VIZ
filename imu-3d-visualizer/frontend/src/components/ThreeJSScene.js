import React, { useRef, useEffect, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Text, Box, Sphere, Cylinder } from '@react-three/drei';

// World Coordinate System Axes
function CoordinateAxes({ position = [0, 0, -1], scale = 1 }) {
  return (
    <group position={position}>
      {/* X axis - Red (Left in our world frame) */}
      <group>
        <Cylinder 
          args={[0.03, 0.03, scale, 8]}
          position={[scale / 2, 0, 0]}
          rotation={[0, 0, Math.PI / 2]}
        >
          <meshBasicMaterial color="#ef4444" />
        </Cylinder>
        <Text rotation={[0, Math.PI, 0]} position={[scale + 0.5, 0, 0]} fontSize={0.3} color="#ef4444">X (Left)</Text>
      </group>
      
      {/* Y axis - Green (Up in our world frame) */}
      <group>
        <Cylinder 
          args={[0.03, 0.03, scale, 8]}
          position={[0, scale / 2, 0]}
        >
          <meshBasicMaterial color="#22c55e" />
        </Cylinder>
        <Text rotation={[0, Math.PI, 0]} position={[0, scale + 0.5, 0]} fontSize={0.3} color="#22c55e">Y (Up)</Text>
      </group>
      
      {/* Z axis - Blue (Forward into screen in our world frame) */}
      <group>
        <Cylinder 
          args={[0.03, 0.03, scale, 8]}
          position={[0, 0, scale / 2]}
          rotation={[Math.PI / 2, 0, 0]}
        >
          <meshBasicMaterial color="#3b82f6" />
        </Cylinder>
        <Text rotation={[0, Math.PI, 0]} position={[0, 0, scale + 0.5]} fontSize={0.3} color="#3b82f6">Z (Forward)</Text>
      </group>
    </group>
  );
}

// iPhone and iWatch Device Local Frame Axes (shows device coordinate system)
function DeviceLocalFrame({ scale = 0.5 }) {
  return (
    <group position={[0, 0.3, 0]}> {/* Raised above the device mesh */}
      {/* Device X axis - Red (Screen Right, same as world X color) */}
      <Cylinder 
        args={[0.02, 0.02, scale, 6]}
        position={[-scale / 2, 0, 0]}
        rotation={[0, 0, Math.PI / 2]}
      >
        <meshBasicMaterial color="#ef4444" />
      </Cylinder>
      
      {/* Device Y axis - Green (Screen Up, same as world Y color) */}
      <Cylinder 
        args={[0.02, 0.02, scale, 6]}
        position={[0, 0, scale / 2]}
        rotation={[Math.PI / 2, 0, 0]}
      >
         <meshBasicMaterial color="#22c55e" />
      </Cylinder>
      
      {/* Device Z axis - Blue (Out of Screen, same as world Z color) */}
      <Cylinder 
        args={[0.02, 0.02, scale, 6]}
        position={[0, scale / 2, 0]}
        rotation={[0, 0, 0]}
      >
        <meshBasicMaterial color="#3b82f6" />
      </Cylinder>
    </group>
  );
}

// Rokid Local Frame Axes (shows device coordinate system)
function RokidLocalFrame({ scale = 0.5 }) {
  return (
    <group position={[0, -0.3, -0.2]}> {/* Raised above the device mesh */}
      {/* Device X axis - Red (Screen Right, same as world X color) */}
      <Cylinder 
        args={[0.02, 0.02, scale, 6]}
        position={[scale / 2, 0, 0]}
        rotation={[0, 0, Math.PI / 2]}
      >
        <meshBasicMaterial color="#ef4444" />
      </Cylinder>
      
      {/* Device Y axis - Green (Screen Up, same as world Y color) */}
      <Cylinder 
        args={[0.02, 0.02, scale, 6]}
        position={[0, -scale / 2, 0]}
        rotation={[0, 0, 0]}
      >
         <meshBasicMaterial color="#22c55e" />
      </Cylinder>
      
      {/* Device Z axis - Blue (Out of Screen, same as world Z color) */}
      <Cylinder 
        args={[0.02, 0.02, scale, 6]}
        position={[0, 0, -scale / 2]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <meshBasicMaterial color="#3b82f6" />
      </Cylinder>
    </group>
  );
}

// Device 3D Models
function PhoneModel({ position, device, isSelected, onClick }) {
  const meshRef = useRef();
  
  useFrame(() => {
    if (meshRef.current && device?.quaternion) {
      // Use calibrated quaternion if available, otherwise use default mapping
      if (device.calibratedQuaternion) {
        // When calibrated, the coordinates are already in world frame
        const [x, y, z, w] = device.calibratedQuaternion;
        meshRef.current.quaternion.set(x, y, z, w);
      } else {
        // Original mapping without calibration
        const [x, y, z, w] = device.quaternion;
        meshRef.current.quaternion.set(-x, z, y, w);
      }
    }
  });

  return (
    <group position={position} onClick={onClick}>
      <group ref={meshRef}>
        {/* Phone body */}
        <Box 
          args={[1.4, 0.15, 2.8]} 
          position={[0, 0, 0]}
        >
          <meshStandardMaterial 
            color={isSelected ? '#4ade80' : '#374151'} 
            roughness={0.4}
            metalness={0.3}
          />
        </Box>
        
        {/* Screen (top face - white) */}
        <Box 
          args={[1.2, 0.02, 2.4]} 
          position={[0, 0.09, 0]}
        >
          <meshStandardMaterial 
            color="#AFBEDC"
            roughness={0.1}
            metalness={0.1}
            emissive="#f3f4f6"
            emissiveIntensity={0.1}
          />
        </Box>
        
        {/* Device Local Frame Axes - Child of rotating group, raised above mesh */}
        <DeviceLocalFrame scale={0.8} />
      </group>
      
      {/* Device Label - Outside rotating group */}
      <Text
        rotation={[0, Math.PI, 0]}
        position={[0, -1.5, -2]}
        fontSize={0.3}
        color={isSelected ? '#10b981' : '#9ca3af'}
        anchorX="center"
        anchorY="middle"
      >
        iPhone
      </Text>
    </group>
  );
}

function WatchModel({ position, device, isSelected, onClick }) {
  const meshRef = useRef();
  
  useFrame(() => {
    if (meshRef.current && device?.quaternion) {
      // Use calibrated quaternion if available, otherwise use default mapping
      if (device.calibratedQuaternion) {
        // When calibrated, the coordinates are already in world frame
        const [x, y, z, w] = device.calibratedQuaternion;
        meshRef.current.quaternion.set(x, y, z, w);
      } else {
        // Original mapping without calibration
        const [x, y, z, w] = device.quaternion;
        meshRef.current.quaternion.set(-x, z, y, w);
      }
    }
  });

  return (
    <group position={position} onClick={onClick}>
      <group ref={meshRef}>
        {/* Watch body */}
        <Cylinder 
          args={[0.6, 0.6, 0.3, 8]} 
          position={[0, 0, 0]}
        >
          <meshStandardMaterial 
            color={isSelected ? '#f59e0b' : '#6b7280'} 
            roughness={0.3}
            metalness={0.7}
          />
        </Cylinder>
        
        {/* Watch screen (top face - white) */}
        <Cylinder 
          args={[0.5, 0.5, 0.02, 8]} 
          position={[0, 0.16, 0]}
        >
          <meshStandardMaterial 
            color="#f9fafb"
            roughness={0.1}
            metalness={0.1}
            emissive="#f3f4f6"
            emissiveIntensity={0.1}
          />
        </Cylinder>
        
        {/* Device Local Frame Axes - Child of rotating group, raised above mesh */}
        <DeviceLocalFrame scale={0.6} />
      </group>
      
      {/* Device Label - Outside rotating group */}
      <Text
        rotation={[0, Math.PI, 0]}
        position={[0, -1, 0]}
        fontSize={0.3}
        color={isSelected ? '#f59e0b' : '#9ca3af'}
        anchorX="center"
        anchorY="middle"
      >
        Watch
      </Text>
    </group>
  );
}

function HeadphoneModel({ position, device, isSelected, onClick }) {
  const meshRef = useRef();

  useFrame(() => {
    if (meshRef.current && device?.quaternion) {
      // Use calibrated quaternion if available, otherwise use default mapping
      if (device.calibratedQuaternion) {
        // When calibrated, the coordinates are already in world frame
        const [x, y, z, w] = device.calibratedQuaternion;
        meshRef.current.quaternion.set(x, y, z, w);
      } else {
        // Original mapping without calibration
        const [x, y, z, w] = device.quaternion;
        meshRef.current.quaternion.set(x, z, -y, w);
      }
    }
  });

  const isGlasses = device.device_name === 'glasses' || device.device_name === 'headphone';
  const color = isSelected ? '#8b5cf6' : '#6b7280';
  const label = isGlasses ? 'AR Glasses' : 'AirPods';

  return (
    <group position={position} onClick={onClick}>
      <group ref={meshRef}>
        {/* rougly a glass shape when in identity: x alignes world world x, y = world -y, z = world -z  */}
        {isGlasses && (
          <>
            <Box args={[1.5, 0.1, 0.1]} position={[0, -0.3, 0]}>
              <meshStandardMaterial color={color} />
            </Box>
            <Box args={[0.1, 0.3, 0.8]} position={[-0.7, 0, 0.2]} rotation={[Math.PI / 2, 0, 0]}>
              <meshStandardMaterial color={color} />
            </Box>
            <Box args={[0.1, 0.3, 0.8]} position={[0.7, 0, 0.2]} rotation={[Math.PI / 2, 0, 0]}>
              <meshStandardMaterial color={color} />
            </Box>
          </>
        )}
        
        {/* Device Local Frame Axes - Child of rotating group, raised above mesh */}
        <RokidLocalFrame scale={0.6} />
      </group>
      
      {/* Device Label - Outside rotating group */}
      <Text
        rotation={[0, Math.PI, 0]}
        position={[0, -1, 0]}
        fontSize={0.3}
        color={isSelected ? '#8b5cf6' : '#9ca3af'}
        anchorX="center"
        anchorY="middle"
      >
        {label}
      </Text>
    </group>
  );
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

// Camera Controls Component
function CameraController() {
  const { camera } = useThree();
  
  useEffect(() => {
    // Set initial camera position
    camera.position.set(2, 6, -10);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  return null;
}

// Main Scene Component
function Scene({ devices, selectedDevice, onDeviceSelect }) {
  const [showAxes] = useState(true);

  const activeDevices = Object.values(devices).filter(device => device.isActive);

  const handleDeviceClick = (deviceKey) => {
    onDeviceSelect(selectedDevice === deviceKey ? null : deviceKey);
  };

  return (
    <>
      {/* Camera Controls */}
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
  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Canvas
        camera={{ position: [8, 6, -8], fov: 60 }}
        style={{ background: '#111827' }}
      >
        <Scene 
          devices={devices}
          selectedDevice={selectedDevice}
          onDeviceSelect={onDeviceSelect}
          calibrationParams={calibrationParams}
        />
      </Canvas>
    </div>
  );
}