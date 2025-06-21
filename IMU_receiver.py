#!/usr/bin/env python3
"""
IMU_receiver.py - Clean IMU Receiver for iOS Devices with Apple Watch Gyroscope Support

Features:
- MobilePoser-style Calibration (set current orientation as reference)
- Apple Watch gyroscope data support
- Enhanced iOS data parsing
- Clean visualization without problematic icons
"""

import socket
import numpy as np
import threading
import time
import queue
from collections import deque
from dataclasses import dataclass
import logging

# Import our refactored visualization module
from UI.main_visualizer import IMUVisualizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IMUData:
    """IMU data structure for iOS devices"""
    timestamp: float
    device_id: str
    accelerometer: np.ndarray  # [ax, ay, az] in m/s²
    gyroscope: np.ndarray      # [gx, gy, gz] in rad/s (Apple Watch support)
    quaternion: np.ndarray     # [x, y, z, w] from iOS
    euler: np.ndarray = None   # [roll, pitch, yaw] (optional)

class MobilePoseCalibrator:
    """MobilePoser-style calibration: Set current orientation as reference"""
    
    def __init__(self):
        # Store reference quaternions for each device (the "zero" position)
        self.reference_quaternions = {}
        
    def set_reference_orientation(self, device_id: str, current_quaternion: np.ndarray):
        """Set current orientation as the reference/zero position (MobilePoser style)"""
        # Store the current quaternion as reference
        self.reference_quaternions[device_id] = current_quaternion.copy()
        logger.info(f"Set reference orientation for {device_id}")
        logger.info(f"   Reference quat: [{current_quaternion[0]:.3f}, {current_quaternion[1]:.3f}, {current_quaternion[2]:.3f}, {current_quaternion[3]:.3f}]")
    
    def get_relative_orientation(self, device_id: str, current_quaternion: np.ndarray) -> np.ndarray:
        """Get orientation relative to the reference position"""
        if device_id not in self.reference_quaternions:
            # No reference set, return current orientation
            return current_quaternion
        
        # Calculate relative orientation: q_relative = q_reference^-1 * q_current
        ref_quat = self.reference_quaternions[device_id]
        
        # Quaternion inverse (conjugate for unit quaternions)
        ref_quat_inv = np.array([-ref_quat[0], -ref_quat[1], -ref_quat[2], ref_quat[3]])
        
        # Quaternion multiplication: q1 * q2
        relative_quat = self._quaternion_multiply(ref_quat_inv, current_quaternion)
        
        return relative_quat
    
    def _quaternion_multiply(self, q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
        """Multiply two quaternions (x,y,z,w format)"""
        x1, y1, z1, w1 = q1
        x2, y2, z2, w2 = q2
        
        return np.array([
            w1*x2 + x1*w2 + y1*z2 - z1*y2,  # x
            w1*y2 - x1*z2 + y1*w2 + z1*x2,  # y  
            w1*z2 + x1*y2 - y1*x2 + z1*w2,  # z
            w1*w2 - x1*x2 - y1*y2 - z1*z2   # w
        ])
    
    def calibrate_all_devices(self, current_orientations: dict):
        """Calibrate all devices at once (set all current orientations as reference)"""
        calibrated_devices = []
        for device_id, quaternion in current_orientations.items():
            self.set_reference_orientation(device_id, quaternion)
            calibrated_devices.append(device_id)
        
        if calibrated_devices:
            logger.info(f"Calibrated devices: {', '.join(calibrated_devices)}")
        else:
            logger.warning("No active devices to calibrate")

class EnhancedIMUReceiver:
    """Enhanced IMU receiver for iOS devices with Apple Watch gyroscope support"""
    
    def __init__(self, port=8001):
        self.port = port
        self.socket = None
        self.running = False
        self.data_queue = queue.Queue()
        
        # Core components
        self.calibrator = MobilePoseCalibrator()
        self.visualizer = IMUVisualizer()
        
        # Current device orientations (for calibration)
        self.current_orientations = {}
        
        logger.info(f"Enhanced IMU Receiver for iOS devices initialized on port {port}")
    
    def start_server(self):
        """Start UDP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.settimeout(0.1)
            
            logger.info(f"UDP server started on port {self.port}")
            self.running = True
            
            # Start receiver thread
            receiver_thread = threading.Thread(target=self._receive_loop)
            receiver_thread.daemon = True
            receiver_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
    
    def _receive_loop(self):
        """Receive and parse UDP data"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = data.decode('utf-8').strip()
                self._parse_ios_data(message, addr)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Receive error: {e}")
    
    def _parse_ios_data(self, message, addr):
        """Parse iOS SensorTracker data format"""
        try:
            # Handle system messages
            if message == "client_initialized":
                logger.info(f"iOS device connected from {addr[0]}")
                return
            elif message == "client_disconnected":
                logger.info(f"iOS device disconnected")
                return
            
            # Parse device data: "ios-device;device_type:data"
            if ';' in message:
                device_prefix, data_part = message.split(';', 1)
                
                if data_part.startswith('phone:'):
                    self._parse_phone_data(data_part[6:])
                elif data_part.startswith('headphone:'):
                    self._parse_headphone_data(data_part[10:])
                elif data_part.startswith('watch:'):
                    self._parse_watch_data(data_part[6:])
                    
        except Exception as e:
            logger.warning(f"Parse error: {e}")
    
    def _parse_phone_data(self, data):
        """Parse phone data: timestamp timestamp userAccel.x y z quat.x y z w roll pitch yaw"""
        try:
            parts = data.split()
            if len(parts) >= 11:
                timestamp = float(parts[0])
                
                # User acceleration (m/s²)
                accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                
                # Quaternion from iOS (x, y, z, w format)
                quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                
                # Convert iOS quaternion to standard orientation
                quat_corrected = self._convert_ios_quaternion(quat)
                
                # Euler angles if available
                euler = None
                if len(parts) >= 12:
                    euler = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
                
                # Phone doesn't send gyroscope data separately - set to zero
                gyro = np.array([0.0, 0.0, 0.0])
                
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='phone',
                    accelerometer=accel,
                    gyroscope=gyro,
                    quaternion=quat_corrected,
                    euler=euler
                )
                
                self.data_queue.put(imu_data)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Phone data parse error: {e}")
    
    def _parse_headphone_data(self, data):
        """Parse headphone data (AirPods)"""
        try:
            parts = data.split()
            if len(parts) >= 9:
                timestamp = float(parts[0])
                accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                quat_corrected = self._convert_ios_quaternion(quat)
                
                # AirPods don't typically send gyroscope data
                gyro = np.array([0.0, 0.0, 0.0])
                
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='headphone',
                    accelerometer=accel,
                    gyroscope=gyro,
                    quaternion=quat_corrected
                )
                
                self.data_queue.put(imu_data)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Headphone data parse error: {e}")
    
    def _parse_watch_data(self, data):
        """Parse Apple Watch data: timestamp deviceTimestamp accX accY accZ quatX quatY quatZ quatW gyroX gyroY gyroZ"""
        try:
            parts = data.split()
            
            # New Apple Watch format: timestamp deviceTimestamp accX accY accZ quatX quatY quatZ quatW gyroX gyroY gyroZ
            if len(parts) >= 12:
                # Parse timestamps
                timestamp = float(parts[0])
                device_timestamp = float(parts[1])
                
                # Parse accelerometer data (m/s²)
                accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                
                # Parse quaternion (x, y, z, w format)
                quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                quat_corrected = self._convert_ios_quaternion(quat)
                
                # Parse gyroscope data (rad/s)
                gyro = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
                
                # Log successful Apple Watch data reception
                logger.debug(f"Apple Watch data - Accel: [{accel[0]:.3f}, {accel[1]:.3f}, {accel[2]:.3f}], "
                           f"Gyro: [{gyro[0]:.3f}, {gyro[1]:.3f}, {gyro[2]:.3f}]")
                
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='watch',
                    accelerometer=accel,
                    gyroscope=gyro,
                    quaternion=quat_corrected
                )
                
                self.data_queue.put(imu_data)
                
            else:
                logger.warning(f"Apple Watch data incomplete: expected 12 parts, got {len(parts)}")
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Watch data parse error: {e} - Data: {data}")
    
    def _convert_ios_quaternion(self, ios_quat: np.ndarray) -> np.ndarray:
        """Convert iOS quaternion to standard 3D graphics convention"""
        # iOS Core Motion quaternion handling
        # For most cases, iOS quaternions can be used directly
        # May need coordinate system adjustments based on device orientation
        
        # Apply any necessary coordinate system transformations here
        # For now, return as-is - adjust in visualization if needed
        return ios_quat
    
    def calibrate_all_devices(self):
        """Calibrate all active devices (MobilePoser style)"""
        self.calibrator.calibrate_all_devices(self.current_orientations)
    
    def process_data(self):
        """Process incoming IMU data"""
        while not self.data_queue.empty():
            imu_data = self.data_queue.get()
            
            # Store current orientation for calibration
            self.current_orientations[imu_data.device_id] = imu_data.quaternion
            
            # Get relative orientation (after calibration)
            relative_quat = self.calibrator.get_relative_orientation(imu_data.device_id, imu_data.quaternion)
            
            # Create processed data with relative orientation
            processed_data = IMUData(
                timestamp=imu_data.timestamp,
                device_id=imu_data.device_id,
                accelerometer=imu_data.accelerometer,
                gyroscope=imu_data.gyroscope,  # Include gyroscope data (especially for Apple Watch)
                quaternion=relative_quat,
                euler=imu_data.euler
            )
            
            # Check if device is calibrated
            is_calibrated = imu_data.device_id in self.calibrator.reference_quaternions
            
            # Update visualization
            self.visualizer.update_device_data(processed_data, is_calibrated)
            
            # Log gyroscope data for Apple Watch
            if imu_data.device_id == 'watch' and np.linalg.norm(imu_data.gyroscope) > 0.001:
                logger.debug(f"Apple Watch active - Gyro magnitude: {np.linalg.norm(imu_data.gyroscope):.3f}, "
                           f"Accel magnitude: {np.linalg.norm(imu_data.accelerometer):.3f}")
    
    def run(self):
        """Main application loop"""
        self.start_server()
        
        try:
            while self.running:
                # Handle visualization events
                event = self.visualizer.handle_events()
                
                if event == "quit":
                    self.running = False
                elif event == "calibrate":
                    self.calibrate_all_devices()
                
                # Process incoming data
                self.process_data()
                
                # Render visualization
                self.visualizer.render()
        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        
        finally:
            self.running = False
            if self.socket:
                self.socket.close()
            self.visualizer.cleanup()

def main():
    receiver = EnhancedIMUReceiver(port=8001)
    receiver.run()

if __name__ == "__main__":
    main()