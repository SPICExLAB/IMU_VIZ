"""
Input_Utils/sensor_utils.py - Enhanced coordinate transformations with parsing

This module provides utilities for transforming IMU data with improved coordinate 
handling, calibration support, and data parsing.

Device coordinate systems:
- Phone/Watch:   X: Right, Y: Up, Z: Toward user (out from screen, Backward)
- Headphone:     X: Right, Y: Forward, Z: Up
- Rokid Glasses: X: Right, Y: Up, Z: Forward

Global coordinate system:
- X: Left
- Y: Up
- Z: Forward

Strategy:
- Phone/Watch: Regular calibration with 180° Y-flip when needed
- Headphone/Glasses: Pre-transform directly to global frame to simplify calibration
"""

import numpy as np
from scipy.spatial.transform import Rotation as R
import logging
from dataclasses import dataclass

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


def preprocess_headphone_data(quaternion, acceleration):
    """
    Preprocess headphone data to align DIRECTLY with global coordinate system.
    
    Headphone device frame: X: Right, Z: Up, Y: Forward
    Global frame:           X: Left,  Y: Up, Z: Forward
    
    Args:
        quaternion: np.ndarray - Orientation quaternion [x, y, z, w]
        acceleration: np.ndarray - Acceleration [x, y, z]
        
    Returns:
        tuple of (aligned_quaternion, aligned_acceleration)
    """
    # Direct transformation to global frame:
    # 1. Negate X (right → left)
    # 2. Keep Y (up)
    # 3. Keep Z (forward)
    # 4. Apply rotations to align axes
    
    # Create combined transformation:
    # - Swap Y and Z (90° X rotation)
    # - Negate X (180° Y rotation)
    transform = R.from_euler('xy', [90, 180], degrees=True)
    
    # Apply to quaternion
    device_rotation = R.from_quat(quaternion)
    aligned_rotation = transform * device_rotation
    aligned_quaternion = aligned_rotation.as_quat()
    
    # For acceleration: apply corresponding transformation
    # Original [ax, ay, az] -> [-ax, az, ay]
    aligned_acceleration = np.array([
        -acceleration[0],  # -X (right to left)
        acceleration[2],   # Z becomes Y (up)
        acceleration[1]    # Y becomes Z (forward)
    ])
    
    return aligned_quaternion, aligned_acceleration

def preprocess_rokid_data(quaternion, acceleration):
    """
    Preprocess Rokid glasses data to align DIRECTLY with global coordinate system.
    
    Rokid device frame:   X: Right, Y: Up, Z: Forward
    Global frame:         X: Left,  Y: Up, Z: Forward
    
    Args:
        quaternion: np.ndarray - Orientation quaternion [x, y, z, w]
        acceleration: np.ndarray - Acceleration [x, y, z]
        
    Returns:
        tuple of (aligned_quaternion, aligned_acceleration)
    """
    # Direct transformation to global frame:
    # Simply flip X axis (right → left)
    
    # Create 180° rotation around Y axis
    transform = R.from_euler('y', 180, degrees=True)
    
    # Apply to quaternion
    device_rotation = R.from_quat(quaternion)
    aligned_rotation = transform * device_rotation
    aligned_quaternion = aligned_rotation.as_quat()
    
    # For acceleration: flip X
    aligned_acceleration = np.array([
        -acceleration[0],  # -X (right to left)
        acceleration[1],   # Y stays the same (up)
        acceleration[2]    # Z stays the same (forward)
    ])
    
    return aligned_quaternion, aligned_acceleration

def apply_calibration_transform(ori, acc, calibration_quats, device_id):
    """
    Apply calibration transformation to sensor data without unwanted rotations.
    
    This assumes the user has physically aligned the device with the global frame
    before calibration. No Y-axis flip is applied as that happens physically.
    
    Args:
        ori: np.ndarray - Device orientation quaternion [x, y, z, w]
        acc: np.ndarray - Device acceleration [x, y, z]
        calibration_quats: dict - Calibration quaternions by device_id
        device_id: str - Device identifier
        
    Returns:
        tuple of (transformed_orientation, transformed_acceleration)
    """
    # Get the calibration quaternion for this device
    # If not calibrated, use identity quaternion [0, 0, 0, 1]
    device_calib_quat = calibration_quats.get(device_id, np.array([0, 0, 0, 1]))

    # Convert quaternions to rotation matrices
    device_rot = R.from_quat(ori).as_matrix()
    calib_rot = R.from_quat(device_calib_quat).as_matrix()
    
    # Apply calibration to orientation - simply the inverse of calibration
    # This shows the device's movement relative to its calibration position
    transformed_rot = calib_rot.T.dot(device_rot)
    
    # Apply same transformation to acceleration
    # First align acceleration to device's local frame
    acc_local = device_rot.dot(acc)
    
    # Then transform to global frame using calibration
    transformed_acc = calib_rot.T.dot(acc_local)
    
    # Convert rotation matrix back to quaternion
    transformed_quat = R.from_matrix(transformed_rot).as_quat()
    
    return transformed_quat, transformed_acc


