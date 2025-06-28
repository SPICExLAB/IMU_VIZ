"""
Input_Utils/sensor_utils.py - Modified MobilePoseR transformations with calibration fix

This module provides utilities for transforming IMU data with a correction
to ensure calibration works as expected with the global frame.

Device coordinate systems:
- Phone/Watch:   X: Right, Y: Up, Z: Out of screen (toward viewer)
- Headphone:     X: Right, Z: Up, Y: Forward (into screen)
- Rokid Glasses: X: Right, Y: Up, Z: Into screen (away from viewer)

Global coordinate system:
- X: Left
- Y: Up
- Z: Into screen (away from viewer)
"""

import numpy as np
from scipy.spatial.transform import Rotation as R

def sensor2global(ori, acc, calibration_quats, device_id):
    """
    Convert the sensor data to the global inertial frame with a fix for calibration.
    
    This is based on MobilePoseR's sensor2global function, but with an added
    transformation to ensure that when a device is placed in the global reference
    orientation and calibrated, the displayed axes align with the global frame.
    
    Args:
        ori: np.ndarray - Device orientation quaternion [x, y, z, w]
        acc: np.ndarray - Device acceleration [x, y, z]
        calibration_quats: dict - Calibration quaternions by device_id
        device_id: str - Device identifier
        
    Returns:
        tuple of (global_orientation, global_acceleration)
    """
    # Get the calibration quaternion for this device
    # If not calibrated, use identity quaternion [0, 0, 0, 1]
    device_mean_quat = calibration_quats.get(device_id, np.array([0, 0, 0, 1]))

    # Convert quaternions to rotation matrices
    og_mat = R.from_quat(ori).as_matrix()  # Device orientation as matrix
    global_inertial_frame = R.from_quat(device_mean_quat).as_matrix()  # Calibration as matrix
    
    # Transform orientation to global frame by applying inverse calibration
    # (global_inertial_frame.T) is the inverse of the calibration matrix
    global_mat = (global_inertial_frame.T).dot(og_mat)
    
    # For phone/watch devices, apply an additional 180° Y-axis rotation
    # when calibrated to flip the coordinate system
    if device_id in ['phone', 'watch'] and device_id in calibration_quats:
        # Create a 180° rotation around Y axis
        y_flip = R.from_euler('y', 180, degrees=True).as_matrix()
        global_mat = y_flip.dot(global_mat)
    
    global_ori = R.from_matrix(global_mat).as_quat()

    # Transform acceleration to global frame
    # First align acceleration to sensor frame of reference
    acc_ref_frame = og_mat.dot(acc)
    # Then align acceleration to world frame using inverse calibration
    global_acc = (global_inertial_frame.T).dot(acc_ref_frame)
    
    # Apply the same coordinate flip to acceleration if needed
    if device_id in ['phone', 'watch'] and device_id in calibration_quats:
        # Flip X and Z components
        global_acc = np.array([-global_acc[0], global_acc[1], -global_acc[2]])

    return global_ori, global_acc

def preprocess_headphone_data(quaternion, acceleration):
    """
    Preprocess headphone data to align coordinate systems before sensor2global.
    
    Headphone device frame: X: Right, Z: Up, Y: Forward
    Standard device frame:  X: Right, Y: Up, Z: Out of screen
    
    Args:
        quaternion: np.ndarray - Orientation quaternion [x, y, z, w]
        acceleration: np.ndarray - Acceleration [x, y, z]
        
    Returns:
        tuple of (aligned_quaternion, aligned_acceleration)
    """
    # For headphones, Z is up and Y is forward, so we need to:
    # 1. Swap Y and Z
    # 2. Keep the new Z pointing toward the user
    
    # For acceleration: [x, y, z] -> [x, z, y]
    aligned_acceleration = np.array([
        acceleration[0],  # X stays the same
        acceleration[2],  # Z becomes Y
        -acceleration[1]   # Y becomes Z
    ])
    
    # For quaternion, apply a rotation that does the same axis change
    device_rotation = R.from_quat(quaternion)
    
    # Create rotation that swaps Y and Z
    transform = R.from_euler('x', 90, degrees=True)
    
    # Apply to quaternion
    aligned_rotation = transform * device_rotation
    aligned_quaternion = aligned_rotation.as_quat()
    
    return aligned_quaternion, aligned_acceleration

def preprocess_rokid_data(quaternion, acceleration):
    """
    Preprocess Rokid glasses data to align coordinate systems before sensor2global.
    
    Rokid device frame:    X: Right, Y: Up, Z: Into screen
    Standard device frame: X: Right, Y: Up, Z: Out of screen
    
    This aligns the Rokid's coordinates to match the standard format
    expected by sensor2global.
    
    Args:
        quaternion: np.ndarray - Orientation quaternion [x, y, z, w]
        acceleration: np.ndarray - Acceleration [x, y, z]
        
    Returns:
        tuple of (aligned_quaternion, aligned_acceleration)
    """
    # The Rokid glasses have Z pointing into screen, while our standard frame
    # has Z pointing out of screen. We need to flip Z.
    
    # Flip Z for acceleration
    aligned_acceleration = np.array([
        acceleration[0],    # X stays the same
        acceleration[1],    # Y stays the same
        -acceleration[2]    # Z is flipped
    ])
    
    # Apply a 180° rotation around Y axis to flip Z
    device_rotation = R.from_quat(quaternion)
    transform = R.from_euler('y', 180, degrees=True)
    aligned_rotation = transform * device_rotation
    aligned_quaternion = aligned_rotation.as_quat()
    
    return aligned_quaternion, aligned_acceleration

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
        print(f"Error in gravity compensation: {e}")
        return acceleration