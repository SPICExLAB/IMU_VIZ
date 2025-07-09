"""
Input_utils/sensor_utils.py - Refactored sensor data parsing and processing
Clean separation of parsing methods for different device types
"""

import numpy as np
import time
import logging
from scipy.spatial.transform import Rotation as R
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class SensorDataProcessor:
    """Processes sensor data from different device types (iOS and AR glasses)"""
    
    def __init__(self, use_ar_as_headphone: bool = True):
        self.use_ar_as_headphone = use_ar_as_headphone
        
        # Device type mapping to indices for live_demo compatibility
        self.device_indices = {
            'phone': 0,
            'watch': 1, 
            'headphone': 2,  # AirPods
            'glasses': 2     # AR Glasses (when use_ar_as_headphone=True)
        }
        
        logger.info(f"SensorDataProcessor initialized with use_ar_as_headphone={use_ar_as_headphone}")
    
    def process_device_data(self, device_type: str, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process raw device data and return standardized format
        
        Args:
            device_type: 'ios' or 'ar_glasses'
            raw_data: Raw data dictionary from socket receiver
            
        Returns:
            Standardized sensor data dictionary or None if processing fails
        """
        try:
            if device_type == 'ios':
                return self._process_ios_data(raw_data)
            elif device_type == 'ar_glasses':
                return self._process_ar_glasses_data(raw_data)
            else:
                logger.warning(f"Unknown device type: {device_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing {device_type} data: {e}")
            return None
    
    def _process_ios_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process iOS device data (iPhone, Apple Watch, AirPods)"""
        try:
            # Extract basic info
            device_name = raw_data['device_name'].lower()
            timestamps = raw_data['timestamps']
            accelerometer = np.array(raw_data['accelerometer'])
            quaternion = np.array(raw_data['quaternion'])
            gyroscope = raw_data.get('gyroscope', np.zeros(3))
            
            # Validate data
            if len(accelerometer) != 3 or len(quaternion) != 4:
                logger.warning(f"Invalid data dimensions for {device_name}")
                return None
            
            # Get device index
            device_id = self._get_device_index(device_name)
            if device_id is None:
                logger.warning(f"Unknown iOS device: {device_name}")
                return None
            
            # Apply device-specific transformations
            processed_acc, processed_quat = self._apply_ios_transformations(
                device_name, accelerometer, quaternion
            )
            
            # Calculate Euler angles
            euler_angles = self._quaternion_to_euler(processed_quat)
            
            return {
                'device_id': device_id,
                'device_name': device_name,
                'device_type': 'ios',
                'timestamp': timestamps[0] if isinstance(timestamps, list) else timestamps,
                'accelerometer': processed_acc,
                'gyroscope': np.array(gyroscope),
                'quaternion': processed_quat,
                'raw_quaternion': quaternion,
                'euler': euler_angles
            }
            
        except Exception as e:
            logger.error(f"Error processing iOS data: {e}")
            return None
    
    def _process_ar_glasses_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process AR glasses data from Unity app"""
        try:
            # Extract data
            timestamps = raw_data.get('timestamps', [time.time(), time.time()])
            accelerometer = np.array(raw_data['accelerometer'])
            quaternion = np.array(raw_data['quaternion'])
            gyroscope = raw_data.get('gyroscope', np.zeros(3))
            
            # Validate data
            if len(accelerometer) != 3 or len(quaternion) != 4:
                logger.warning("Invalid AR glasses data dimensions")
                return None
            
            # Determine device index based on use_ar_as_headphone flag
            if self.use_ar_as_headphone:
                device_id = self.device_indices['glasses']  # Index 2 (same as headphone)
                device_name = 'headphone'  # Map to headphone for live_demo compatibility
            else:
                device_id = 4  # Separate index for AR glasses
                device_name = 'glasses'
            
            # Apply AR glasses transformations 
            processed_acc, processed_quat = self._apply_ar_glasses_transformations(
                accelerometer, quaternion, remove_gravity=True
            )
            
            # Calculate Euler angles
            euler_angles = self._quaternion_to_euler(processed_quat)
            
            return {
                'device_id': device_id,
                'device_name': device_name,
                'device_type': 'ar_glasses',
                'timestamp': timestamps[0] if isinstance(timestamps, list) else timestamps,
                'accelerometer': processed_acc,
                'gyroscope': np.array(gyroscope),
                'quaternion': processed_quat,
                'raw_quaternion': quaternion,
                'euler': euler_angles
            }
            
        except Exception as e:
            logger.error(f"Error processing AR glasses data: {e}")
            return None
    
    def _get_device_index(self, device_name: str) -> Optional[int]:
        """Get device index for live_demo compatibility"""
        # Map device names to standard names
        name_mapping = {
            'phone': 'phone',
            'iphone': 'phone',
            'watch': 'watch',
            'applewatch': 'watch',
            'headphone': 'headphone',
            'airpods': 'headphone',
            'glasses': 'glasses',
            'arglasses': 'glasses'
        }
        
        normalized_name = name_mapping.get(device_name.lower())
        if normalized_name:
            return self.device_indices.get(normalized_name)
        
        return None
    
    def _apply_ios_transformations(self, device_name: str, accelerometer: np.ndarray, 
                                 quaternion: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Apply device-specific coordinate transformations for iOS devices"""
        
        # Copy arrays to avoid modifying originals
        acc = accelerometer.copy()
        quat = quaternion.copy()
        
        # Apply device-specific transformations
        if device_name == 'headphone':
            # AirPods coordinate frame adjustments
            # Note: Removed the Unity bug fix comment as requested
            euler = R.from_quat(quat).as_euler("xyz")
            fixed_euler = np.array([euler[0] * -1, euler[2], euler[1]])
            quat = R.from_euler("xyz", fixed_euler).as_quat()
            acc = np.array([acc[0] * -1, acc[2], acc[1]])
        
        # Add other device-specific transformations as needed
        # elif device_name == 'phone':
        #     # Phone-specific transformations
        #     pass
        # elif device_name == 'watch':
        #     # Watch-specific transformations
        #     pass
        
        return acc, quat
    
    def _apply_ar_glasses_transformations(self, accelerometer: np.ndarray, quaternion: np.ndarray,
                                        remove_gravity: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply coordinate transformations for AR glasses
        
        AR Glasses frame: X:right, Y:forward, Z:up
        Expected frame: X:right, Y:up, Z:away from user
        """
        # Copy arrays
        acc = accelerometer.copy()
        quat = quaternion.copy()
        
        # Apply coordinate transformation from AR glasses frame to expected frame
        # Transform acceleration: [X:right, Y:forward, Z:up] -> [X:right, Y:up, Z:away]
        transformed_acc = np.array([-acc[0], acc[2], acc[1]])
        
        # Remove gravity if requested
        if remove_gravity:
            try:
                gravity_world = np.array([0, 0, 9.81])
                rotation = R.from_quat(quat)
                gravity_device = rotation.inv().apply(gravity_world)
                transformed_acc = transformed_acc - gravity_device
            except Exception as e:
                logger.warning(f"Failed to remove gravity: {e}")
        
        # Quaternion should remain the same for now
        # Additional quaternion transformations can be added here if needed
        transformed_quat = quat
        
        return transformed_acc, transformed_quat
    
    def _quaternion_to_euler(self, quaternion: np.ndarray) -> np.ndarray:
        """Convert quaternion to Euler angles (roll, pitch, yaw) in degrees"""
        try:
            rotation = R.from_quat(quaternion)
            euler_rad = rotation.as_euler('xyz', degrees=False)
            euler_deg = np.degrees(euler_rad)
            return euler_deg
        except Exception as e:
            logger.warning(f"Failed to convert quaternion to Euler: {e}")
            return np.array([0, 0, 0])




def parse_ios_message(message: str) -> Optional[Dict[str, Any]]:
    """
    Parse iOS sensor message format
    Expected format: "device_id;device_type:timestamp1 timestamp2 ax ay az qx qy qz qw [gx gy gz]"
    """
    try:
        message = message.strip()
        if not message or ';' not in message or ':' not in message:
            return None
        
        # Split device info and data
        device_id_str, raw_data_str = message.split(";", 1)
        device_type, data_str = raw_data_str.split(":", 1)
        
        # Parse numeric data
        data_values = []
        for value_str in data_str.strip().split():
            try:
                data_values.append(float(value_str))
            except ValueError:
                continue
        
        # Need at least 2 timestamps + 3 accel + 4 quat = 9 values
        if len(data_values) < 9:
            logger.warning(f"Insufficient data values: got {len(data_values)}, need at least 9")
            return None
        
        # Extract data components
        timestamps = data_values[:2]
        accelerometer = data_values[2:5]
        quaternion = data_values[5:9]
        
        # Extract gyroscope if available
        gyroscope = data_values[9:12] if len(data_values) >= 12 else [0.0, 0.0, 0.0]
        
        return {
            'device_id': device_id_str,
            'device_name': device_type.lower(),
            'timestamps': timestamps,
            'accelerometer': accelerometer,
            'quaternion': quaternion,
            'gyroscope': gyroscope
        }
        
    except Exception as e:
        logger.error(f"Error parsing iOS message: {e}")
        return None


def parse_ar_glasses_message(message: str) -> Optional[Dict[str, Any]]:
    """
    Parse AR glasses message format from Unity
    Expected format: "timestamp device_timestamp qx qy qz qw ax ay az [gx gy gz]"
    """
    try:
        parts = message.strip().split()
        
        if len(parts) < 9:  # timestamp + device_timestamp + 4 quat + 3 accel
            logger.warning(f"AR glasses data format error: expected at least 9 values, got {len(parts)}")
            return None
        
        # Parse components
        timestamp = float(parts[0])
        device_timestamp = float(parts[1])
        
        # Quaternion (x, y, z, w format from Unity)
        quaternion = [float(parts[i]) for i in range(2, 6)]
        
        # Acceleration
        accelerometer = [float(parts[i]) for i in range(6, 9)]
        
        # Gyroscope if available
        gyroscope = [0.0, 0.0, 0.0]
        if len(parts) >= 12:
            gyroscope = [float(parts[i]) for i in range(9, 12)]
        
        return {
            'device_name': 'glasses',
            'timestamps': [timestamp, device_timestamp],
            'accelerometer': accelerometer,
            'quaternion': quaternion,
            'gyroscope': gyroscope
        }
        
    except Exception as e:
        logger.error(f"Error parsing AR glasses message: {e}")
        return None