def apply_mobileposer_calibration(current_orientations, reference_device=None):
    """
    Apply calibration with selectable reference device.
    
    This function correctly handles the case where the phone/watch is
    already physically aligned with the global frame (screen facing away).
    
    Args:
        current_orientations: dict - Current device orientations {device_id: quaternion}
        reference_device: str - Device to use as reference (default: auto-select)
        
    Returns:
        tuple - (calibration_quats, reference_device)
            calibration_quats: dict - Updated calibration quaternions
            reference_device: str - The device used as reference
    """
    if not current_orientations:
        return {}, None
    
    # If no reference device specified, select one automatically
    if reference_device is None or reference_device not in current_orientations:
        # Priority order: phone, glasses, watch, headphone
        for device in ['phone', 'glasses', 'watch', 'headphone']:
            if device in current_orientations:
                reference_device = device
                break
        
        if reference_device is None:
            # Still no reference device, use first in dict
            reference_device = next(iter(current_orientations))
    
    logger.info(f"Calibrating using {reference_device} as reference device")
    
    # Get reference quaternion
    ref_quat = current_orientations[reference_device]
    ref_rotation = R.from_quat(ref_quat)
    
    # For phone/watch reference, we need to check if we need a transformation
    # We're assuming the user has physically oriented the device with screen facing away
    # But we need to check the orientation to see if it's already aligned with global frame
    if reference_device in ['phone', 'watch']:
        # Convert to Euler angles to check orientation
        ref_euler = ref_rotation.as_euler('xyz', degrees=True)
        logger.info(f"Reference device ({reference_device}) Euler angles: {ref_euler}")
        
        # If Z axis is approximately pointing toward user (screen facing toward user)
        # we need to apply a 180° Y-flip to correctly align with global frame
        # This happens if the user calibrated with screen facing them
        if abs(ref_euler[2]) < 90:  # Z-axis pointing approximately toward user
            logger.info(f"Applying 180° Y-flip to {reference_device} to align with global frame")
            y_flip = R.from_euler('y', 180, degrees=True)
            ref_rotation = y_flip * ref_rotation
    
    # Store calibration quaternions
    calibration_quats = {}
    
    # For each device, calculate the calibration quaternion
    for device_id, curr_quat in current_orientations.items():
        curr_rotation = R.from_quat(curr_quat)
        
        if device_id == reference_device:
            # Reference device gets its current orientation with potential Y-flip
            calibration_quats[device_id] = ref_rotation.as_quat()
        else:
            # Other devices get calibrated relative to the reference device
            # Calculate relative quaternion for calibration
            relative_rotation = ref_rotation.inv() * curr_rotation
            calibration_quats[device_id] = relative_rotation.as_quat()
    
    # Log calibration results
    for device_id, quat in calibration_quats.items():
        logger.info(f"Calibration quat for {device_id}: [{quat[0]:.3f}, {quat[1]:.3f}, {quat[2]:.3f}, {quat[3]:.3f}]")
    
    return calibration_quats, reference_device

def apply_gravity_compensation(quaternion, acceleration, gravity_magnitude=9.81):
    """
    Remove gravity component from acceleration vector.
    
    Args:
        quaternion: np.ndarray - Orientation quaternion [x, y, z, w]
        acceleration: np.ndarray - Acceleration [x, y, z]
        gravity_magnitude: float - Magnitude of gravity
        
    Returns:
        np.ndarray - Linear acceleration with gravity removed
    """
    try:
        # Define gravity in world frame (pointing down)
        gravity_world = np.array([0, -gravity_magnitude, 0])
        
        # Convert to device frame using inverse of orientation
        rotation = R.from_quat(quaternion)
        gravity_device_frame = rotation.inv().apply(gravity_world)
        
        # Remove gravity from raw acceleration
        linear_acceleration = acceleration - gravity_device_frame
        
        return linear_acceleration
        
    except Exception as e:
        logger.error(f"Error in gravity compensation: {e}")
        return acceleration

# -------------------- Parsing Methods --------------------

def parse_phone_data(data_str):
    """
    Parse phone data (screen-based device).
    
    Args:
        data_str: str - Raw data string from phone
        
    Returns:
        tuple - (timestamp, device_quat, device_accel, gyro, euler)
    """
    parts = data_str.split()
    if len(parts) < 11:
        raise ValueError(f"Incomplete phone data: expected at least 11 parts, got {len(parts)}")
        
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
    
    return timestamp, device_quat, device_accel, gyro, euler

