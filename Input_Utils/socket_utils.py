"""
Input_utils/socket_utils.py - Refactored UDP socket communication
Clean UDP handling with data forwarding to live_demo
"""

import socket
import threading
import time
import queue
import logging
import traceback
import select
from typing import Optional, Callable, List, Dict, Any, Tuple
import numpy as np

from .sensor_utils import parse_ios_message, parse_ar_glasses_message

logger = logging.getLogger(__name__)


class IMUSocketReceiver:
    """
    Enhanced UDP socket receiver for IMU data from iOS devices and AR glasses
    Handles data classification, parsing, and forwarding
    """
    
    def __init__(self, host: str = '0.0.0.0', ports: List[int] = None, 
                 data_callback: Optional[Callable] = None, timeout: float = 0.1):
        """
        Initialize the socket receiver
        
        Args:
            host: Host address to bind to
            ports: List of UDP ports to listen on
            data_callback: Callback function for processed data
            timeout: Socket timeout for non-blocking operations
        """
        self.host = host
        self.ports = ports or [8001, 8002, 8003, 8004, 8005]
        self.timeout = timeout
        self.data_callback = data_callback
        
        # Socket management
        self.sockets = []
        self.running = False
        self.receive_thread = None
        
        # Data processing
        self.data_queue = queue.Queue()
        self.packet_stats = {
            'ios': 0,
            'ar_glasses': 0,
            'unknown': 0,
            'errors': 0
        }
        
        # Device management
        self.device_ip_mapping = {}
        self.last_stats_time = time.time()
        self.stats_interval = 10.0
        
        # Live demo forwarding
        self.live_demo_socket = None
        self.live_demo_host = '127.0.0.1'
        self.live_demo_port = 7777
        
        logger.info(f"IMUSocketReceiver initialized for ports {self.ports}")
    
    def start(self) -> bool:
        """Start the socket receiver"""
        try:
            # Initialize UDP sockets
            if not self._initialize_sockets():
                return False
            
            # Initialize live demo forwarding socket
            self._initialize_live_demo_socket()
            
            # Start receiver thread
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            logger.info("IMU Socket Receiver started successfully")
            logger.info("Listening for:")
            logger.info("  - iOS devices (phone/watch/headphone)")
            logger.info("  - AR Glasses (Unity app)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start socket receiver: {e}")
            return False
    
    def stop(self):
        """Stop the socket receiver"""
        logger.info("Stopping socket receiver...")
        
        self.running = False
        
        # Wait for receive thread to finish
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        
        # Close all sockets
        for sock in self.sockets:
            try:
                sock.close()
            except:
                pass
        self.sockets.clear()
        
        # Close live demo socket
        if self.live_demo_socket:
            try:
                self.live_demo_socket.close()
            except:
                pass
        
        logger.info("Socket receiver stopped")
    
    def _initialize_sockets(self) -> bool:
        """Initialize UDP listening sockets"""
        success_count = 0
        
        for port in self.ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # Try to bind to the port
                sock.bind((self.host, port))
                sock.settimeout(self.timeout)
                
                self.sockets.append(sock)
                success_count += 1
                logger.info(f"Successfully bound to port {port}")
                
            except socket.error as e:
                logger.warning(f"Could not bind to port {port}: {e}")
                # Try alternative port
                alt_port = port + 1000
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind((self.host, alt_port))
                    sock.settimeout(self.timeout)
                    
                    self.sockets.append(sock)
                    success_count += 1
                    logger.info(f"Successfully bound to alternative port {alt_port}")
                    
                except socket.error as e2:
                    logger.error(f"Failed to bind to alternative port {alt_port}: {e2}")
        
        if success_count == 0:
            logger.error("Could not bind to any ports")
            return False
        
        logger.info(f"Successfully initialized {success_count} UDP sockets")
        return True
    
    def _initialize_live_demo_socket(self):
        """Initialize socket for forwarding data to live_demo"""
        try:
            self.live_demo_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"Live demo forwarding socket created for {self.live_demo_host}:{self.live_demo_port}")
        except Exception as e:
            logger.warning(f"Failed to create live demo socket: {e}")
    
    def _receive_loop(self):
        """Main receive loop"""
        logger.info("Started UDP receive loop")
        
        while self.running and self.sockets:
            try:
                # Use select to wait for data on any socket
                readable, _, _ = select.select(self.sockets, [], [], self.timeout)
                
                for sock in readable:
                    try:
                        data, addr = sock.recvfrom(4096)
                        self._process_incoming_data(data, addr)
                        
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            logger.error(f"Error receiving data: {e}")
                            self.packet_stats['errors'] += 1
                
                # Print statistics periodically
                self._update_statistics()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Receive loop error: {e}")
                    logger.debug(traceback.format_exc())
    
    def _process_incoming_data(self, data: bytes, addr: Tuple[str, int]):
        """Process incoming UDP data"""
        try:
            # Try to decode as UTF-8
            try:
                decoded_data = data.decode('utf-8', errors='ignore').strip()
            except UnicodeDecodeError:
                logger.warning(f"Failed to decode data from {addr[0]}")
                self.packet_stats['unknown'] += 1
                return
            
            # Classify and parse the data
            device_type, parsed_data = self._classify_and_parse_data(decoded_data, addr)
            
            if device_type and parsed_data:
                # Update statistics
                self.packet_stats[device_type] += 1
                
                # Send to callback if provided
                if self.data_callback:
                    self.data_callback(device_type, parsed_data)
                
                # Log successful processing
                if self.packet_stats[device_type] % 100 == 0:
                    logger.debug(f"Processed {self.packet_stats[device_type]} {device_type} packets")
            else:
                self.packet_stats['unknown'] += 1
                
        except Exception as e:
            logger.error(f"Error processing data from {addr[0]}: {e}")
            self.packet_stats['errors'] += 1
    
    def _classify_and_parse_data(self, data_str: str, addr: Tuple[str, int]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Classify data source and parse accordingly
        
        Returns:
            Tuple of (device_type, parsed_data) or (None, None) if parsing fails
        """
        try:
            # Try iOS format first (has semicolon and colon)
            if ';' in data_str and ':' in data_str:
                parsed_data = parse_ios_message(data_str)
                if parsed_data:
                    logger.debug(f"Parsed iOS data from {addr[0]}: device={parsed_data['device_name']}")
                    return 'ios', parsed_data
            
            # Try AR glasses format (space-separated numeric values)
            parts = data_str.split()
            if len(parts) >= 9:  # Minimum for AR glasses data
                # Check if all parts are numeric (AR glasses format)
                try:
                    [float(p) for p in parts[:9]]  # Try converting first 9 values
                    parsed_data = parse_ar_glasses_message(data_str)
                    if parsed_data:
                        logger.debug(f"Parsed AR glasses data from {addr[0]}")
                        return 'ar_glasses', parsed_data
                except ValueError:
                    pass
            
            # Try Unity-style AR glasses format
            if 'unity' in data_str.lower() or len(parts) >= 9:
                parsed_data = parse_ar_glasses_message(data_str)
                if parsed_data:
                    logger.debug(f"Parsed Unity AR glasses data from {addr[0]}")
                    return 'ar_glasses', parsed_data
            
            # Log unknown format for debugging
            logger.debug(f"Unknown data format from {addr[0]}: '{data_str[:50]}...'")
            return None, None
            
        except Exception as e:
            logger.error(f"Error classifying data from {addr[0]}: {e}")
            return None, None
    
    def _update_statistics(self):
        """Update and log packet statistics"""
        current_time = time.time()
        if current_time - self.last_stats_time >= self.stats_interval:
            total_packets = sum(self.packet_stats.values())
            
            if total_packets > 0:
                logger.info("=== Packet Statistics ===")
                for packet_type, count in self.packet_stats.items():
                    percentage = (count / total_packets) * 100
                    logger.info(f"{packet_type.upper()}: {count} packets ({percentage:.1f}%)")
                logger.info(f"Total: {total_packets} packets")
                logger.info("========================")
            
            self.last_stats_time = current_time
    
    def send_to_live_demo(self, virtual_acc: Dict[int, np.ndarray], virtual_ori: Dict[int, np.ndarray]):
        """
        Send processed data to live_demo in expected format
        
        Args:
            virtual_acc: Dictionary of device_id -> acceleration arrays
            virtual_ori: Dictionary of device_id -> quaternion arrays
        """
        if not self.live_demo_socket:
            return
        
        try:
            # Format data as expected by live_demo
            acc_list = []
            ori_list = []
            
            # live_demo expects exactly 5 devices (indices 0-4)
            for device_id in range(5):
                if device_id in virtual_acc and device_id in virtual_ori:
                    acc_list.append(virtual_acc[device_id])
                    # Reorder quaternion from [x,y,z,w] to [w,x,y,z] for live_demo
                    quat = virtual_ori[device_id]
                    ori_list.append(quat[[3, 0, 1, 2]])
                else:
                    # Default values for inactive devices
                    acc_list.append(np.zeros((1, 3)))
                    ori_list.append(np.array([1, 0, 0, 0]))  # Identity quaternion [w,x,y,z]
            
            # Convert to numpy arrays
            acc_array = np.array(acc_list)
            ori_array = np.array(ori_list)
            
            # Create the message string format expected by live_demo
            acc_str = ','.join(['%g' % v for v in acc_array.flatten()])
            ori_str = ','.join(['%g' % v for v in ori_array.flatten()])
            message = f"{acc_str}#{ori_str}$"
            
            # Send to live_demo
            self.live_demo_socket.sendto(message.encode('utf-8'), 
                                       (self.live_demo_host, self.live_demo_port))
            
        except Exception as e:
            logger.error(f"Error sending to live_demo: {e}")
    
    def get_device_ip_mapping(self) -> Dict[str, str]:
        """Get current device IP address mappings"""
        return self.device_ip_mapping.copy()
    
    def get_packet_statistics(self) -> Dict[str, int]:
        """Get current packet statistics"""
        return self.packet_stats.copy()


class LiveDemoForwarder:
    """Handles forwarding processed data to live_demo application"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 7777):
        self.host = host
        self.port = port
        self.socket = None
        self._initialize_socket()
    
    def _initialize_socket(self):
        """Initialize UDP socket for forwarding"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"Live demo forwarder initialized for {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to initialize live demo forwarder: {e}")
    
    def send_data(self, accelerations: np.ndarray, orientations: np.ndarray):
        """
        Send data to live_demo in the expected format
        
        Args:
            accelerations: Array of shape [num_devices, 3] for accelerometer data
            orientations: Array of shape [num_devices, 4] for quaternion data
        """
        if not self.socket:
            return False
        
        try:
            # Format data as comma-separated values
            acc_str = ','.join(['%g' % v for v in accelerations.flatten()])
            ori_str = ','.join(['%g' % v for v in orientations.flatten()])
            
            # Create message in live_demo format: "acc1,acc2,...#ori1,ori2,...$"
            message = f"{acc_str}#{ori_str}$"
            
            # Send UDP packet
            self.socket.sendto(message.encode('utf-8'), (self.host, self.port))
            return True
            
        except Exception as e:
            logger.error(f"Error sending data to live_demo: {e}")
            return False
    
    def close(self):
        """Close the forwarder socket"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None


def find_available_ports(base_ports: List[int], num_needed: int = None) -> List[int]:
    """
    Find available UDP ports for binding
    
    Args:
        base_ports: Preferred ports to try first
        num_needed: Number of ports needed (None = try all base_ports)
        
    Returns:
        List of available port numbers
    """
    available_ports = []
    
    if num_needed is None:
        num_needed = len(base_ports)
    
    # Try base ports first
    for port in base_ports:
        if len(available_ports) >= num_needed:
            break
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', port))
            sock.close()
            available_ports.append(port)
            logger.debug(f"Port {port} is available")
        except socket.error:
            logger.debug(f"Port {port} is not available")
    
    # Try alternative ports if needed
    if len(available_ports) < num_needed:
        for port in range(8050, 8100):
            if len(available_ports) >= num_needed:
                break
                
            if port not in base_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.bind(('0.0.0.0', port))
                    sock.close()
                    available_ports.append(port)
                    logger.debug(f"Alternative port {port} is available")
                except socket.error:
                    pass
    
    return available_ports

