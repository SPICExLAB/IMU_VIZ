#!/usr/bin/env python3
"""
Fixed IMU_receiver.py - Enhanced for Rokid AR Glasses

Key fixes:
- Proper coordinate system handling for Rokid vs Apple devices
- Fixed quaternion calibration logic
- Updated data parsing for Unity's new 11-value format
- Corrected 3D visualization for glasses orientation
"""

import socket
import numpy as np
import threading
import time
import queue
from collections import deque
from dataclasses import dataclass
import logging
from scipy.spatial.transform import Rotation as R

# Import our refactored visualization module
from UI.main_visualizer import IMUVisualizer
from imu_data_api import IMUDataAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IMUData:
    """IMU data structure for iOS devices and AR glasses"""
    timestamp: float
    device_id: str
    accelerometer: np.ndarray  # [ax, ay, az] in m/s²
    gyroscope: np.ndarray      # [gx, gy, gz] in rad/s
    quaternion: np.ndarray     # [x, y, z, w] orientation
    euler: np.ndarray = None   # [nod, tilt, turn] for Rokid glasses

class MobilePoseCalibrator:
    
    def __init__(self):
        # Store reference quaternions for each device (the "zero" position)
        self.reference_quaternions = {}
        
    def set_reference_orientation(self, device_id: str, current_quaternion: np.ndarray):
        """Set current orientation as the reference/zero position with device-specific handling"""
        
        if device_id == 'glasses':
            # For Rokid glasses, we need to handle their Z-backward coordinate system
            # Apply a coordinate system transform before storing reference
            try:
                # Create rotation that flips Z axis for glasses (Z backward -> Z forward)
                # This is a 180-degree rotation around Y axis
                z_flip_rotation = R.from_euler('y', 180, degrees=True)
                
                # Apply the flip to the current quaternion
                current_rotation = R.from_quat(current_quaternion)
                flipped_rotation = z_flip_rotation * current_rotation
                
                # Store the flipped quaternion as reference
                self.reference_quaternions[device_id] = flipped_rotation.as_quat()
                
                logger.info(f"Set reference orientation for {device_id} (with Z-flip)")
                logger.info(f"   Original quat: [{current_quaternion[0]:.3f}, {current_quaternion[1]:.3f}, {current_quaternion[2]:.3f}, {current_quaternion[3]:.3f}]")
                logger.info(f"   Reference quat: [{flipped_rotation.as_quat()[0]:.3f}, {flipped_rotation.as_quat()[1]:.3f}, {flipped_rotation.as_quat()[2]:.3f}, {flipped_rotation.as_quat()[3]:.3f}]")
            
            except Exception as e:
                logger.warning(f"Failed to apply coordinate transform for glasses: {e}")
                # Fallback to standard behavior
                self.reference_quaternions[device_id] = current_quaternion.copy()
        else:
            # Standard behavior for Apple devices
            self.reference_quaternions[device_id] = current_quaternion.copy()
            logger.info(f"Set reference orientation for {device_id}")
            logger.info(f"   Reference quat: [{current_quaternion[0]:.3f}, {current_quaternion[1]:.3f}, {current_quaternion[2]:.3f}, {current_quaternion[3]:.3f}]")
        
        # For all devices, log the euler angles at calibration
        try:
            if device_id == 'glasses':
                # Use the flipped quaternion for Euler calculation
                ref_quat = self.reference_quaternions[device_id]
            else:
                ref_quat = current_quaternion
                
            r = R.from_quat(ref_quat)
            euler = r.as_euler('xyz', degrees=True)
            logger.info(f"   Reference euler: NOD={euler[0]:.1f}° TURN={euler[1]:.1f}° TILT={euler[2]:.1f}°")
        except:
            pass
    
    def get_relative_orientation(self, device_id: str, current_quaternion: np.ndarray) -> np.ndarray:
        """Get orientation relative to the reference position with device-specific handling"""
        if device_id not in self.reference_quaternions:
            # No reference set, return current orientation
            return current_quaternion
        
        # Calculate relative orientation
        ref_quat = self.reference_quaternions[device_id]
        
        # Use scipy for proper quaternion operations
        try:
            ref_rotation = R.from_quat(ref_quat)
            
            if device_id == 'glasses':
                # For glasses, apply the same Z-flip to current quaternion before comparison
                z_flip_rotation = R.from_euler('y', 180, degrees=True)
                current_rotation = R.from_quat(current_quaternion)
                flipped_current = z_flip_rotation * current_rotation
                
                # Get relative rotation: ref_inv * flipped_current
                relative_rotation = ref_rotation.inv() * flipped_current
            else:
                # Standard behavior for Apple devices
                current_rotation = R.from_quat(current_quaternion)
                relative_rotation = ref_rotation.inv() * current_rotation
            
            relative_quat = relative_rotation.as_quat()
            return relative_quat
            
        except Exception as e:
            logger.warning(f"Quaternion calculation error for {device_id}: {e}")
            return current_quaternion
    
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

