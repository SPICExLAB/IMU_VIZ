#!/usr/bin/env python3
"""
IMU_receiver.py - Refactored with modular structure

Key improvements:
- Modular design with separate modules for different functionality
- Socket handling and sensor transformations moved to Input_Utils
- Cleaner main class focusing on coordination
"""

import numpy as np
import time
from collections import deque
from dataclasses import dataclass
import logging
from scipy.spatial.transform import Rotation as R

# Import our visualization module
from UI.main_visualizer import IMUVisualizer

# Import our input utilities
from Input_Utils import (
    # Socket utilities
    SocketReceiver, 
    ApiServer,
    
    # Sensor utilities
    sensor2global,
    preprocess_headphone_data,
    preprocess_rokid_data,
    apply_gravity_compensation
)

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

class IMUCalibrator:
    """
    Handles calibration of IMU devices using MobilePoseR's approach.
    """
    
    def __init__(self):
        # Store reference quaternions for each device (the "zero" position)
        self.reference_quaternions = {}
    
    def set_reference_orientation(self, device_id: str, current_quaternion: np.ndarray):
        """Set current orientation as the reference/zero position"""
        self.reference_quaternions[device_id] = current_quaternion.copy()
        
        logger.info(f"Set reference orientation for {device_id}")
        logger.info(f"   Reference quat: [{current_quaternion[0]:.3f}, {current_quaternion[1]:.3f}, "
                   f"{current_quaternion[2]:.3f}, {current_quaternion[3]:.3f}]")
        
        # Log the euler angles at calibration for convenience
        try:
            r = R.from_quat(current_quaternion)
            euler = r.as_euler('xyz', degrees=True)
            logger.info(f"   Reference euler: NOD={euler[0]:.1f}° TURN={euler[1]:.1f}° TILT={euler[2]:.1f}°")
        except Exception as e:
            logger.warning(f"Could not calculate Euler angles: {e}")
    
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
    """Core IMU receiver using modular components"""
    
    # Class variable to store the instance for external access
    _instance = None
    
    def __init__(self, data_port=8001, api_port=9001):
        # Current device orientations and raw data
        self.current_orientations = {}
        self.raw_device_data = {}
        
        # Public calibration flag - can be set by external applications
        self.calibration_requested = False
        
        # Core components
        self.calibrator = IMUCalibrator()
        self.visualizer = IMUVisualizer()
        self.running = False
        
        # Initialize socket receivers
        self.socket_receiver = SocketReceiver(port=data_port)
        
        # Initialize API server with callbacks
        self.api_server = ApiServer(
            port=api_port,
            callbacks={
                'get_device_data': self._get_device_data,
                'get_active_devices': self._get_active_devices,
                'calibrate': self.request_calibration
            }
        )
        
        # Store instance for external access
        IMUReceiver._instance = self
        
        logger.info(f"Enhanced IMU Receiver initialized")
        logger.info(f"Data port: {data_port}, API port: {api_port}")
        logger.info("Using MobilePoseR-style coordinate transformations")
    
    @classmethod
    def get_instance(cls):
        """Get the current IMUReceiver instance for external access"""
        return cls._instance
    
    def request_calibration(self):
        """Request calibration (can be called internally or externally)"""
        self.calibration_requested = True
        logger.info("Calibration requested")
        return True
    
    def _get_active_devices(self):
        """Get list of active devices - used by API server"""
        active = []
        current_time = time.time()
        for device_id, device_data in self.visualizer.device_data.items():
            if current_time - device_data['last_update'] < 2.0:
                active.append(device_id)
        return active
    
    def _get_device_data(self, device_id):
        """Get data for a specific device - used by API server"""
        if device_id not in self.current_orientations:
            return None
            
        device_data = self.visualizer.device_data.get(device_id)
        if not device_data:
            return None
            
        current_time = time.time()
        if current_time - device_data['last_update'] > 2.0:
            return None
            
        # Get device data
        quaternion = device_data.get('quaternion', np.array([0, 0, 0, 1]))
        
        try:
            rotation_matrix = R.from_quat(quaternion).as_matrix()
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
    
    def _parse_data(self, message, addr):
        """Parse incoming data from socket"""
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
        """Parse Rokid Glasses Unity data"""
        try:
            parts = message.split()
            if len(parts) != 12:
                logger.warning(f"Rokid Glasses data format error: expected 12 values, got {len(parts)}")
                return
                
            # Parse Unity's format
            timestamp = float(parts[0])
            device_timestamp = float(parts[1])
            
            # Parse quaternion from Unity (x, y, z, w format)
            device_quat = np.array([float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])])
            
            # Parse sensor data
            raw_accel = np.array([float(parts[6]), float(parts[7]), float(parts[8])])
            gyro = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
            
            # Assign device ID
            device_id = self.socket_receiver.get_device_id_for_ip(addr[0], 'glasses')
            
            # Preprocess Rokid data to match expected format for sensor2global
            aligned_quat, aligned_accel = preprocess_rokid_data(device_quat, raw_accel)
            
            # Store raw data for future reference
            self.raw_device_data[device_id] = {
                'quaternion': aligned_quat,
                'acceleration': aligned_accel,
                'gyroscope': gyro
            }
            
            # Apply sensor2global transformation
            global_quat, global_accel = sensor2global(
                aligned_quat, 
                aligned_accel, 
                self.calibrator.reference_quaternions, 
                device_id
            )
            
            # Apply gravity compensation if enabled
            if self.visualizer.get_gravity_enabled():
                linear_accel = apply_gravity_compensation(global_quat, global_accel)
            else:
                # Use acceleration without gravity compensation
                linear_accel = global_accel
            
            # Store the quaternion for calibration reference
            self.current_orientations[device_id] = global_quat
            
            # Convert quaternion to Euler angles for display
            euler_deg = None
            try:
                rotation = R.from_quat(global_quat)
                euler_rad = rotation.as_euler('xyz', degrees=False)
                euler_deg = euler_rad * 180.0 / np.pi
                
                # Map to head movements: nod, turn, tilt
                nod = euler_deg[0]    # X rotation = NOD (up/down)
                turn = euler_deg[1]   # Y rotation = TURN (left/right)  
                tilt = euler_deg[2]   # Z rotation = TILT (left/right tilt)
                
                euler_deg = np.array([nod, turn, tilt])  # Store as [nod, turn, tilt]
                
            except:
                euler_deg = np.array([0, 0, 0])
            
            # Create IMU data with the transformed values
            imu_data = IMUData(
                timestamp=timestamp,
                device_id=device_id,
                accelerometer=linear_accel,
                gyroscope=gyro,
                quaternion=global_quat,
                euler=euler_deg
            )
            
            # Update visualization
            is_calibrated = device_id in self.calibrator.reference_quaternions
            self.visualizer.update_device_data(imu_data, is_calibrated)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Rokid Glasses data parse error: {e} - Data: {message}")
    
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
    
    def _parse_phone_data(self, data):
        """Parse phone data with MobilePoseR-style transformations"""
        try:
            parts = data.split()
            if len(parts) >= 11:
                timestamp = float(parts[0])
                
                # User acceleration (m/s²)
                device_accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                
                # Quaternion from iOS (x, y, z, w format)
                device_quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                
                # Euler angles if available
                euler = None
                if len(parts) >= 12:
                    euler = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
                
                # Phone doesn't send gyroscope data separately - set to zero
                gyro = np.array([0.0, 0.0, 0.0])
                
                # Store raw data for future reference
                self.raw_device_data['phone'] = {
                    'quaternion': device_quat,
                    'acceleration': device_accel,
                    'gyroscope': gyro
                }
                
                # Apply sensor2global transformation
                global_quat, global_accel = sensor2global(
                    device_quat, 
                    device_accel, 
                    self.calibrator.reference_quaternions, 
                    'phone'
                )
                
                # Store the quaternion for calibration reference
                self.current_orientations['phone'] = global_quat
                
                # Create IMU data with the transformed values
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='phone',
                    accelerometer=global_accel,
                    gyroscope=gyro,
                    quaternion=global_quat,
                    euler=euler
                )
                
                # Update visualization
                is_calibrated = 'phone' in self.calibrator.reference_quaternions
                self.visualizer.update_device_data(imu_data, is_calibrated)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Phone data parse error: {e}")
    
    def _parse_headphone_data(self, data):
        """Parse headphone data with MobilePoseR-style transformations"""
        try:
            parts = data.split()
            if len(parts) >= 9:
                timestamp = float(parts[0])
                
                # Get device-frame data
                device_accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                device_quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                
                # AirPods don't typically send gyroscope data
                gyro = np.array([0.0, 0.0, 0.0])
                
                # Preprocess headphone data to match expected format
                aligned_quat, aligned_accel = preprocess_headphone_data(device_quat, device_accel)
                
                # Store raw data for future reference
                self.raw_device_data['headphone'] = {
                    'quaternion': aligned_quat,
                    'acceleration': aligned_accel,
                    'gyroscope': gyro
                }
                
                # Apply sensor2global transformation
                global_quat, global_accel = sensor2global(
                    aligned_quat, 
                    aligned_accel, 
                    self.calibrator.reference_quaternions, 
                    'headphone'
                )
                
                # Store the quaternion for calibration reference
                self.current_orientations['headphone'] = global_quat
                
                # Create IMU data with the transformed values
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='headphone',
                    accelerometer=global_accel,
                    gyroscope=gyro,
                    quaternion=global_quat
                )
                
                # Update visualization
                is_calibrated = 'headphone' in self.calibrator.reference_quaternions
                self.visualizer.update_device_data(imu_data, is_calibrated)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Headphone data parse error: {e}")
    
    def _parse_watch_data(self, data):
        """Parse Apple Watch data with MobilePoseR-style transformations"""
        try:
            parts = data.split()
            
            # Apple Watch format: timestamp deviceTimestamp accX accY accZ quatX quatY quatZ quatW gyroX gyroY gyroZ
            if len(parts) >= 12:
                timestamp = float(parts[0])
                device_timestamp = float(parts[1])
                
                # Parse device-frame data
                device_accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
                device_quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
                gyro = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
                
                # Store raw data for future reference
                self.raw_device_data['watch'] = {
                    'quaternion': device_quat,
                    'acceleration': device_accel,
                    'gyroscope': gyro
                }
                
                # Apply sensor2global transformation
                global_quat, global_accel = sensor2global(
                    device_quat, 
                    device_accel, 
                    self.calibrator.reference_quaternions, 
                    'watch'
                )
                
                # Store the quaternion for calibration reference
                self.current_orientations['watch'] = global_quat
                
                # Create IMU data with the transformed values
                imu_data = IMUData(
                    timestamp=timestamp,
                    device_id='watch',
                    accelerometer=global_accel,
                    gyroscope=gyro,
                    quaternion=global_quat
                )
                
                # Update visualization
                is_calibrated = 'watch' in self.calibrator.reference_quaternions
                self.visualizer.update_device_data(imu_data, is_calibrated)
                
            else:
                logger.warning(f"Apple Watch data incomplete: expected 12 parts, got {len(parts)}")
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Watch data parse error: {e} - Data: {data}")
    
    def calibrate_all_devices(self):
        """Calibrate all active devices (set current pose as reference)"""
        self.calibrator.calibrate_all_devices(self.current_orientations)
    
    def process_data(self):
        """Process any pending data from the socket receiver"""
        # Get next data packet
        data_packet = self.socket_receiver.get_data()
        
        # Process if we have data
        if data_packet:
            message, addr = data_packet
            self._parse_data(message, addr)
    
    def run(self):
        """Main application loop"""
        # Start the socket receiver and API server
        self.socket_receiver.start()
        self.api_server.start()
        
        self.running = True
        
        try:
            while self.running:
                # Handle visualization events
                event = self.visualizer.handle_events()
                
                if event == "quit":
                    self.running = False
                elif event == "calibrate":
                    self.calibrate_all_devices()
                
                # Check for external calibration request
                if self.calibration_requested:
                    self.calibrate_all_devices()
                    self.calibration_requested = False
                
                # Process incoming data
                self.process_data()
                
                # Render visualization
                self.visualizer.render()
        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        
        finally:
            self.running = False
            self.socket_receiver.stop()
            self.api_server.stop()
            self.visualizer.cleanup()

def main():
    print("=============================")
    print("IMU Receiver with MobilePoseR-style Transformations")
    print("=============================")
    print("Device Coordinate Systems:")
    print("  Phone/Watch:   X:right, Y:up, Z:backward")
    print("  Headphone:     X:right, Z:up, Y:forward")
    print("  Rokid Glasses: X:right, Y:up, Z:forward")
    print()
    print("Calibration maps device coordinates to aligned frame")
    print("External API: Available on port 9001")
    
    receiver = IMUReceiver(data_port=8001, api_port=9001)
    receiver.run()

if __name__ == "__main__":
    main()