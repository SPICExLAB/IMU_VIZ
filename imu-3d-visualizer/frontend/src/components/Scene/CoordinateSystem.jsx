import React from 'react';
import { Text, Cylinder } from '@react-three/drei';

// World Coordinate System Axes
export function CoordinateAxes({ position = [0, 0, -1], scale = 1 }) {
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

// Device Local Frame Axes (shows device coordinate system)
export function DeviceLocalFrame({ scale = 0.5 }) {
  return (
    <group position={[0, 0.3, 0]}>
      {/* Device X axis - Red */}
      <Cylinder 
        args={[0.02, 0.02, scale, 6]}
        position={[-scale / 2, 0, 0]}
        rotation={[0, 0, Math.PI / 2]}
      >
        <meshBasicMaterial color="#ef4444" />
      </Cylinder>
      
      {/* Device Y axis - Green */}
      <Cylinder 
        args={[0.02, 0.02, scale, 6]}
        position={[0, 0, scale / 2]}
        rotation={[Math.PI / 2, 0, 0]}
      >
         <meshBasicMaterial color="#22c55e" />
      </Cylinder>
      
      {/* Device Z axis - Blue */}
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