#!/usr/bin/env python3
"""
IMU_receiver.py - Refactored with improved modular structure

Key improvements:
- Enhanced modular design with separate calibration and parsing modules
- Improved coordinate transformations for all device types
- Support for reference device selection
- Pre-transformation of headphones and AR glasses to global frame
"""

import numpy as np
import time
from collections import deque
import logging
from scipy.spatial.transform import Rotation as R

# Import our visualization module
from UI.main_visualizer import IMUVisualizer

# Import our input utilities
from Input_Utils.socket_utils import SocketReceiver, ApiServer

# Import our sensor utilities
from Input_Utils.sensor_utils import (
    # Data types
    IMUData,
    
    # Transformation functions
    apply_calibration_transform,
    apply_gravity_compensation,
    calculate_euler_from_quaternion,
    apply_mobileposer_calibration,
    
    # Parsing functions
    parse_ios_data,
    parse_rokid_glasses_data
)

# Import calibration module
from Input_Utils.sensor_calibrate import IMUCalibrator

logging.basicConfig(level=logging.INFO,
                              format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


class IMUReceiver:
    """Core IMU receiver with reference device selection before calibration"""
    
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
                'calibrate': self.request_calibration,
                'select_reference_device': self._select_reference_device
            }
        )
        
        # Store instance for external access
        IMUReceiver._instance = self
        
        logger.info(f"Enhanced IMU Receiver initialized with reference device selection")
        logger.info(f"Data port: {data_port}, API port: {api_port}")
        logger.info("Headphones/AR Glasses pre-transformed to global frame for easier calibration")
    
    @classmethod
    def get_instance(cls):
        """Get the current IMUReceiver instance for external access"""
        return cls._instance
    
    def request_calibration(self):
        """Request calibration (can be called internally or externally)"""
        self.calibration_requested = True
        # Use the selected reference device from visualizer
        logger.info(f"Calibration requested")
        return True
    
    def _select_reference_device(self, device_id):
        """Select a device as reference (can be called via API)"""
        if device_id in self.current_orientations:
            # Log orientation at time of selection
            curr_quat = self.current_orientations[device_id]
            euler = calculate_euler_from_quaternion(curr_quat)
            logger.info(f"REFERENCE SELECTION: {device_id} orientation at selection: "
                    f"Roll={euler[0]:.1f}°, Pitch={euler[1]:.1f}°, Yaw={euler[2]:.1f}°")
            logger.info(f"REFERENCE SELECTION: {device_id} quaternion at selection: "
                    f"[{curr_quat[0]:.3f}, {curr_quat[1]:.3f}, {curr_quat[2]:.3f}, {curr_quat[3]:.3f}]")
            
            success = self.visualizer.select_reference_device(device_id)
            if success:
                logger.info(f"Selected {device_id} as reference device")
            return success
        return False
    
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
            'is_calibrated': device_id in self.calibrator.reference_quaternions,
            'is_reference': device_id == self.calibrator.reference_device
        }
    
    def _parse_data(self, message, addr):
        """Parse incoming data from socket"""
        try:
            # Handle iOS system messages
            if isinstance(message, str):
                if message == "client_initialized":
                    logger.info(f"iOS device connected from {addr[0]}")
                    return
                elif message == "client_disconnected":
                    logger.info(f"iOS device disconnected")
                    return
            
            # Check if it's iOS format (contains ';' and device prefixes)
            if ';' in message and ('phone:' in message or 'headphone:' in message or 'watch:' in message):
                try:
                    # Use the parsing function from sensor_utils
                    device_id, parsed_data = parse_ios_data(message)
                    self._process_device_data(device_id, parsed_data, addr)
                except Exception as e:
                    logger.warning(f"iOS parse error: {e}")
            else:
                # Assume it's Rokid Glasses Unity format
                try:
                    # Use the parsing function from sensor_utils
                    parsed_data = parse_rokid_glasses_data(message)
                    device_id = self.socket_receiver.get_device_id_for_ip(addr[0], 'glasses')
                    self._process_device_data(device_id, parsed_data, addr)
                except Exception as e:
                    logger.warning(f"Rokid Glasses parse error: {e}")
                    
        except Exception as e:
            logger.warning(f"Parse error: {e}")
    
    def _process_device_data(self, device_id, parsed_data, addr):
        """
        Process parsed device data.
        
        Args:
            device_id: str - Device identifier
            parsed_data: tuple - Parsed data from device
            addr: tuple - Socket address (host, port)
        """
        try:
            timestamp, device_quat, device_accel, gyro, aligned_data = parsed_data
            
            # Log initial connection and orientation
            if device_id not in self.current_orientations:
                logger.info(f"Initial connection from {device_id} at {addr[0]}")
                
                # Log initial orientation
                euler = calculate_euler_from_quaternion(device_quat)
                logger.info(f"CONNECTED: {device_id} initial orientation: "
                        f"Roll={euler[0]:.1f}°, Pitch={euler[1]:.1f}°, Yaw={euler[2]:.1f}°")
                logger.info(f"CONNECTED: {device_id} initial quaternion: "
                        f"[{device_quat[0]:.3f}, {device_quat[1]:.3f}, {device_quat[2]:.3f}, {device_quat[3]:.3f}]")
            
            # Store raw data for future reference
            self.raw_device_data[device_id] = {
                'quaternion': device_quat,
                'acceleration': device_accel,
                'gyroscope': gyro
            }
            
            # For all devices, use the pre-aligned data if available
            if aligned_data is not None:
                aligned_quat, aligned_accel = aligned_data
                
                # Store original and aligned data
                self.raw_device_data[device_id].update({
                    'aligned_quaternion': aligned_quat,
                    'aligned_acceleration': aligned_accel
                })
                
                # Use aligned data for calibration and transformation
                quat_for_calibration = aligned_quat
                accel_for_processing = aligned_accel
                
                # Store the aligned quaternion for calibration
                self.current_orientations[device_id] = aligned_quat
            else:
                # Fallback to original data if no alignment available
                quat_for_calibration = device_quat
                accel_for_processing = device_accel
                
                # Store the original quaternion for calibration
                self.current_orientations[device_id] = device_quat
                
                # Log current raw orientation periodically (every 30 frames)
                if device_id in self.raw_device_data and 'frame_counter' in self.raw_device_data[device_id]:
                    frame_counter = self.raw_device_data[device_id]['frame_counter'] + 1
                    self.raw_device_data[device_id]['frame_counter'] = frame_counter
                    
                    if frame_counter % 30 == 0:
                        euler = calculate_euler_from_quaternion(device_quat)
                        logger.debug(f"RAW: {device_id} orientation: "
                                f"Roll={euler[0]:.1f}°, Pitch={euler[1]:.1f}°, Yaw={euler[2]:.1f}°")
                else:
                    # Initialize frame counter
                    self.raw_device_data[device_id]['frame_counter'] = 0
            
            # Apply calibration transformation if device is calibrated
            calibration_quats = self.calibrator.get_calibration_quaternions()
            reference_device = self.calibrator.reference_device
            if device_id in calibration_quats:
                # Transform using calibration
                global_quat, global_acc = apply_calibration_transform(
                    quat_for_calibration, 
                    accel_for_processing, 
                    calibration_quats, 
                    device_id,
                    reference_device=reference_device
                )
            else:
                # Not calibrated - use as is
                global_quat = quat_for_calibration
                global_acc = accel_for_processing
            
            # Apply gravity compensation if enabled for glasses
            if self.visualizer.get_gravity_enabled() and device_id == 'glasses':
                linear_accel = apply_gravity_compensation(global_quat, global_acc)
            else:
                # Use acceleration without gravity compensation
                linear_accel = global_acc
            
            # Calculate Euler angles for display
            euler_deg = calculate_euler_from_quaternion(global_quat)
            
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
                    
        except Exception as e:
            logger.warning(f"Error processing {device_id} data: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def calibrate_all_devices(self):
        """
        Calibrate all active devices using the selected reference device.
        
        This assumes the user has already physically aligned the reference device
        with the global frame before calibration.
        """
        # Get the selected reference device
        reference_device = self.visualizer.get_selected_reference_device()
        
        # If no reference device is selected, don't proceed
        if not reference_device:
            logger.warning("No reference device selected for calibration")
            return None
        
        # Log raw orientation at time of calibration
        for device_id, quaternion in self.current_orientations.items():
            try:
                euler = calculate_euler_from_quaternion(quaternion)
                logger.info(f"PRE-CALIBRATION RAW: {device_id} orientation: "
                        f"Roll={euler[0]:.1f}°, Pitch={euler[1]:.1f}°, Yaw={euler[2]:.1f}°")
                logger.info(f"PRE-CALIBRATION RAW: {device_id} quaternion: "
                        f"[{quaternion[0]:.3f}, {quaternion[1]:.3f}, {quaternion[2]:.3f}, {quaternion[3]:.3f}]")
            except:
                pass
        
        # Apply calibration
        from Input_Utils.sensor_utils import apply_mobileposer_calibration
        calibration_quats, ref_device = apply_mobileposer_calibration(
            self.current_orientations,
            reference_device
        )
        
        # Update calibrator with new calibration quaternions
        for device_id, quat in calibration_quats.items():
            self.calibrator.set_reference_orientation(device_id, quat)
        
        # Update reference device in calibrator
        self.calibrator.reference_device = ref_device
        
        # Update reference device in visualizer
        self.visualizer.set_reference_device(ref_device)
        
        logger.info(f"Calibration complete using {ref_device} as reference device")
        
        # Log Euler angles for each device after calibration
        for device_id, quaternion in self.current_orientations.items():
            try:
                # Log raw orientation after calibration
                euler = calculate_euler_from_quaternion(quaternion)
                logger.info(f"POST-CALIBRATION RAW: {device_id} orientation: "
                        f"Roll={euler[0]:.1f}°, Pitch={euler[1]:.1f}°, Yaw={euler[2]:.1f}°")
                
                # If device is calibrated, log its calibrated orientation
                if device_id in calibration_quats:
                    cal_quat = calibration_quats[device_id]
                    cal_euler = calculate_euler_from_quaternion(cal_quat)
                    logger.info(f"CALIBRATION QUATERNION: {device_id}: "
                            f"[{cal_quat[0]:.3f}, {cal_quat[1]:.3f}, {cal_quat[2]:.3f}, {cal_quat[3]:.3f}]")
                    logger.info(f"CALIBRATION EULER: {device_id}: "
                            f"Roll={cal_euler[0]:.1f}°, Pitch={cal_euler[1]:.1f}°, Yaw={cal_euler[2]:.1f}°")
                    
                    # Attempt to log what would be displayed with this calibration
                    try:
                        # This will show what happens when we apply the calibration to current orientation
                        global_quat, _ = apply_calibration_transform(
                            quaternion, 
                            np.zeros(3), 
                            calibration_quats, 
                            device_id
                        )
                        display_euler = calculate_euler_from_quaternion(global_quat)
                        logger.info(f"DISPLAY ORIENTATION: {device_id}: "
                                f"Roll={display_euler[0]:.1f}°, Pitch={display_euler[1]:.1f}°, Yaw={display_euler[2]:.1f}°")
                    except Exception as e:
                        logger.warning(f"Could not calculate display orientation: {e}")
                        
            except Exception as e:
                logger.warning(f"Could not log orientation for {device_id}: {e}")
        
        return ref_device
    
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
                elif event and event.startswith("select_reference:"):
                    # Handle reference device selection
                    device_id = event.split(":", 1)[1]
                    self._select_reference_device(device_id)
                
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
    print("IMU Receiver with Enhanced Calibration")
    print("=============================")
    print("Device Positioning for Calibration:")
    print("  All devices: Place vertically with screen/front facing you")
    print()
    print("Global frame:    X:left, Y:up, Z:forward (into screen)")
    print("Visualization:   All devices shown in global frame")
    print()
    print("Calibration:")
    print("  1. Select which device sets the reference frame")
    print("  2. Position the device vertically with screen facing you")
    print("  3. Calibrate all devices relative to this reference")
    print()
    print("External API: Available on port 9001")
    
    receiver = IMUReceiver(data_port=8001, api_port=9001)
    receiver.run()

if __name__ == "__main__":
    main()