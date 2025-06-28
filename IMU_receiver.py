#!/usr/bin/env python3
"""
IMU_receiver.py 

Key features:
- Proper coordinate system handling for Rokid vs Apple devices
- Fixed quaternion calibration logic
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
    """Core IMU receiver with clean separation of concerns"""
    
    # Class variable to store the instance for external access
    _instance = None
    
    def __init__(self, port=8001, api_port=9001):
        self.port = port
        self.api_port = api_port
        self.socket = None
        self.api_socket = None
        self.running = False
        self.api_running = False
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
        
        # Store instance for external access
        IMUReceiver._instance = self
        
        logger.info(f"Enhanced IMU Receiver initialized on port {port}")
        logger.info(f"API server will start on port {api_port}")
        logger.info("External API available via imu_data_api.py")

    @classmethod
    def get_instance(cls):
        """Get the current IMUReceiver instance for external access"""
        return cls._instance
    
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
            
            # Start API server thread
            api_thread = threading.Thread(target=self._start_api_server)
            api_thread.daemon = True
            api_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
    
    def _start_api_server(self):
        """Start API server for external demo access"""
        try:
            self.api_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.api_socket.bind(('127.0.0.1', self.api_port))
            self.api_socket.settimeout(0.1)
            self.api_running = True
            
            logger.info(f"API server started on port {self.api_port}")
            
            while self.api_running:
                try:
                    data, addr = self.api_socket.recvfrom(1024)
                    request = data.decode('utf-8')
                    response = self._handle_api_request(request)
                    self.api_socket.sendto(response.encode('utf-8'), addr)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.api_running:
                        logger.error(f"API server error: {e}")
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
    
    def _handle_api_request(self, request):
        """Handle API requests and return JSON responses"""
        import json
        
        try:
            if request == "get_all_devices":
                devices = {}
                for device_id in ['phone', 'watch', 'headphone', 'glasses']:
                    device_data = self._get_device_data_internal(device_id)
                    if device_data:
                        devices[device_id] = device_data
                return json.dumps(devices)
                
            elif request.startswith("get_device:"):
                device_id = request.split(":", 1)[1]
                device_data = self._get_device_data_internal(device_id)
                return json.dumps(device_data) if device_data else json.dumps(None)
                
            elif request == "get_active_devices":
                active = []
                current_time = time.time()
                for device_id, device_data in self.visualizer.device_data.items():
                    if current_time - device_data['last_update'] < 2.0:
                        active.append(device_id)
                return json.dumps(active)
                
            elif request == "ping":
                return json.dumps({"status": "ok", "timestamp": time.time()})
                
        except Exception as e:
            return json.dumps({"error": str(e)})
        
        return json.dumps({"error": "Unknown request"})
    
    def _get_device_data_internal(self, device_id):
        """Internal method to get device data for API"""
        if device_id not in self.current_orientations:
            return None
            
        device_data = self.visualizer.device_data.get(device_id)
        if not device_data:
            return None
            
        current_time = time.time()
        if current_time - device_data['last_update'] > 2.0:
            return None
            
        # Get calibrated data
        raw_quaternion = self.current_orientations[device_id]
        calibrated_quat = self.calibrator.get_relative_orientation(device_id, raw_quaternion)
        
        try:
            rotation_matrix = R.from_quat(calibrated_quat).as_matrix()
        except:
            rotation_matrix = np.eye(3)
            
        acceleration_history = device_data.get('accel_history', [])
        if len(acceleration_history) == 0:
            return None
            
        latest_acceleration = list(acceleration_history[-1])
        
        # Get gyroscope if available
        gyroscope = None
        gyro_history = device_data.get('gyro_history', [])
        if len(gyro_history) > 0:
            latest_gyro = list(gyro_history[-1])
            if sum(abs(x) for x in latest_gyro) > 0.001:
                gyroscope = latest_gyro
        
        return {
            'timestamp': device_data['last_update'],
            'device_name': device_id,
            'frequency': device_data.get('frequency', 0.0),
            'acceleration': latest_acceleration,
            'rotation_matrix': rotation_matrix.tolist(),
            'gyroscope': gyroscope,
            'is_calibrated': device_id in self.calibrator.reference_quaternions
        }
    
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
                    # gravity_magnitude = np.linalg.norm(raw_accel)
                    gravity_world = np.array([0, 0, 9,81])
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
            self.api_running = False
            if self.socket:
                self.socket.close()
            if self.api_socket:
                self.api_socket.close()
            self.visualizer.cleanup()

def main():
    print("=============================")
    print("Coordinate Systems:")
    print("  Apple devices: Z toward user (standard)")
    print("  Rokid glasses: Z away from user (mirrored)")
    print()
    print("External API: Use imu_data_api.py for accessing data")
    
    receiver = IMUReceiver(port=8001)
    receiver.run()

if __name__ == "__main__":
    main()