class IMUReceiver:
    """IMU receiver with fixed Rokid glasses support"""
    
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
        
        logger.info(f"Enhanced IMU Receiver initialized on port {port}")
        self.api = IMUDataAPI(self)
        logger.info("API available via receiver.api")

    def get_api(self) -> IMUDataAPI:
        """
        Get the IMU Data API instance
        
        Returns:
            IMUDataAPI instance for external access
        """
        return self.api
    
    def start_server(self):
        """Start UDP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.settimeout(0.1)
            
            logger.info(f"UDP server started on port {self.port}")
            logger.info("Waiting for data from:")
            logger.info("  - iOS devices (phone/watch)")
            logger.info("  - Rokid AR Glasses (Unity app)")
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
        """Parse data from different sources (iOS or Rokid Glasses)"""
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
                # Assume it's Rokid Glasses Unity format
                self._parse_rokid_glasses_data(message, addr)
                    
        except Exception as e:
            logger.warning(f"Parse error: {e}")

    
    def _parse_rokid_glasses_data(self, message, addr):
        """Parse Rokid Glasses Unity data format with dynamic gravity removal"""
        try:
            parts = message.split()
            if len(parts) != 12:
                logger.warning(f"Rokid Glasses data format error: expected 12 values, got {len(parts)}")
                return
                
            # Parse Unity's format
            timestamp = float(parts[0])
            device_timestamp = float(parts[1])
            
            # Parse gameRotation quaternion from Unity (x, y, z, w format)
            quat = np.array([float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])])
            
            # Parse sensor data
            raw_accel = np.array([float(parts[6]), float(parts[7]), float(parts[8])])
            gyro = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
            
            # CONDITIONAL GRAVITY REMOVAL based on visualizer toggle
            if self.visualizer.get_gravity_enabled():
                try:
                    # Convert left-handed Unity quaternion to right-handed for gravity calculation only
                    quat_right_handed = np.array([-quat[0], quat[1], quat[2], -quat[3]])
                    rotation = R.from_quat(quat_right_handed)
                    
                    # Define gravity vector in world frame and transform to device frame
                    gravity_magnitude = np.linalg.norm(raw_accel)
                    gravity_world = np.array([0, 0, gravity_magnitude])
                    gravity_device_frame = rotation.inv().apply(gravity_world)
                    
                    # Remove gravity from raw acceleration
                    linear_accel = raw_accel - gravity_device_frame
                    
                except Exception as e:
                    logger.warning(f"Gravity removal failed: {e}, using raw acceleration")
                    linear_accel = raw_accel
            else:
                # Use raw acceleration when gravity removal is disabled
                linear_accel = raw_accel
            
            # Convert quaternion to Euler angles for display
            euler_deg = None
            try:
                # Use right-handed quaternion for Euler conversion
                quat_right_handed = np.array([-quat[0], quat[1], quat[2], -quat[3]])
                rotation = R.from_quat(quat_right_handed)
                euler_rad = rotation.as_euler('xyz', degrees=False)
                euler_deg = euler_rad * 180.0 / np.pi
                
                # Map to head movements: nod, turn, tilt
                nod = euler_deg[0]    # X rotation = NOD (up/down)
                turn = euler_deg[2]   # Y rotation = TURN (left/right)  
                tilt = euler_deg[1]   # Z rotation = TILT (left/right tilt)
                
                euler_deg = np.array([nod, tilt, turn])  # Store as [nod, tilt, turn]
                
            except:
                euler_deg = np.array([0, 0, 0])
            
            # Assign device ID
            device_id = self._get_device_id_for_ip(addr[0], 'glasses')
            
            # Create IMU data
            imu_data = IMUData(
                timestamp=timestamp,
                device_id=device_id,
                accelerometer=linear_accel,  # Conditionally gravity-removed acceleration
                gyroscope=gyro,
                quaternion=quat,  # Use ORIGINAL quaternion for correct visualization
                euler=euler_deg  # NOD, TILT, TURN in degrees
            )
            
            self.data_queue.put(imu_data)
            
            # Optional: Log gravity removal info periodically
            if hasattr(self, '_gravity_log_counter'):
                self._gravity_log_counter += 1
            else:
                self._gravity_log_counter = 0
                
            if self._gravity_log_counter % 300 == 0:  # Every ~5 seconds at 60Hz
                gravity_enabled = self.visualizer.get_gravity_enabled()
                if gravity_enabled:
                    gravity_magnitude = np.linalg.norm(gravity_device_frame)
                    linear_magnitude = np.linalg.norm(linear_accel)
                    # logger.info(f"Glasses gravity removal - Gravity mag: {gravity_magnitude:.2f}, Linear acc mag: {linear_magnitude:.2f}")
                else:
                    raw_magnitude = np.linalg.norm(raw_accel)
                    # logger.info(f"Glasses raw acceleration - Magnitude: {raw_magnitude:.2f}")
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Rokid Glasses data parse error: {e} - Data: {message}")
    
    def _get_device_id_for_ip(self, ip_address, preferred_type='glasses'):
        """Get device ID for an IP address, assigning new ones as needed"""
        if ip_address in self.device_ip_mapping:
            return self.device_ip_mapping[ip_address]
        
        # For Rokid glasses, always assign 'glasses' if available
        if preferred_type == 'glasses' and 'glasses' not in self.device_ip_mapping.values():
            self.device_ip_mapping[ip_address] = 'glasses'
            logger.info(f"Assigned Rokid AR Glasses to IP {ip_address}")
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
                
                # User acceleration (m/s²)
                accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                
                # Quaternion from iOS (x, y, z, w format)
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
                    accelerometer=accel,
                    gyroscope=gyro,
                    quaternion=quat,
                    euler=euler
                )
                
                self.data_queue.put(imu_data)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Phone data parse error: {e}")
    
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
    
    def _parse_headphone_data(self, data):
        """Parse headphone data (AirPods)"""
        try:
            parts = data.split()
            if len(parts) >= 9:
                timestamp = float(parts[0])
                accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                
                # AirPods don't typically send gyroscope data
                gyro = np.array([0.0, 0.0, 0.0])
                
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='headphone',
                    accelerometer=accel,
                    gyroscope=gyro,
                    quaternion=quat
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
                timestamp = float(parts[0])
                device_timestamp = float(parts[1])
                
                # Parse accelerometer data (m/s²)
                accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                
                # Parse quaternion (x, y, z, w format)
                quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                
                # Parse gyroscope data (rad/s)
                gyro = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
                
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='watch',
                    accelerometer=accel,
                    gyroscope=gyro,
                    quaternion=quat
                )
                
                self.data_queue.put(imu_data)
                
            else:
                logger.warning(f"Apple Watch data incomplete: expected 12 parts, got {len(parts)}")
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Watch data parse error: {e} - Data: {data}")
    
    def calibrate_all_devices(self):
        """Calibrate all active devices (set current pose as T-pose/neutral)"""
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
                gyroscope=imu_data.gyroscope,
                quaternion=relative_quat,
                euler=imu_data.euler
            )
            
            # Check if device is calibrated
            is_calibrated = imu_data.device_id in self.calibrator.reference_quaternions
            
            # Update visualization
            self.visualizer.update_device_data(processed_data, is_calibrated)
            
            # Log interesting data for debugging (optional)
            if imu_data.device_id == 'glasses' and imu_data.euler is not None:
                nod, tilt, turn = imu_data.euler
                # Only log if significant movement (optional - can be removed)
                if abs(nod) > 15 or abs(tilt) > 15 or abs(turn) > 30:
                    logger.debug(f"Glasses large movement - NOD:{nod:.1f}° TILT:{tilt:.1f}° TURN:{turn:.1f}°")
    
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
    print("=============================")
    print("Coordinate Systems:")
    print("  Apple devices: Z toward user (standard)")
    print("  Rokid glasses: Z away from user (mirrored)")
    
    receiver = IMUReceiver(port=8001)
    receiver.run()

if __name__ == "__main__":
    main()