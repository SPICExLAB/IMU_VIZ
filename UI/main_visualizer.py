"""Main IMU Visualizer - Enhanced with AR Glasses Support"""

import pygame
import numpy as np
import time
from collections import deque

from .utils.colors import Colors
from .utils.fonts import FontManager
from .components.device_panel import DevicePanel
from .components.waveform_panel import WaveformPanel
from .components.reference_panel import ReferencePanel
from .components.calibration_button import CalibrationButton
from .layouts.device_grid import DeviceGridLayout

class IMUVisualizer:
    """Enhanced IMU visualizer with AR Glasses support"""
    
    def __init__(self, width=1400, height=800):
        pygame.init()
        
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("IMU Receiver - iOS Devices + AR Glasses Visualization")
        
        # Initialize managers
        self.font_manager = FontManager()
        
        # Layout dimensions
        self.left_panel_width = 500
        self.right_panel_width = width - self.left_panel_width - 30
        
        # Device data storage
        self.device_data = {}
        
        # Initialize components
        self._init_components()
        
        # Device order - now includes AR glasses
        self.device_order = ['phone', 'headphone', 'watch', 'glasses']
        
        # Waveform settings
        self.waveform_history = 300
        
        print("Enhanced IMU Visualizer initialized with AR Glasses support")
    
    def _init_components(self):
        """Initialize UI components"""
        # Reference panel (top of left panel)
        self.reference_panel = ReferencePanel(
            self.screen, 
            x=10, 
            y=20, 
            width=self.left_panel_width, 
            height=150
        )
        
        # Device grid layout manager (updated for AR glasses)
        self.device_layout = DeviceGridLayout(box_size=180, margin=20)
        
        # Calibration button (bottom of left panel)
        button_width = 180
        button_x = (self.left_panel_width - button_width) // 2 + 10
        button_y = self.height - 80
        self.calibration_button = CalibrationButton(
            self.screen, 
            button_x, 
            button_y
        )
        
        # Waveform panel (right side)
        self.waveform_panel = WaveformPanel(
            self.screen,
            x=self.left_panel_width + 20,
            y=10,
            width=self.right_panel_width,
            height=self.height - 20
        )
        
        # Device panels will be created dynamically
        self.device_panels = {}
    
    def update_device_data(self, imu_data, is_calibrated: bool):
        """Update device data for visualization"""
        device_id = imu_data.device_id
        
        if device_id not in self.device_data:
            self.device_data[device_id] = {
                'accel_history': deque(maxlen=self.waveform_history),
                'gyro_history': deque(maxlen=self.waveform_history),
                'quaternion': np.array([0, 0, 0, 1]),
                'euler': None,
                'last_update': 0,
                'sample_count': 0,
                'is_calibrated': False,
                'frequency': 0,
                'frequency_counter': 0,
                'frequency_timer': time.time()
            }
        
        data = self.device_data[device_id]
        
        # Update data
        data['accel_history'].append(imu_data.accelerometer)
        data['gyro_history'].append(imu_data.gyroscope)
        data['quaternion'] = imu_data.quaternion
        data['euler'] = imu_data.euler  # Store Euler angles for glasses
        data['last_update'] = time.time()
        data['sample_count'] += 1
        data['is_calibrated'] = is_calibrated
        
        # Calculate frequency
        data['frequency_counter'] += 1
        if data['frequency_counter'] % 30 == 0:
            current_time = time.time()
            time_diff = current_time - data['frequency_timer']
            if time_diff > 0:
                data['frequency'] = 30.0 / time_diff
                data['frequency_timer'] = current_time
    
    def get_active_devices(self):
        """Get list of currently active devices"""
        active = []
        current_time = time.time()
        for device_id, data in self.device_data.items():
            if current_time - data['last_update'] < 2.0:
                active.append(device_id)
        return active
    
    def _update_device_panels(self):
        """Update device panels based on active devices"""
        active_devices = self.get_active_devices()
        positions = self.device_layout.calculate_positions(active_devices)
        
        # Create or update device panels
        for device_name in self.device_order:
            if device_name in positions:
                if device_name not in self.device_panels:
                    self.device_panels[device_name] = DevicePanel(
                        self.screen, 
                        device_name, 
                        positions[device_name]
                    )
                else:
                    # Update position info
                    self.device_panels[device_name].position_info = positions[device_name]
                    self.device_panels[device_name].center = positions[device_name]['center']
                    self.device_panels[device_name].size = positions[device_name]['size']
                    self.device_panels[device_name].is_active = positions[device_name]['active']
    
    def handle_events(self):
        """Handle pygame events and return action"""
        mouse_pos = pygame.mouse.get_pos()
        self.calibration_button.update(mouse_pos)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check calibration button
                if self.calibration_button.is_clicked(event):
                    return "calibrate"
                
                # Check waveform panel clicks
                waveform_action = self.waveform_panel.handle_click(event.pos)
                if waveform_action:
                    action_type, device_name = waveform_action
                    # print(f"Waveform action: {action_type} for {device_name}")
        
        return None
    
    def render(self):
        """Main render function"""
        # Clear screen
        self.screen.fill(Colors.BG)
        
        # Draw left panel background
        pygame.draw.rect(self.screen, Colors.PANEL, 
                        (10, 10, self.left_panel_width, self.height - 20))
        
        # Draw components
        self.reference_panel.draw()
        
        # Update and draw device panels
        self._update_device_panels()
        for device_name in self.device_order:
            if device_name in self.device_panels:
                device_data = self.device_data.get(device_name)
                is_calibrated = device_data['is_calibrated'] if device_data else False
                self.device_panels[device_name].draw(device_data, is_calibrated)
        
        # Draw calibration button
        self.calibration_button.draw()
        
        # Draw waveform panel
        self.waveform_panel.draw(self.device_data)
        
        # Draw connection status for AR glasses
        self._draw_connection_status()
        
        # Update display
        pygame.display.flip()
    
    def _draw_connection_status(self):
        """Draw connection status information"""
        # Show active device count and types
        active_devices = self.get_active_devices()
        
        status_text = f"Active Devices: {len(active_devices)}"
        if active_devices:
            device_names = []
            for device in active_devices:
                if device == 'glasses':
                    device_names.append("AR Glasses")
                elif device == 'phone':
                    device_names.append("Phone")
                elif device == 'watch':
                    device_names.append("Watch")
                elif device == 'headphone':
                    device_names.append("AirPods")
                else:
                    device_names.append(device.title())
            
            status_text += f" ({', '.join(device_names)})"
        
        status_surface = self.font_manager.render_text(status_text, 'small', Colors.TEXT_SECONDARY)
        self.screen.blit(status_surface, (20, self.height - 25))
        
        # Show listening port
        port_text = "Listening on UDP port 8001"
        port_surface = self.font_manager.render_text(port_text, 'tiny', Colors.TEXT_TERTIARY)
        self.screen.blit(port_surface, (20, self.height - 45))
    
    def cleanup(self):
        """Clean up resources"""
        pygame.quit()
        print("Enhanced IMU visualizer with AR Glasses support cleaned up")