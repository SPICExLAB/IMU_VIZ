import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text, Box, Cylinder } from '@react-three/drei';
import { DeviceLocalFrame } from './CoordinateSystem';

// Phone Model
export function PhoneModel({ position, device, isSelected, onClick, calibrationParams }) {
  const meshRef = useRef();
  
  useFrame(() => {
    if (meshRef.current && device) {
      // After calibration, use the world frame quaternion directly
      if (calibrationParams?.isCalibrated && device.worldFrameQuatForViz) {
        const [x, y, z, w] = device.worldFrameQuatForViz;
        meshRef.current.quaternion.set(x, y, z, w);
      
      } else if (device.quaternion) {
        // Before calibration: apply device-specific transform
        const [x, y, z, w] = device.quaternion;
        meshRef.current.quaternion.set(-x, z, y, w);
      }
    }
  });

  return (
    <group position={position} onClick={onClick}>
      <group ref={meshRef}>
        {/* Phone body */}
        <Box args={[1.4, 0.15, 2.8]} position={[0, 0, 0]}>
          <meshStandardMaterial 
            color={isSelected ? '#4ade80' : '#374151'} 
            roughness={0.4}
            metalness={0.3}
          />
        </Box>
        
        {/* Screen */}
        <Box args={[1.2, 0.02, 2.4]} position={[0, 0.09, 0.2]}>
          <meshStandardMaterial 
            color="#AFBEDC"
            roughness={0.1}
            metalness={0.1}
            emissive="#f3f4f6"
            emissiveIntensity={0.1}
          />
        </Box>
        
        <DeviceLocalFrame scale={0.8} />
      </group>
      
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

// Watch Model
export function WatchModel({ position, device, isSelected, onClick, calibrationParams }) {
  const meshRef = useRef();
  
  useFrame(() => {
    if (meshRef.current && device) {
      if (calibrationParams?.isCalibrated && device.worldFrameQuatForViz) {
        const [x, y, z, w] = device.worldFrameQuatForViz;
        meshRef.current.quaternion.set(x, y, z, w);
      } else if (device.quaternion) {
        const [x, y, z, w] = device.quaternion;
        meshRef.current.quaternion.set(-x, z, y, w);
      }
    }
  });

  return (
    <group position={position} onClick={onClick}>
      <group ref={meshRef}>
        {/* Watch body */}
        <Cylinder args={[0.6, 0.6, 0.3, 8]} position={[0, 0, 0]}>
          <meshStandardMaterial 
            color={isSelected ? '#f59e0b' : '#6b7280'} 
            roughness={0.3}
            metalness={0.7}
          />
        </Cylinder>
        
        {/* Watch screen */}
        <Cylinder args={[0.5, 0.5, 0.02, 8]} position={[0, 0.16, 0]}>
          <meshStandardMaterial 
            color="#f9fafb"
            roughness={0.1}
            metalness={0.1}
            emissive="#f3f4f6"
            emissiveIntensity={0.1}
          />
        </Cylinder>
        
        <DeviceLocalFrame scale={0.6} />
      </group>
      
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

// Headphone/Glasses Model
export function HeadphoneModel({ position, device, isSelected, onClick, calibrationParams }) {
  const meshRef = useRef();

  useFrame(() => {
    if (meshRef.current && device) {
      if (calibrationParams?.isCalibrated && device.worldFrameQuatForViz) {
        const [x, y, z, w] = device.worldFrameQuatForViz;
        meshRef.current.quaternion.set(x, y, z, w);
      } else if (device.quaternion) {
        const [x, y, z, w] = device.quaternion;
        meshRef.current.quaternion.set(-x, z, y, w);
      }
    }
  });

  const isActuallyGlasses = device.device_type === 'ar_glasses';
  const color = isSelected ? '#8b5cf6' : '#6b7280';
  const label = isActuallyGlasses ? 'AR Glasses' : 'AirPods';

  return (
    <group position={position} onClick={onClick}>
      <group ref={meshRef}>
        {/* Glasses model */}
        <Box args={[1.5, 0.1, 0.1]} position={[0, 0.2, 0]}>
          <meshStandardMaterial color={color} />
        </Box>
        <Box args={[0.1, 0.3, 0.8]} position={[-0.7, 0, -0.3]} >
          <meshStandardMaterial color={color} />
        </Box>
        <Box args={[0.1, 0.3, 0.8]} position={[0.7, 0, -0.3]} >
          <meshStandardMaterial color={color} />
        </Box>
        
        <DeviceLocalFrame scale={0.6} />
      </group>
      
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