def parse_headphone_data(data_str):
    """
    Parse headphone data.
    
    Args:
        data_str: str - Raw data string from headphone
        
    Returns:
        tuple - (timestamp, device_quat, device_accel, gyro, aligned_quat, aligned_accel)
    """
    parts = data_str.split()
    if len(parts) < 9:
        raise ValueError(f"Incomplete headphone data: expected at least 9 parts, got {len(parts)}")
        
    timestamp = float(parts[0])
    
    # Get device-frame data
    device_accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
    device_quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
    
    # AirPods don't typically send gyroscope data
    gyro = np.array([0.0, 0.0, 0.0])
    
    # Preprocess headphone data to DIRECTLY match global frame
    # This transforms: (X:right, Z:up, Y:forward) -> (X:left, Y:up, Z:forward)
    aligned_quat, aligned_accel = preprocess_headphone_data(device_quat, device_accel)
    
    return timestamp, device_quat, device_accel, gyro, aligned_quat, aligned_accel

def parse_watch_data(data_str):
    """
    Parse Apple Watch data.
    
    Args:
        data_str: str - Raw data string from watch
        
    Returns:
        tuple - (timestamp, device_quat, device_accel, gyro, None)
    """
    parts = data_str.split()
    if len(parts) < 12:
        raise ValueError(f"Incomplete watch data: expected at least 12 parts, got {len(parts)}")
        
    timestamp = float(parts[0])
    device_timestamp = float(parts[1])
    
    # Parse device-frame data
    device_accel = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
    device_quat = np.array([float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8])])
    gyro = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
    
    return timestamp, device_quat, device_accel, gyro, None

def parse_rokid_glasses_data(data_str):
    """
    Parse Rokid Glasses data.
    
    Args:
        data_str: str - Raw data string from Rokid glasses
        
    Returns:
        tuple - (timestamp, device_quat, device_accel, gyro, aligned_quat, aligned_accel)
    """
    parts = data_str.split()
    if len(parts) != 12:
        raise ValueError(f"Rokid Glasses data format error: expected 12 values, got {len(parts)}")
        
    # Parse Unity's format
    timestamp = float(parts[0])
    device_timestamp = float(parts[1])
    
    # Parse quaternion from Unity (x, y, z, w format)
    device_quat = np.array([float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])])
    
    # Parse sensor data
    device_accel = np.array([float(parts[6]), float(parts[7]), float(parts[8])])
    gyro = np.array([float(parts[9]), float(parts[10]), float(parts[11])])
    
    # Preprocess Rokid data to DIRECTLY match global frame
    aligned_quat, aligned_accel = preprocess_rokid_data(device_quat, device_accel)
    
    return timestamp, device_quat, device_accel, gyro, aligned_quat, aligned_accel

def parse_ios_data(message):
    """
    Parse iOS device data message.
    
    Args:
        message: str - Raw message from iOS device
        
    Returns:
        tuple - (device_id, parsed_data)
            parsed_data: tuple - Parsed device data (format depends on device type)
    """
    if not ';' in message:
        raise ValueError("Invalid iOS data format: missing ';' separator")
        
    device_prefix, data_part = message.split(';', 1)
    
    if data_part.startswith('phone:'):
        return 'phone', parse_phone_data(data_part[6:])
    elif data_part.startswith('headphone:'):
        return 'headphone', parse_headphone_data(data_part[10:])
    elif data_part.startswith('watch:'):
        return 'watch', parse_watch_data(data_part[6:])
    else:
        raise ValueError(f"Unknown iOS device type in message: {message}")

def calculate_euler_from_quaternion(quaternion):
    """
    Calculate Euler angles from quaternion.
    
    Args:
        quaternion: np.ndarray - Quaternion [x, y, z, w]
        
    Returns:
        np.ndarray - Euler angles [nod, turn, tilt] in degrees
    """
    try:
        rotation = R.from_quat(quaternion)
        euler_rad = rotation.as_euler('xyz', degrees=False)
        euler_deg = euler_rad * 180.0 / np.pi
        
        # Map to head movements: nod, turn, tilt
        nod = euler_deg[0]    # X rotation = NOD (up/down)
        turn = euler_deg[1]   # Y rotation = TURN (left/right)  
        tilt = euler_deg[2]   # Z rotation = TILT (left/right tilt)
        
        return np.array([nod, turn, tilt])
    except Exception as e:
        logger.warning(f"Error calculating Euler angles: {e}")
        return np.array([0, 0, 0])