#!/usr/bin/env python3
"""
IMU_receiver.py - Simple main entry point for IMU data reception and visualization
Simplified version focused on responsiveness and your original design
"""

import os
import time
import numpy as np
import logging
from argparse import ArgumentParser
from collections import deque
import threading

# Set pygame hide support prompt before importing
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

from Input_utils.sensor_utils import SensorDataProcessor
from Input_utils.socket_utils import IMUSocketReceiver
from Sensor_UI.main_window import SensorUIWindow

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleDeviceConfig:
    """Simple configuration for device settings"""
    
    def __init__(self):
        # Device index mapping for live_demo compatibility
        self.DEVICE_INDICES = {
            'phone': 0,
            'watch': 1,
            'headphone': 2,
            'glasses': 2  # When use_ar_as_headphone=True
        }
        
        # Network settings
        self.HOST = '0.0.0.0'
        self.PORTS = [8001, 8002, 8003, 8004, 8005]
        self.OUTPUT_PORT = 7777
        
        # Buffer settings
        self.BUFFER_SIZE = 300


class SimpleDataBuffer:
    """Simple thread-safe data buffer"""
    
    def __init__(self, config):
        self.config = config
        self.device_data = {}
        self.device_states = {}
        self.lock = threading.Lock()
        
        # Initialize device buffers
        for device_name in self.config.DEVICE_INDICES.keys():
            device_id = self.config.DEVICE_INDICES[device_name]
            self.device_data[device_id] = {
                'device_name': device_name,
                'accelerometer': deque(maxlen=self.config.BUFFER_SIZE),
                'gyroscope': deque(maxlen=self.config.BUFFER_SIZE),
                'quaternion': np.array([0, 0, 0, 1]),
                'last_update': 0,
                'sample_count': 0,
                'frequency': 0,
                'is_active': False
            }
            self.device_states[device_id] = {
                'connected': False,
                'last_seen': 0
            }
    
    def update_device_data(self, device_id: int, sensor_data: dict):
        """Update device data with new sensor readings"""
        with self.lock:
            current_time = time.time()
            
            if device_id not in self.device_data:
                logger.warning(f"Unknown device ID: {device_id}")
                return
            
            data = self.device_data[device_id]
            state = self.device_states[device_id]
            
            # Update sensor data
            data['accelerometer'].append(sensor_data['accelerometer'])
            data['gyroscope'].append(sensor_data['gyroscope'])
            data['quaternion'] = sensor_data['quaternion']
            data['last_update'] = current_time
            data['sample_count'] += 1
            data['is_active'] = True
            
            # Update connection state
            state['connected'] = True
            state['last_seen'] = current_time
            
            # Simple frequency calculation
            if data['sample_count'] % 30 == 0:
                data['frequency'] = 30.0  # Approximate
    
    def get_device_data_copy(self, device_id: int):
        """Get thread-safe copy of device data"""
        with self.lock:
            if device_id in self.device_data:
                data = self.device_data[device_id].copy()
                data['accelerometer'] = list(data['accelerometer'])
                data['gyroscope'] = list(data['gyroscope'])
                return data
        return None
    
    def get_all_active_devices(self):
        """Get list of currently active device IDs"""
        with self.lock:
            current_time = time.time()
            active_devices = []
            
            for device_id, state in self.device_states.items():
                if state['connected'] and (current_time - state['last_seen']) < 3.0:
                    active_devices.append(device_id)
                else:
                    state['connected'] = False
                    if device_id in self.device_data:
                        self.device_data[device_id]['is_active'] = False
            
            return active_devices


class SimpleIMUReceiver:
    """Simple IMU receiver without complex threading"""
    
    def __init__(self, use_ar_as_headphone=True, enable_ui=True):
        self.config = SimpleDeviceConfig()
        self.use_ar_as_headphone = use_ar_as_headphone
        self.enable_ui = enable_ui
        
        # Core components
        self.data_buffer = SimpleDataBuffer(self.config)
        self.sensor_processor = SensorDataProcessor(use_ar_as_headphone)
        self.socket_receiver = None
        self.ui_window = None
        
        # Control flags
        self.running = False
        
        logger.info(f"Simple IMU Receiver initialized")
        logger.info(f"Use AR as headphone: {use_ar_as_headphone}")
        logger.info(f"UI enabled: {enable_ui}")
    
    def start(self):
        """Start the IMU receiver system"""
        try:
            # Initialize socket receiver
            self.socket_receiver = IMUSocketReceiver(
                host=self.config.HOST,
                ports=self.config.PORTS,
                data_callback=self._handle_sensor_data
            )
            
            if not self.socket_receiver.start():
                logger.error("Failed to start socket receiver")
                return False
            
            # Initialize UI if enabled
            if self.enable_ui:
                self.ui_window = SensorUIWindow(
                    width=1400,
                    height=800,
                    data_buffer=self.data_buffer,
                    config=self.config
                )
                
                # Run UI in main thread (more responsive)
                logger.info("Starting UI (press ESC to exit)")
                self.ui_window.run()
            else:
                # Headless mode - just keep running
                self.running = True
                logger.info("Running in headless mode (press Ctrl+C to exit)")
                while self.running:
                    time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error running IMU Receiver: {e}")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the IMU receiver system"""
        logger.info("Stopping IMU Receiver...")
        
        self.running = False
        
        if self.socket_receiver:
            self.socket_receiver.stop()
        
        if self.ui_window:
            self.ui_window.stop()
        
        logger.info("IMU Receiver stopped")
    
    def _handle_sensor_data(self, device_type: str, parsed_data: dict):
        """Handle incoming sensor data from socket receiver"""
        try:
            # Process the data
            processed_data = self.sensor_processor.process_device_data(device_type, parsed_data)
            
            if processed_data:
                device_id = processed_data['device_id']
                
                # Update data buffer
                self.data_buffer.update_device_data(device_id, processed_data)
                
                # Log occasionally
                if self.data_buffer.device_data[device_id]['sample_count'] % 100 == 0:
                    logger.debug(f"Device {device_type} (ID {device_id}): "
                               f"{self.data_buffer.device_data[device_id]['sample_count']} samples")
        
        except Exception as e:
            logger.error(f"Error handling sensor data: {e}")


def main():
    """Simple main entry point"""
    parser = ArgumentParser(description="Simple IMU Receiver - iOS + AR Glasses")
    parser.add_argument("--no-ui", action='store_true', help="Run without UI")
    parser.add_argument("--ar-as-headphone", action='store_true', default=True,
                       help="Use AR glasses as headphone input")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help="Set logging level")
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and start simple receiver
    receiver = SimpleIMUReceiver(
        use_ar_as_headphone=args.ar_as_headphone,
        enable_ui=not args.no_ui
    )
    
    try:
        receiver.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        receiver.stop()


if __name__ == "__main__":
    main()