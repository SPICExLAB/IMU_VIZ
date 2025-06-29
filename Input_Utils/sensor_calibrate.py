"""
Input_Utils/sensor_calibrate.py - IMU calibration and reference device handling

This module provides calibration functionality for IMU devices with support
for reference device selection and global frame alignment.
"""

import numpy as np
import logging
from scipy.spatial.transform import Rotation as R

logger = logging.getLogger(__name__)

class IMUCalibrator:
    """
    Handles calibration of IMU devices with selectable reference device.
    """
    
    def __init__(self):
        # Store reference quaternions for each device (the "zero" position)
        self.reference_quaternions = {}
        # Currently selected reference device
        self.reference_device = None
        # Record which devices are calibrated
        self.calibrated_devices = set()
    
    def set_reference_orientation(self, device_id: str, current_quaternion: np.ndarray):
        """Set current orientation as the reference/zero position for a single device"""
        self.reference_quaternions[device_id] = current_quaternion.copy()
        self.calibrated_devices.add(device_id)
        
        logger.info(f"Set reference orientation for {device_id}")
        logger.info(f"   Reference quat: [{current_quaternion[0]:.3f}, {current_quaternion[1]:.3f}, "
                   f"{current_quaternion[2]:.3f}, {current_quaternion[3]:.3f}]")
        
        # Calculate Euler angles for logging
        try:
            r = R.from_quat(current_quaternion)
            euler = r.as_euler('xyz', degrees=True)
            logger.info(f"   Reference euler: X={euler[0]:.1f}° Y={euler[1]:.1f}° Z={euler[2]:.1f}°")
        except Exception as e:
            logger.warning(f"Could not calculate Euler angles: {e}")
    
    def calibrate_all_devices(self, current_orientations, reference_device=None):
        """
        Calibrate all devices using a reference device.
        
        Args:
            current_orientations: dict - Current orientations {device_id: quaternion}
            reference_device: str - Device to use as reference (default: auto-select)
        
        Returns:
            str - The device used as reference
        """
        if not current_orientations:
            logger.warning("No device orientations provided for calibration")
            return None
        
        # Apply MobilePoseR-style calibration
        from .sensor_utils import apply_mobileposer_calibration
        new_calibration, ref_device = apply_mobileposer_calibration(
            current_orientations, 
            reference_device
        )
        
        # Update reference quaternions
        self.reference_quaternions = new_calibration
        self.reference_device = ref_device
        
        # Update calibrated devices
        self.calibrated_devices = set(new_calibration.keys())
        
        # Log success
        calibrated_devices = list(self.calibrated_devices)
        if calibrated_devices:
            logger.info(f"Calibrated devices: {', '.join(calibrated_devices)}")
            logger.info(f"Reference device: {self.reference_device}")
        else:
            logger.warning("No active devices to calibrate")
        
        return self.reference_device
    
    def is_calibrated(self, device_id):
        """Check if a device is calibrated"""
        return device_id in self.calibrated_devices
    
    def get_reference_device(self):
        """Get the current reference device"""
        return self.reference_device
    
    def get_calibration_quaternions(self):
        """Get all calibration quaternions"""
        return self.reference_quaternions.copy()