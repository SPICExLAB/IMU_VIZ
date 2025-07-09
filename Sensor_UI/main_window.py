"""
Sensor_UI/main_window.py - Simple main UI window
Back to your original working design with device panels and simple waveforms
"""

import pygame
import time
import logging
import threading
from typing import Dict, Any, Optional

from .components.device_panel_3d import DevicePanel3D
from .utils.colors import UIColors
from .utils.fonts import FontManager
from .utils.layout import LayoutManager

logger = logging.getLogger(__name__)


class SensorUIWindow:
    """Simple UI window with device panels and basic waveforms"""
    
    def __init__(self, width: int = 1400, height: int = 800, data_buffer=None, config=None):
        self.width = width
        self.height = height
        self.data_buffer = data_buffer
        self.config = config
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("IMU Receiver - Real-time Sensor Visualization")
        
        # UI managers
        self.font_manager = FontManager()
        self.layout_manager = LayoutManager(width, height)
        
        # Control flags
        self.running = False
        self.clock = pygame.time.Clock()
        self.target_fps = 60
        
        # Device panels (left side)
        self.device_panels = {}
        
        # Simple waveform area (right side)
        self.waveform_area = {
            'x': 600,
            'y': 20,
            'width': width - 620,
            'height': height - 40
        }
        
        # Performance tracking
        self.frame_count = 0
        self.last_fps_update = time.time()
        self.current_fps = 0
        
        self._initialize_device_panels()
        logger.info(f"Simple UI Window initialized ({width}x{height})")
    
    def _initialize_device_panels(self):
        """Initialize device panels in simple 2x2 grid"""
        panel_size = 250
        margin = 20
        
        # Simple 2x2 layout for device panels
        positions = {
            'phone': {'x': margin, 'y': 50, 'width': panel_size, 'height': panel_size},
            'watch': {'x': margin + panel_size + 20, 'y': 50, 'width': panel_size, 'height': panel_size},
            'headphone': {'x': margin, 'y': 50 + panel_size + 20, 'width': panel_size, 'height': panel_size},
            'glasses': {'x': margin + panel_size + 20, 'y': 50 + panel_size + 20, 'width': panel_size, 'height': panel_size}
        }
        
        for device_name, pos in positions.items():
            self.device_panels[device_name] = DevicePanel3D(
                screen=self.screen,
                device_name=device_name,
                x=pos['x'],
                y=pos['y'],
                width=pos['width'],
                height=pos['height'],
                font_manager=self.font_manager
            )
    
    def run(self):
        """Simple main UI loop"""
        self.running = True
        logger.info("Starting simple UI main loop")
        
        try:
            while self.running:
                frame_start = time.time()
                
                # Handle events
                if not self._handle_events():
                    break
                
                # Update and render
                self._update()
                self._render()
                
                # Update display
                pygame.display.flip()
                
                # Control frame rate
                self.clock.tick(self.target_fps)
                
                # Update performance metrics
                self._update_performance_metrics()
                
        except Exception as e:
            logger.error(f"UI main loop error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the UI window"""
        logger.info("Stopping simple UI window")
        self.running = False
        
        # Clean up device panels
        for panel in self.device_panels.values():
            if hasattr(panel, 'cleanup'):
                panel.cleanup()
        
        pygame.quit()
        logger.info("Simple UI window stopped")
    
    def _handle_events(self) -> bool:
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Handle device panel mouse interactions
                for panel in self.device_panels.values():
                    if hasattr(panel, 'handle_mouse_event'):
                        panel.handle_mouse_event(event)
            elif event.type == pygame.MOUSEMOTION:
                # Handle mouse motion for device panels
                for panel in self.device_panels.values():
                    if hasattr(panel, 'handle_mouse_event'):
                        panel.handle_mouse_event(event)
            elif event.type == pygame.MOUSEWHEEL:
                # Handle mouse wheel for device panels
                fake_event = type('Event', (), {
                    'type': pygame.MOUSEWHEEL,
                    'y': event.y,
                    'pos': pygame.mouse.get_pos()
                })()
                for panel in self.device_panels.values():
                    if hasattr(panel, 'handle_mouse_event'):
                        panel.handle_mouse_event(fake_event)
        
        return True
    
    def _update(self):
        """Update components with latest data"""
        if not self.data_buffer:
            return
        
        try:
            # Get active devices
            active_devices = self.data_buffer.get_all_active_devices()
            
            # Update device panels
            for device_name, panel in self.device_panels.items():
                device_data = None
                is_active = False
                
                # Find matching device data
                for device_id in active_devices:
                    data = self.data_buffer.get_device_data_copy(device_id)
                    if data and data['device_name'] == device_name:
                        device_data = data
                        is_active = True
                        break
                
                # Update panel
                panel.update(
                    device_data=device_data,
                    is_active=is_active,
                    is_selected=False,  # No selection in simple mode
                    is_calibrated=False,  # No calibration in simple mode
                    gravity_enabled=True
                )
                
        except Exception as e:
            logger.error(f"Error updating components: {e}")
    
    def _render(self):
        """Render all UI components"""
        # Clear screen
        self.screen.fill(UIColors.BACKGROUND)
        
        # Draw title
        title_text = self.font_manager.render_text("IMU Receiver - Real-time Sensor Visualization", 
                                                  'large', UIColors.TEXT_PRIMARY)
        title_rect = title_text.get_rect(centerx=self.width // 2, y=10)
        self.screen.blit(title_text, title_rect)
        
        # Draw device panels
        for panel in self.device_panels.values():
            panel.render()
        
        # Draw simple waveform area
        self._draw_simple_waveforms()
        
        # Draw status info
        self._draw_simple_status()
    
    def _draw_simple_waveforms(self):
        """Draw simple waveform area like your original design"""
        area = self.waveform_area
        
        # Background
        pygame.draw.rect(self.screen, UIColors.PANEL_BACKGROUND, 
                        (area['x'], area['y'], area['width'], area['height']))
        pygame.draw.rect(self.screen, UIColors.BORDER, 
                        (area['x'], area['y'], area['width'], area['height']), 2)
        
        # Title
        title = self.font_manager.render_text("Sensor Waveforms", 'large', UIColors.TEXT_PRIMARY)
        title_rect = title.get_rect(x=area['x'] + 20, y=area['y'] + 10)
        self.screen.blit(title, title_rect)
        
        if not self.data_buffer:
            # No data message
            msg = self.font_manager.render_text("No sensor data available", 'medium', UIColors.TEXT_SECONDARY)
            msg_rect = msg.get_rect(center=(area['x'] + area['width']//2, area['y'] + area['height']//2))
            self.screen.blit(msg, msg_rect)
            return
        
        # Get active devices
        active_devices = self.data_buffer.get_all_active_devices()
        if not active_devices:
            msg = self.font_manager.render_text("Connect devices to see waveforms", 'medium', UIColors.TEXT_SECONDARY)
            msg_rect = msg.get_rect(center=(area['x'] + area['width']//2, area['y'] + area['height']//2))
            self.screen.blit(msg, msg_rect)
            return
        
        # Simple waveform display
        current_y = area['y'] + 50
        device_height = (area['height'] - 60) // len(active_devices)
        
        for i, device_id in enumerate(active_devices):
            device_data = self.data_buffer.get_device_data_copy(device_id)
            if device_data:
                self._draw_device_waveform(device_data, area['x'] + 10, current_y, 
                                         area['width'] - 20, device_height - 10)
                current_y += device_height
    
    def _draw_device_waveform(self, device_data, x, y, width, height):
        """Draw simple waveform for one device"""
        # Device header
        device_name = device_data['device_name']
        display_names = {'phone': 'iPhone', 'watch': 'Apple Watch', 'headphone': 'AirPods', 'glasses': 'AR Glasses'}
        display_name = display_names.get(device_name, device_name.title())
        
        # Header background
        header_height = 25
        device_color = UIColors.get_device_color(device_name)
        pygame.draw.rect(self.screen, device_color, (x, y, width, header_height))
        
        # Header text
        freq = device_data.get('frequency', 0)
        header_text = f"{display_name} @ {freq:.1f}Hz"
        header_surface = self.font_manager.render_text(header_text, 'small', UIColors.TEXT_PRIMARY)
        self.screen.blit(header_surface, (x + 10, y + 5))
        
        # Waveform area
        wave_y = y + header_height
        wave_height = height - header_height
        
        # Background
        pygame.draw.rect(self.screen, UIColors.WAVEFORM_BACKGROUND, 
                        (x, wave_y, width, wave_height))
        
        # Simple accelerometer data display
        accel_history = device_data.get('accelerometer', [])
        if len(accel_history) > 0:
            self._draw_simple_accel_lines(x, wave_y, width, wave_height, accel_history)
    
    def _draw_simple_accel_lines(self, x, y, width, height, accel_history):
        """Draw simple accelerometer lines"""
        if len(accel_history) < 50:
            return
        
        # Take last 50 samples
        recent_data = list(accel_history)[-50:]
        
        # Draw zero line
        zero_y = y + height // 2
        pygame.draw.line(self.screen, UIColors.WAVEFORM_ZERO_LINE, 
                        (x, zero_y), (x + width, zero_y), 1)
        
        # Draw X, Y, Z lines
        colors = [UIColors.AXIS_X, UIColors.AXIS_Y, UIColors.AXIS_Z]
        
        for axis_idx in range(3):
            points = []
            for i, sample in enumerate(recent_data):
                if hasattr(sample, '__len__') and len(sample) > axis_idx:
                    plot_x = x + int((i / len(recent_data)) * width)
                    # Simple scaling
                    value = float(sample[axis_idx])
                    scaled_value = max(-10, min(10, value))  # Clamp to ±10
                    plot_y = zero_y - int((scaled_value / 10.0) * (height // 2))
                    points.append((plot_x, plot_y))
            
            if len(points) > 1:
                try:
                    pygame.draw.lines(self.screen, colors[axis_idx], False, points, 2)
                except:
                    pass  # Skip if points are invalid
    
    def _draw_simple_status(self):
        """Draw simple status information"""
        if not self.data_buffer:
            return
        
        # FPS in top right
        fps_text = f"FPS: {self.current_fps:.1f}"
        fps_surface = self.font_manager.render_text(fps_text, 'small', UIColors.TEXT_SECONDARY)
        self.screen.blit(fps_surface, (self.width - 100, 10))
        
        # Active device count
        active_devices = self.data_buffer.get_all_active_devices()
        device_count_text = f"Active Devices: {len(active_devices)}"
        device_surface = self.font_manager.render_text(device_count_text, 'small', UIColors.TEXT_SECONDARY)
        self.screen.blit(device_surface, (20, self.height - 30))
        
        # Connection help if no devices
        if len(active_devices) == 0:
            help_text = "Start iOS SensorTracker app or Unity AR glasses app to see device data"
            help_surface = self.font_manager.render_text(help_text, 'small', UIColors.TEXT_SECONDARY)
            help_rect = help_surface.get_rect(centerx=self.width//2, y=self.height - 50)
            self.screen.blit(help_surface, help_rect)
    
    def _update_performance_metrics(self):
        """Update performance metrics"""
        self.frame_count += 1
        
        # Update FPS every second
        current_time = time.time()
        if current_time - self.last_fps_update >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.last_fps_update)
            self.frame_count = 0
            self.last_fps_update = current_time