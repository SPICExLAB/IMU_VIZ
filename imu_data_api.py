"""
IMU Data API - Socket-based external interface for accessing calibrated IMU data
File: imu_data_api.py
"""

import time
import socket
import json
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
    Socket-based API for accessing calibrated IMU data from running IMUReceiver
    """
    
    def __init__(self, api_port=9001):
        """Initialize API with socket connection to running receiver"""
        self.api_port = api_port
        self.socket = None
        self._connect()
    
    def _connect(self):
        """Connect to the running IMU receiver API server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(2.0)  # 2 second timeout
            
            # Test connection
            response = self._send_request("ping")
            if response and "status" in response and response["status"] == "ok":
                print("✅ Connected to IMU receiver API server")
            else:
                raise ConnectionError("Invalid response from API server")
                
        except Exception as e:
            raise RuntimeError(f"Cannot connect to IMU receiver. Make sure IMU_receiver.py is running. Error: {e}")
    
    def _send_request(self, request):
        """Send request to API server and get response"""
        try:
            self.socket.sendto(request.encode('utf-8'), ('127.0.0.1', self.api_port))
            data, addr = self.socket.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            return response
        except socket.timeout:
            raise RuntimeError("API server timeout. Is IMU_receiver.py still running?")
        except Exception as e:
            raise RuntimeError(f"API communication error: {e}")
    
    def get_device_data(self, device_id: str) -> Optional[CalibratedIMUData]:
        """
        Get calibrated IMU data for a specific device
        
        Args:
            device_id: Device identifier ('phone', 'watch', 'headphone', 'glasses')
            
        Returns:
            CalibratedIMUData object or None if device not active/calibrated
        """
        try:
            response = self._send_request(f"get_device:{device_id}")
            
            if not response or response is None:
                return None
                
            if "error" in response:
                return None
            
            # Convert response to CalibratedIMUData
            acceleration = np.array(response['acceleration'])
            rotation_matrix = np.array(response['rotation_matrix'])
            gyroscope = np.array(response['gyroscope']) if response['gyroscope'] else None
            
            return CalibratedIMUData(
                timestamp=response['timestamp'],
                device_name=response['device_name'],
                frequency=response['frequency'],
                acceleration=acceleration,
                rotation_matrix=rotation_matrix,
                gyroscope=gyroscope,
                is_calibrated=response['is_calibrated']
            )
            
        except Exception as e:
            print(f"Error getting device data for {device_id}: {e}")
            return None
    
    def get_all_device_data(self) -> Dict[str, CalibratedIMUData]:
        """
        Get calibrated IMU data for all active devices
        
        Returns:
            Dictionary mapping device_id to CalibratedIMUData
        """
        try:
            response = self._send_request("get_all_devices")
            
            if not response or "error" in response:
                return {}
            
            all_data = {}
            for device_id, device_info in response.items():
                if device_info:
                    acceleration = np.array(device_info['acceleration'])
                    rotation_matrix = np.array(device_info['rotation_matrix'])
                    gyroscope = np.array(device_info['gyroscope']) if device_info['gyroscope'] else None
                    
                    all_data[device_id] = CalibratedIMUData(
                        timestamp=device_info['timestamp'],
                        device_name=device_info['device_name'],
                        frequency=device_info['frequency'],
                        acceleration=acceleration,
                        rotation_matrix=rotation_matrix,
                        gyroscope=gyroscope,
                        is_calibrated=device_info['is_calibrated']
                    )
            
            return all_data
            
        except Exception as e:
            print(f"Error getting all device data: {e}")
            return {}
    
    def get_active_devices(self) -> List[str]:
        """
        Get list of currently active device IDs
        
        Returns:
            List of active device identifiers
        """
        try:
            response = self._send_request("get_active_devices")
            
            if response and isinstance(response, list):
                return response
            else:
                return []
                
        except Exception as e:
            print(f"Error getting active devices: {e}")
            return []
    
    def get_calibrated_devices(self) -> List[str]:
        """
        Get list of calibrated device IDs
        
        Returns:
            List of calibrated device identifiers
        """
        all_devices = self.get_all_device_data()
        return [device_id for device_id, data in all_devices.items() if data.is_calibrated]
    
    def is_device_calibrated(self, device_id: str) -> bool:
        """
        Check if a specific device is calibrated
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if device is calibrated, False otherwise
        """
        device_data = self.get_device_data(device_id)
        return device_data is not None and device_data.is_calibrated
    
    def get_device_frequencies(self) -> Dict[str, float]:
        """
        Get current frequency for all active devices
        
        Returns:
            Dictionary mapping device_id to frequency in Hz
        """
        all_devices = self.get_all_device_data()
        return {device_id: data.frequency for device_id, data in all_devices.items()}
    
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
        for device_id in ['phone', 'watch', 'headphone', 'glasses']:
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
    
    def close(self):
        """Close the socket connection"""
        if self.socket:
            self.socket.close()
            self.socket = None


# Convenience function for quick access
def get_imu_api(api_port=9001):
    """
    Convenience function to get IMU API instance
    
    Args:
        api_port: Port number for API server (default 9001)
    
    Returns:
        IMUDataAPI instance connected to running receiver
    """
    return IMUDataAPI(api_port)


# Usage Examples:
"""
# In your demo code:
from imu_data_api import get_imu_api

# Get API (automatically connects to running receiver)
api = get_imu_api()

# Get specific device data
glasses_data = api.get_device_data('glasses')
if glasses_data and glasses_data.is_calibrated:
    print(f"Glasses: {glasses_data.frequency:.1f} Hz")
    print(f"Acceleration: {glasses_data.acceleration}")
    print(f"Rotation matrix: {glasses_data.rotation_matrix.shape}")

# Get all devices
all_devices = api.get_all_device_data()
for device_id, data in all_devices.items():
    print(f"{device_id}: {data.frequency:.1f} Hz, Calibrated: {data.is_calibrated}")

# Ready for MobilePOSER
mobileposer_data = api.get_all_mobileposer_format()
for device_id, (acc, rot) in mobileposer_data.items():
    print(f"{device_id}: acc={acc.shape}, rot={rot.shape}")

# Close connection when done
api.close()
"""