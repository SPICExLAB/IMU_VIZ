#!/usr/bin/env python3
"""
IMU_receiver.py - Enhanced IMU Receiver for iOS Devices + AR Glasses Support

Features:
- MobilePoser-style Calibration (set current orientation as reference)
- Apple Watch gyroscope data support
- AR Glasses support (Unity/Rokid data format)
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
    """IMU data structure for iOS devices and AR glasses"""
    timestamp: float
    device_id: str
    accelerometer: np.ndarray  # [ax, ay, az] in m/s²
    gyroscope: np.ndarray      # [gx, gy, gz] in rad/s
    quaternion: np.ndarray     # [x, y, z, w] from iOS/Unity
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
    """Enhanced IMU receiver for iOS devices + AR Glasses with gyroscope support"""
    
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
        
        # Device detection - track IP addresses for device assignment
        self.device_ip_mapping = {}
        self.next_device_assignment = ['phone', 'watch', 'glasses']  # Assignment order
        self.assignment_index = 0
        
        logger.info(f"Enhanced IMU Receiver for iOS devices + AR Glasses initialized on port {port}")
    
    def start_server(self):
        """Start UDP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.settimeout(0.1)
            
            logger.info(f"UDP server started on port {self.port}")
            logger.info("Waiting for data from:")
            logger.info("  - iOS devices (phone/watch)")
            logger.info("  - AR Glasses (Unity app)")
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
                self._parse_data(message, addr)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Receive error: {e}")
    
    def _parse_data(self, message, addr):
        """Parse data from different sources (iOS or AR Glasses)"""
        try:
            # Handle iOS system messages
            if message == "client_initialized":
                logger.info(f"iOS device connected from {addr[0]}")
                return
            elif message == "client_disconnected":
                logger.info(f"iOS device disconnected")
                return
            
            # Check if it's iOS format (contains ';' and device prefixes)
            if ';' in message and ('phone:' in message or 'headphone:' in message or 'watch:' in message):
                self._parse_ios_data(message, addr)
            else:
                # Assume it's AR Glasses Unity format
                self._parse_ar_glasses_data(message, addr)
                    
        except Exception as e:
            logger.warning(f"Parse error: {e}")
    
    def _parse_ios_data(self, message, addr):
        """Parse iOS SensorTracker data format"""
        try:
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
            logger.warning(f"iOS parse error: {e}")
    
    def _parse_ar_glasses_data(self, message, addr):
        """Parse AR Glasses Unity data format: timestamp device_timestamp acc_x acc_y acc_z quat_x quat_y quat_z quat_w gyro_x gyro_y gyro_z"""
        try:
            parts = message.split()
            if len(parts) != 12:
                logger.warning(f"AR Glasses data format error: expected 12 values, got {len(parts)}")
                return
                
            # Parse Unity format data
            timestamp = float(parts[0])
            device_timestamp = float(parts[1])
            
            # Parse accelerometer data (m/s²) - RAW, no conversion
            accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
            
            # Parse quaternion (x, y, z, w format) - RAW, no conversion
            quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
            
            # Parse gyroscope data (rad/s) - RAW, no conversion
            gyro = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
            
            # Assign device ID based on IP address
            device_id = self._get_device_id_for_ip(addr[0], 'glasses')
            
            # Log raw data to debug
            logger.info(f"AR Glasses RAW data - Device: {device_id}")
            logger.info(f"  Accel: [{accel[0]:.3f}, {accel[1]:.3f}, {accel[2]:.3f}]")
            logger.info(f"  Gyro: [{gyro[0]:.3f}, {gyro[1]:.3f}, {gyro[2]:.3f}]")
            logger.info(f"  Quat: [{quat[0]:.3f}, {quat[1]:.3f}, {quat[2]:.3f}, {quat[3]:.3f}]")
            
            imu_data = IMUData(
                timestamp=timestamp,
                device_id=device_id,
                accelerometer=accel,  # Raw data
                gyroscope=gyro,       # Raw data
                quaternion=quat       # Raw data
            )
            
            self.data_queue.put(imu_data)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"AR Glasses data parse error: {e} - Data: {message}")
    
    def _get_device_id_for_ip(self, ip_address, preferred_type='glasses'):
        """Get device ID for an IP address, assigning new ones as needed"""
        if ip_address in self.device_ip_mapping:
            return self.device_ip_mapping[ip_address]
        
        # For AR glasses, always assign 'glasses' if available
        if preferred_type == 'glasses' and 'glasses' not in self.device_ip_mapping.values():
            self.device_ip_mapping[ip_address] = 'glasses'
            logger.info(f"Assigned AR Glasses to IP {ip_address}")
            return 'glasses'
        
        # Find next available device type
        for device_type in self.next_device_assignment:
            if device_type not in self.device_ip_mapping.values():
                self.device_ip_mapping[ip_address] = device_type
                logger.info(f"Assigned {device_type} to IP {ip_address}")
                return device_type
        
        # Fallback if all devices assigned
        fallback = f"device_{len(self.device_ip_mapping)}"
        self.device_ip_mapping[ip_address] = fallback
        logger.warning(f"All standard device types assigned, using {fallback} for IP {ip_address}")
        return fallback
    
    def _parse_phone_data(self, data):
        """Parse phone data: timestamp timestamp userAccel.x y z quat.x y z w roll pitch yaw"""
        try:
            parts = data.split()
            if len(parts) >= 11:
                timestamp = float(parts[0])
                
                # User acceleration (m/s²) - RAW, no conversion
                accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                
                # Quaternion from iOS (x, y, z, w format) - RAW, no conversion
                quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                
                # Euler angles if available
                euler = None
                if len(parts) >= 12:
                    euler = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
                
                # Phone doesn't send gyroscope data separately - set to zero
                gyro = np.array([0.0, 0.0, 0.0])
                
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='phone',
                    accelerometer=accel,  # Raw data
                    gyroscope=gyro,
                    quaternion=quat,      # Raw data
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
                accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])  # Raw data
                quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])  # Raw data
                
                # AirPods don't typically send gyroscope data
                gyro = np.array([0.0, 0.0, 0.0])
                
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='headphone',
                    accelerometer=accel,  # Raw data
                    gyroscope=gyro,
                    quaternion=quat       # Raw data
                )
                
                self.data_queue.put(imu_data)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Headphone data parse error: {e}")
    
    def _parse_watch_data(self, data):
        """Parse Apple Watch data: timestamp deviceTimestamp accX accY accZ quatX quatY quatZ quatW gyroX gyroY gyroZ"""
        try:
            parts = data.split()
            
            # Apple Watch format: timestamp deviceTimestamp accX accY accZ quatX quatY quatZ quatW gyroX gyroY gyroZ
            if len(parts) >= 12:
                # Parse timestamps
                timestamp = float(parts[0])
                device_timestamp = float(parts[1])
                
                # Parse accelerometer data (m/s²) - RAW, no conversion
                accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                
                # Parse quaternion (x, y, z, w format) - RAW, no conversion
                quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                
                # Parse gyroscope data (rad/s) - RAW, no conversion
                gyro = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
                
                # Log successful Apple Watch data reception
                logger.debug(f"Apple Watch RAW data - Accel: [{accel[0]:.3f}, {accel[1]:.3f}, {accel[2]:.3f}], "
                           f"Gyro: [{gyro[0]:.3f}, {gyro[1]:.3f}, {gyro[2]:.3f}]")
                
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='watch',
                    accelerometer=accel,  # Raw data
                    gyroscope=gyro,       # Raw data
                    quaternion=quat       # Raw data
                )
                
                self.data_queue.put(imu_data)
                
            else:
                logger.warning(f"Apple Watch data incomplete: expected 12 parts, got {len(parts)}")
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Watch data parse error: {e} - Data: {data}")
    
    def _convert_ios_quaternion(self, ios_quat: np.ndarray) -> np.ndarray:
        """Convert iOS quaternion - DISABLED for now, return raw data"""
        # Return raw data for debugging
        return ios_quat
    
    def _convert_ar_glasses_quaternion(self, ar_quat: np.ndarray) -> np.ndarray:
        """Convert AR Glasses quaternion - DISABLED for now, return raw data"""
        # Return raw data for debugging
        return ar_quat
    
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
                gyroscope=imu_data.gyroscope,  # Include gyroscope data (Apple Watch + AR Glasses)
                quaternion=relative_quat,
                euler=imu_data.euler
            )
            
            # Check if device is calibrated
            is_calibrated = imu_data.device_id in self.calibrator.reference_quaternions
            
            # Update visualization
            self.visualizer.update_device_data(processed_data, is_calibrated)
            
            # Log gyroscope data for Apple Watch and AR Glasses
            if imu_data.device_id in ['watch', 'glasses'] and np.linalg.norm(imu_data.gyroscope) > 0.001:
                logger.debug(f"{imu_data.device_id} active - Gyro magnitude: {np.linalg.norm(imu_data.gyroscope):.3f}, "
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