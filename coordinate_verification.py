#!/usr/bin/env python3
"""
Coordinate System Verification Script - Updated for Quaternion Component Flipping
Based on your IMU analyzer code to verify Unity coordinate conversion
"""

import socket
import numpy as np
from scipy.spatial.transform import Rotation as R
import time

class CoordinateVerifier:
    def __init__(self, port=8001):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        print(f"🎯 Coordinate System Verifier listening on port {self.port}")
        print("\nExpected Python Reference Coordinate System:")
        print("  X: Right (+ when tilting head right)")
        print("  Y: Up (+ when looking up)")  
        print("  Z: Toward user (+ when tilting forward)")
        print("\nTesting quaternion component flipping from Unity...")
        print("="*60)
    
    def parse_data(self, data_str):
        """Parse Unity data: timestamp device_timestamp quat_x quat_y quat_z quat_w acc_x acc_y acc_z gyro_x gyro_y gyro_z"""
        try:
            parts = data_str.strip().split()
            if len(parts) != 12:
                return None
                
            return {
                'timestamp': float(parts[0]),
                'device_time': float(parts[1]),
                'quaternion': np.array([float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])]),
                'acceleration': np.array([float(parts[6]), float(parts[7]), float(parts[8])]),
                'gyroscope': np.array([float(parts[9]), float(parts[10]), float(parts[11])])
            }
        except (ValueError, IndexError):
            return None
    
    def quaternion_to_euler(self, quat):
        """Convert quaternion to Euler angles in degrees"""
        try:
            r = R.from_quat(quat)
            euler_rad = r.as_euler('xyz', degrees=False)
            return euler_rad * 180.0 / np.pi
        except:
            return np.array([0, 0, 0])
    
    def analyze_data(self, data):
        """Analyze the coordinate system with quaternion component flipping"""
        # Convert quaternion to Euler for intuitive understanding
        euler = self.quaternion_to_euler(data['quaternion'])
        
        # Extract components
        acc = data['acceleration']
        gyro = data['gyroscope']
        quat = data['quaternion']
        
        print(f"\n⏰ Time: {data['timestamp']:.3f}")
        
        print(f"📊 RAW QUATERNION (after Unity remapping):")
        print(f"   X: {quat[0]:8.3f} (flipped from original)")
        print(f"   Y: {quat[1]:8.3f} (unchanged)")
        print(f"   Z: {quat[2]:8.3f} (flipped from original)")
        print(f"   W: {quat[3]:8.3f} (unchanged)")
        
        print(f"📐 ROTATION (Euler from remapped quaternion):")
        print(f"   X-rotation (NOD):  {euler[0]:8.1f}° (around Right axis = up/down movement)")
        print(f"   Y-rotation (TURN): {euler[1]:8.1f}° (around Up axis = left/right rotation)")
        print(f"   Z-rotation (TILT): {euler[2]:8.1f}° (around Backward axis = left/right tilt)")
        
        print(f"🚀 ACCELERATION (remapped in Unity):")
        print(f"   X (right):     {acc[0]:8.3f} m/s² (should be + when tilting right)")
        print(f"   Y (up):        {acc[1]:8.3f} m/s² (should be ~9.8 when level)")
        print(f"   Z (backward):  {acc[2]:8.3f} m/s² (should be + when tilting backward)")
        print(f"   Magnitude:     {np.linalg.norm(acc):.3f} m/s²")
        
        print(f"🔄 GYROSCOPE (remapped in Unity):")
        print(f"   X (nod rate):  {gyro[0]:8.3f} rad/s")
        print(f"   Y (tilt rate): {gyro[1]:8.3f} rad/s")
        print(f"   Z (turn rate): {gyro[2]:8.3f} rad/s")
        
        # Coordinate system verification
        print(f"✅ VERIFICATION:")
        
        # Check gravity direction (should be in +Y when level)
        if abs(acc[1]) > 8.0:  # Strong Y component suggests gravity
            if acc[1] > 0:
                print(f"   ✅ Gravity in +Y direction (correct when level)")
            else:
                print(f"   ⚠️  Gravity in -Y direction (upside down?)")
        else:
            print(f"   ⚠️  No strong gravity component detected")
        
        # Check if head is level (Euler angles should be small)
        if abs(euler[0]) < 20 and abs(euler[1]) < 20 and abs(euler[2]) < 20:
            print(f"   ✅ Head position appears reasonable")
            if abs(euler[0]) < 5 and abs(euler[2]) < 5:
                print(f"   ✅ Head appears level (NOD≈0°, TILT≈0°)")
        else:
            print(f"   📍 Significant head orientation: NOD={euler[0]:.1f}° TURN={euler[1]:.1f}° TILT={euler[2]:.1f}°")
        
        # Check quaternion magnitude (should be ~1.0)
        quat_mag = np.linalg.norm(quat)
        if abs(quat_mag - 1.0) < 0.1:
            print(f"   ✅ Quaternion magnitude: {quat_mag:.3f} (good)")
        else:
            print(f"   ⚠️  Quaternion magnitude: {quat_mag:.3f} (should be ~1.0)")
        
        print("-" * 60)
    
    def run(self):
        """Main verification loop"""
        print("\n🎮 Starting quaternion component flip verification...")
        print("Put on glasses and move your head to test:")
        print("  - Look up/down → Should see changes in NOD (X-rotation)")
        print("  - Turn left/right → Should see changes in TURN (Y-rotation)")  
        print("  - Tilt left/right → Should see changes in TILT (Z-rotation)")
        print("  - All should start from reasonable values when level")
        print("\nPress Ctrl+C to stop\n")
        
        last_display_time = time.time()
        
        try:
            while True:
                data, addr = self.sock.recvfrom(1024)
                data_str = data.decode('utf-8')
                
                parsed_data = self.parse_data(data_str)
                if parsed_data is None:
                    continue
                
                # Display analysis every second
                current_time = time.time()
                if current_time - last_display_time > 1.0:
                    self.analyze_data(parsed_data)
                    last_display_time = current_time
                    
        except KeyboardInterrupt:
            print("\n\n🏁 Coordinate system verification stopped")
            print("If NOD/TURN/TILT values are reasonable when level,")
            print("the quaternion component flipping is working correctly!")
        finally:
            self.sock.close()

def main():
    print("🧪 Rokid Glasses Quaternion Component Flip Verification")
    print("=" * 60)
    print("This verifies that Unity's quaternion component flipping")
    print("correctly converts coordinates to your Python reference system")
    print("(X=right, Y=up, Z=toward user)")
    
    verifier = CoordinateVerifier()
    verifier.run()

if __name__ == "__main__":
    main()