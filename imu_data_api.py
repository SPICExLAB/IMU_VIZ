"""
IMU Data API - External interface for accessing calibrated IMU data
File: imu_data_api.py
"""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from scipy.spatial.transform import Rotation as R

@dataclass
class CalibratedIMUData:
    """Calibrated IMU data structure for external APIs"""
    timestamp: float
    device_name: str
    frequency: float
    acceleration: np.ndarray      # [3] - gravity-removed, calibrated
    rotation_matrix: np.ndarray   # [3, 3] - calibrated relative to T-pose
    gyroscope: Optional[np.ndarray] = None  # [3] - gyroscope data if available
    is_calibrated: bool = False

class IMUDataAPI:
    """
    External API for accessing calibrated IMU data from IMUReceiver
    """
    
    def __init__(self, imu_receiver):
        """
        Initialize API with reference to IMUReceiver instance
        
        Args:
            imu_receiver: IMUReceiver instance
        """
        self.receiver = imu_receiver
    
    def get_device_data(self, device_id: str) -> Optional[CalibratedIMUData]:
        """
        Get calibrated IMU data for a specific device
        
        Args:
            device_id: Device identifier ('phone', 'watch', 'headphone', 'glasses')
            
        Returns:
            CalibratedIMUData object or None if device not active/calibrated
        """
        if device_id not in self.receiver.current_orientations:
            return None
            
        # Check if device is active (received data recently)
        device_data = self.receiver.visualizer.device_data.get(device_id)
        if not device_data:
            return None
            
        current_time = time.time()
        if current_time - device_data['last_update'] > 2.0:
            return None  # Device inactive
            
        # Get current raw data
        raw_quaternion = self.receiver.current_orientations[device_id]
        
        # Get calibrated quaternion (this is what the 3D visualization uses)
        calibrated_quat = self.receiver.calibrator.get_relative_orientation(device_id, raw_quaternion)
        
        # Convert calibrated quaternion to 3x3 rotation matrix
        try:
            rotation_matrix = R.from_quat(calibrated_quat).as_matrix()
        except Exception:
            rotation_matrix = np.eye(3)  # Identity matrix fallback
            
        # Get latest acceleration (already processed with gravity toggle)
        acceleration_history = device_data.get('accel_history', [])
        if len(acceleration_history) == 0:
            return None
            
        latest_acceleration = np.array(acceleration_history[-1])
        
        # Get gyroscope data if available
        gyroscope_data = None
        gyro_history = device_data.get('gyro_history', [])
        if len(gyro_history) > 0:
            latest_gyro = np.array(gyro_history[-1])
            # Only include if it's not zero (some devices don't send gyro)
            if np.linalg.norm(latest_gyro) > 0.001:
                gyroscope_data = latest_gyro
        
        return CalibratedIMUData(
            timestamp=device_data['last_update'],
            device_name=device_id,
            frequency=device_data.get('frequency', 0.0),
            acceleration=latest_acceleration,
            rotation_matrix=rotation_matrix,
            gyroscope=gyroscope_data,
            is_calibrated=device_id in self.receiver.calibrator.reference_quaternions
        )
    
    def get_all_device_data(self) -> Dict[str, CalibratedIMUData]:
        """
        Get calibrated IMU data for all active devices
        
        Returns:
            Dictionary mapping device_id to CalibratedIMUData
        """
        all_data = {}
        for device_id in self.receiver.device_order:
            device_data = self.get_device_data(device_id)
            if device_data is not None:
                all_data[device_id] = device_data
        return all_data
    
    def get_active_devices(self) -> List[str]:
        """
        Get list of currently active device IDs
        
        Returns:
            List of active device identifiers
        """
        active_devices = []
        current_time = time.time()
        
        for device_id, device_data in self.receiver.visualizer.device_data.items():
            if current_time - device_data['last_update'] < 2.0:
                active_devices.append(device_id)
                
        return active_devices
    
    def get_calibrated_devices(self) -> List[str]:
        """
        Get list of calibrated device IDs
        
        Returns:
            List of calibrated device identifiers
        """
        return list(self.receiver.calibrator.reference_quaternions.keys())
    
    def is_device_calibrated(self, device_id: str) -> bool:
        """
        Check if a specific device is calibrated
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if device is calibrated, False otherwise
        """
        return device_id in self.receiver.calibrator.reference_quaternions
    
    def get_device_frequencies(self) -> Dict[str, float]:
        """
        Get current frequency for all active devices
        
        Returns:
            Dictionary mapping device_id to frequency in Hz
        """
        frequencies = {}
        for device_id in self.get_active_devices():
            device_data = self.receiver.visualizer.device_data.get(device_id)
            if device_data:
                frequencies[device_id] = device_data.get('frequency', 0.0)
        return frequencies
    
    def get_mobileposer_format(self, device_id: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Get data in MobilePOSER expected format for a specific device
        
        Args:
            device_id: Device identifier
            
        Returns:
            Tuple of (acceleration_vector, rotation_matrix) or None
            - acceleration_vector: [3] array in m/s²
            - rotation_matrix: [3, 3] array
        """
        calibrated_data = self.get_device_data(device_id)
        if calibrated_data is None or not calibrated_data.is_calibrated:
            return None
            
        return calibrated_data.acceleration, calibrated_data.rotation_matrix
    
    def get_all_mobileposer_format(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """
        Get data for all calibrated devices in MobilePOSER format
        
        Returns:
            Dictionary mapping device_id to (acceleration, rotation_matrix) tuples
        """
        mobileposer_data = {}
        for device_id in self.receiver.device_order:
            data = self.get_mobileposer_format(device_id)
            if data is not None:
                mobileposer_data[device_id] = data
        return mobileposer_data
    
    def has_gyroscope_data(self, device_id: str) -> bool:
        """
        Check if a device has gyroscope data available
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if device has gyroscope data, False otherwise
        """
        data = self.get_device_data(device_id)
        return data is not None and data.gyroscope is not None
    
    def export_snapshot(self) -> Dict:
        """
        Export current data snapshot for logging/debugging
        
        Returns:
            Complete data snapshot
        """
        return {
            'timestamp': time.time(),
            'active_devices': self.get_active_devices(),
            'calibrated_devices': self.get_calibrated_devices(),
            'device_frequencies': self.get_device_frequencies(),
            'all_device_data': {
                device_id: {
                    'timestamp': data.timestamp,
                    'frequency': data.frequency,
                    'acceleration': data.acceleration.tolist(),
                    'rotation_matrix': data.rotation_matrix.tolist(),
                    'has_gyroscope': data.gyroscope is not None,
                    'gyroscope': data.gyroscope.tolist() if data.gyroscope is not None else None,
                    'is_calibrated': data.is_calibrated
                }
                for device_id, data in self.get_all_device_data().items()
            }
        }


# Usage Examples:
"""

# Get all devices
all_devices = api.get_all_device_data()
for device_id, data in all_devices.items():
    print(f"{device_id}: {data.frequency:.1f} Hz, Calibrated: {data.is_calibrated}")

# Ready for MobilePOSER
mobileposer_data = api.get_all_mobileposer_format()
for device_id, (acc, rot) in mobileposer_data.items():
    print(f"{device_id}: acc={acc.shape}, rot={rot.shape}")

# Check which devices have gyroscope
for device_id in api.get_active_devices():
    has_gyro = api.has_gyroscope_data(device_id)
    print(f"{device_id} has gyroscope: {has_gyro}")
"""