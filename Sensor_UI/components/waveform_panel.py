"""
Sensor_UI/components/waveform_panel.py - Real-time waveform display
Scrolling waveforms for accelerometer and gyroscope data
"""

import pygame
import numpy as np
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import deque

from ..utils.colors import UIColors
from ..utils.fonts import FontManager

logger = logging.getLogger(__name__)


class WaveformPanel:
    """Main waveform panel managing multiple device waveforms"""
    
    def __init__(self, screen, x: int, y: int, width: int, height: int, font_manager: FontManager):
        self.screen = screen
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font_manager = font_manager
        
        # Device waveform displays
        self.device_waveforms = {}
        
        # Panel state
        self.scroll_offset = 0
        self.max_devices_visible = 3
        
        # Zoom settings
        self.zoom_levels = {
            'accel': [(-0.5, 0.5), (-1.0, 1.0), (-2.0, 2.0), (-5.0, 5.0), (-10.0, 10.0)],
            'gyro': [(-0.1, 0.1), (-0.5, 0.5), (-1.0, 1.0), (-2.0, 2.0), (-5.0, 5.0)]
        }
        self.current_zoom_indices = {'accel': 2, 'gyro': 2}  # Default to middle zoom
        
        # UI elements
        self.buttons = {}
        self.show_controls = True
        
        logger.info("WaveformPanel initialized")
    
    def update(self, device_data: Dict[str, Any]):
        """Update waveform panel with new device data"""
        # Update existing device waveforms
        for device_name, data in device_data.items():
            if device_name not in self.device_waveforms:
                self.device_waveforms[device_name] = DeviceWaveform(
                    device_name, self.font_manager
                )
            
            self.device_waveforms[device_name].update(data)
        
        # Remove inactive devices
        active_devices = set(device_data.keys())
        inactive_devices = set(self.device_waveforms.keys()) - active_devices
        
        for device_name in inactive_devices:
            if not self.device_waveforms[device_name].has_recent_data():
                del self.device_waveforms[device_name]
    
    def render(self):
        """Render the waveform panel"""
        # Clear panel background
        pygame.draw.rect(self.screen, UIColors.WAVEFORM_BACKGROUND, 
                        (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, UIColors.BORDER, 
                        (self.x, self.y, self.width, self.height), 2)
        
        # Draw title
        title_text = self.font_manager.render_text("Real-time Sensor Waveforms", 
                                                  'large', UIColors.TEXT_PRIMARY)
        title_rect = title_text.get_rect(centerx=self.x + self.width // 2, y=self.y + 10)
        self.screen.blit(title_text, title_rect)
        
        # Draw controls if enabled
        if self.show_controls:
            self._draw_controls()
        
        # Calculate device layout
        active_devices = list(self.device_waveforms.keys())
        if not active_devices:
            self._draw_no_data_message()
            return
        
        # Calculate individual device areas
        content_y = self.y + 60  # Space for title and controls
        available_height = self.height - 100  # Space for title and bottom margin
        
        visible_devices = active_devices[self.scroll_offset:self.scroll_offset + self.max_devices_visible]
        device_height = available_height // len(visible_devices) if visible_devices else available_height
        
        # Draw device waveforms
        current_y = content_y
        for device_name in visible_devices:
            waveform = self.device_waveforms[device_name]
            
            # Get zoom ranges
            accel_range = self.zoom_levels['accel'][self.current_zoom_indices['accel']]
            gyro_range = self.zoom_levels['gyro'][self.current_zoom_indices['gyro']]
            
            # Render device waveform
            waveform.render(
                self.screen,
                x=self.x + 10,
                y=current_y,
                width=self.width - 20,
                height=device_height - 10,
                accel_range=accel_range,
                gyro_range=gyro_range
            )
            
            current_y += device_height
        
        # Draw scroll indicators if needed
        if len(active_devices) > self.max_devices_visible:
            self._draw_scroll_indicators()
    
    def _draw_controls(self):
        """Draw control buttons for zoom and settings"""
        self.buttons.clear()
        
        control_y = self.y + 35
        button_width = 60
        button_height = 20
        button_spacing = 10
        
        # Zoom controls
        zoom_x = self.x + 10
        
        # Accelerometer zoom
        accel_zoom_text = f"Accel Zoom: {self.current_zoom_indices['accel'] + 1}/{len(self.zoom_levels['accel'])}"
        zoom_label = self.font_manager.render_text(accel_zoom_text, 'small', UIColors.TEXT_SECONDARY)
        self.screen.blit(zoom_label, (zoom_x, control_y))
        
        zoom_out_btn = pygame.Rect(zoom_x + 120, control_y, 20, button_height)
        zoom_in_btn = pygame.Rect(zoom_x + 145, control_y, 20, button_height)
        
        pygame.draw.rect(self.screen, UIColors.BUTTON_NORMAL, zoom_out_btn)
        pygame.draw.rect(self.screen, UIColors.BUTTON_NORMAL, zoom_in_btn)
        pygame.draw.rect(self.screen, UIColors.BORDER, zoom_out_btn, 1)
        pygame.draw.rect(self.screen, UIColors.BORDER, zoom_in_btn, 1)
        
        # Zoom button text
        minus_text = self.font_manager.render_text("-", 'small', UIColors.TEXT_PRIMARY)
        plus_text = self.font_manager.render_text("+", 'small', UIColors.TEXT_PRIMARY)
        
        minus_rect = minus_text.get_rect(center=zoom_out_btn.center)
        plus_rect = plus_text.get_rect(center=zoom_in_btn.center)
        
        self.screen.blit(minus_text, minus_rect)
        self.screen.blit(plus_text, plus_rect)
        
        self.buttons['accel_zoom_out'] = zoom_out_btn
        self.buttons['accel_zoom_in'] = zoom_in_btn
        
        # Gyroscope zoom (to the right)
        gyro_x = zoom_x + 200
        gyro_zoom_text = f"Gyro Zoom: {self.current_zoom_indices['gyro'] + 1}/{len(self.zoom_levels['gyro'])}"
        gyro_label = self.font_manager.render_text(gyro_zoom_text, 'small', UIColors.TEXT_SECONDARY)
        self.screen.blit(gyro_label, (gyro_x, control_y))
        
        gyro_out_btn = pygame.Rect(gyro_x + 110, control_y, 20, button_height)
        gyro_in_btn = pygame.Rect(gyro_x + 135, control_y, 20, button_height)
        
        pygame.draw.rect(self.screen, UIColors.BUTTON_NORMAL, gyro_out_btn)
        pygame.draw.rect(self.screen, UIColors.BUTTON_NORMAL, gyro_in_btn)
        pygame.draw.rect(self.screen, UIColors.BORDER, gyro_out_btn, 1)
        pygame.draw.rect(self.screen, UIColors.BORDER, gyro_in_btn, 1)
        
        minus_rect2 = minus_text.get_rect(center=gyro_out_btn.center)
        plus_rect2 = plus_text.get_rect(center=gyro_in_btn.center)
        
        self.screen.blit(minus_text, minus_rect2)
        self.screen.blit(plus_text, plus_rect2)
        
        self.buttons['gyro_zoom_out'] = gyro_out_btn
        self.buttons['gyro_zoom_in'] = gyro_in_btn
        
        # Current zoom range display
        range_x = self.x + self.width - 200
        accel_range = self.zoom_levels['accel'][self.current_zoom_indices['accel']]
        gyro_range = self.zoom_levels['gyro'][self.current_zoom_indices['gyro']]
        
        range_text = f"Ranges: A±{abs(accel_range[1]):.1f} G±{abs(gyro_range[1]):.1f}"
        range_surface = self.font_manager.render_text(range_text, 'small', UIColors.TEXT_SECONDARY)
        self.screen.blit(range_surface, (range_x, control_y))
    
    def _draw_no_data_message(self):
        """Draw message when no device data is available"""
        msg_text = "No sensor data available"
        msg_surface = self.font_manager.render_text(msg_text, 'medium', UIColors.TEXT_SECONDARY)
        msg_rect = msg_surface.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
        self.screen.blit(msg_surface, msg_rect)
        
        # Instructions
        inst_lines = [
            "Connect devices to see real-time waveforms:",
            "• iOS SensorTracker app for iPhone/Watch/AirPods",
            "• Unity app on AR glasses",
            "",
            "Data will appear automatically when devices connect"
        ]
        
        start_y = msg_rect.bottom + 40
        for i, line in enumerate(inst_lines):
            if line:  # Skip empty lines
                inst_surface = self.font_manager.render_text(line, 'small', UIColors.TEXT_SECONDARY)
                inst_rect = inst_surface.get_rect(centerx=self.x + self.width // 2, y=start_y + i * 25)
                self.screen.blit(inst_surface, inst_rect)
    
    def _draw_scroll_indicators(self):
        """Draw scroll indicators when there are more devices than visible"""
        indicator_x = self.x + self.width - 30
        indicator_y = self.y + 70
        indicator_height = self.height - 120
        
        # Scroll bar background
        pygame.draw.rect(self.screen, UIColors.PANEL_BACKGROUND, 
                        (indicator_x, indicator_y, 20, indicator_height))
        pygame.draw.rect(self.screen, UIColors.BORDER, 
                        (indicator_x, indicator_y, 20, indicator_height), 1)
        
        # Scroll thumb
        total_devices = len(self.device_waveforms)
        thumb_height = max(20, indicator_height * self.max_devices_visible // total_devices)
        thumb_y = indicator_y + (indicator_height - thumb_height) * self.scroll_offset // (total_devices - self.max_devices_visible)
        
        pygame.draw.rect(self.screen, UIColors.ACCENT, 
                        (indicator_x + 2, thumb_y, 16, thumb_height))
    
    def handle_event(self, event):
        """Handle pygame events"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self.handle_click(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            return self.handle_scroll(event.y)
        elif event.type == pygame.KEYDOWN:
            return self.handle_key(event.key)
        return False
    
    def handle_click(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse clicks on waveform panel"""
        # Check if click is within panel
        if not (self.x <= pos[0] <= self.x + self.width and 
                self.y <= pos[1] <= self.y + self.height):
            return False
        
        # Check control buttons
        for button_name, button_rect in self.buttons.items():
            if button_rect.collidepoint(pos):
                return self._handle_button_click(button_name)
        
        return True
    
    def _handle_button_click(self, button_name: str) -> bool:
        """Handle control button clicks"""
        if button_name == 'accel_zoom_out':
            if self.current_zoom_indices['accel'] < len(self.zoom_levels['accel']) - 1:
                self.current_zoom_indices['accel'] += 1
        elif button_name == 'accel_zoom_in':
            if self.current_zoom_indices['accel'] > 0:
                self.current_zoom_indices['accel'] -= 1
        elif button_name == 'gyro_zoom_out':
            if self.current_zoom_indices['gyro'] < len(self.zoom_levels['gyro']) - 1:
                self.current_zoom_indices['gyro'] += 1
        elif button_name == 'gyro_zoom_in':
            if self.current_zoom_indices['gyro'] > 0:
                self.current_zoom_indices['gyro'] -= 1
        
        return True
    
    def handle_scroll(self, scroll_y: int) -> bool:
        """Handle mouse wheel scrolling"""
        total_devices = len(self.device_waveforms)
        
        if total_devices > self.max_devices_visible:
            self.scroll_offset = max(0, min(
                total_devices - self.max_devices_visible,
                self.scroll_offset - scroll_y
            ))
            return True
        
        return False
    
    def handle_key(self, key: int) -> bool:
        """Handle keyboard input"""
        if key == pygame.K_UP:
            return self.handle_scroll(1)
        elif key == pygame.K_DOWN:
            return self.handle_scroll(-1)
        elif key == pygame.K_PLUS or key == pygame.K_EQUALS:
            # Zoom in both
            self._handle_button_click('accel_zoom_in')
            self._handle_button_click('gyro_zoom_in')
            return True
        elif key == pygame.K_MINUS:
            # Zoom out both
            self._handle_button_click('accel_zoom_out')
            self._handle_button_click('gyro_zoom_out')
            return True
        
        return False
    
    def is_point_inside(self, pos: Tuple[int, int]) -> bool:
        """Check if point is inside the waveform panel"""
        return (self.x <= pos[0] <= self.x + self.width and 
                self.y <= pos[1] <= self.y + self.height)


class DeviceWaveform:
    """Waveform display for a single device"""
    
    def __init__(self, device_name: str, font_manager: FontManager):
        self.device_name = device_name
        self.font_manager = font_manager
        
        # Data storage
        self.accel_history = deque(maxlen=300)  # 10 seconds at 30Hz
        self.gyro_history = deque(maxlen=300)
        self.timestamps = deque(maxlen=300)
        
        # Current values
        self.current_accel = np.array([0.0, 0.0, 0.0])
        self.current_gyro = np.array([0.0, 0.0, 0.0])
        self.frequency = 0.0
        self.last_update = 0.0
        
        # Display settings
        self.colors = {
            'x': UIColors.AXIS_X,
            'y': UIColors.AXIS_Y, 
            'z': UIColors.AXIS_Z
        }
        
        # Device display names
        self.display_names = {
            'phone': 'iPhone',
            'watch': 'Apple Watch',
            'headphone': 'AirPods',
            'glasses': 'AR Glasses'
        }
    
    def update(self, device_data: Dict[str, Any]):
        """Update waveform with new device data"""
        current_time = time.time()
        
        # Extract data
        if 'accelerometer_history' in device_data:
            # Bulk update from history
            accel_list = list(device_data['accelerometer_history'])
            gyro_list = list(device_data.get('gyroscope_history', []))
            
            # Add new data points
            for i, accel in enumerate(accel_list[-10:]):  # Only add recent points
                self.accel_history.append(np.array(accel))
                self.timestamps.append(current_time - (len(accel_list) - i) * 0.033)  # ~30Hz
                
                if i < len(gyro_list):
                    self.gyro_history.append(np.array(gyro_list[i]))
                else:
                    self.gyro_history.append(np.array([0.0, 0.0, 0.0]))
        
        # Update current values
        if 'current_accel' in device_data:
            self.current_accel = np.array(device_data['current_accel'])
        if 'current_gyro' in device_data:
            self.current_gyro = np.array(device_data['current_gyro'])
        
        self.frequency = device_data.get('frequency', 0.0)
        self.last_update = current_time
    
    def render(self, screen, x: int, y: int, width: int, height: int,
              accel_range: Tuple[float, float], gyro_range: Tuple[float, float]):
        """Render device waveform"""
        # Draw device header
        header_height = 30
        self._draw_header(screen, x, y, width, header_height)
        
        # Calculate waveform areas
        waveform_y = y + header_height
        waveform_height = height - header_height
        
        # Check if we have gyroscope data
        has_gyro = len(self.gyro_history) > 0 and any(np.linalg.norm(g) > 0.001 for g in list(self.gyro_history)[-10:])
        
        if has_gyro:
            # Split area for accelerometer and gyroscope
            accel_height = waveform_height // 2 - 10
            gyro_height = waveform_height // 2 - 10
            
            # Draw accelerometer waveform
            self._draw_sensor_waveform(
                screen, x, waveform_y, width, accel_height,
                self.accel_history, accel_range, "Accelerometer (m/s²)", 
                self.current_accel
            )
            
            # Draw gyroscope waveform
            gyro_y = waveform_y + accel_height + 20
            self._draw_sensor_waveform(
                screen, x, gyro_y, width, gyro_height,
                self.gyro_history, gyro_range, "Gyroscope (rad/s)", 
                self.current_gyro
            )
        else:
            # Only accelerometer
            self._draw_sensor_waveform(
                screen, x, waveform_y, width, waveform_height - 10,
                self.accel_history, accel_range, "Accelerometer (m/s²) - No gyroscope data", 
                self.current_accel
            )
    
    def _draw_header(self, screen, x: int, y: int, width: int, height: int):
        """Draw device header with status info"""
        # Background
        device_color = UIColors.get_device_color(self.device_name)
        pygame.draw.rect(screen, device_color, (x, y, width, height))
        pygame.draw.rect(screen, UIColors.BORDER, (x, y, width, height), 2)
        
        # Device name and status
        display_name = self.display_names.get(self.device_name, self.device_name.title())
        status_text = f"{display_name} @ {self.frequency:.1f}Hz"
        
        status_surface = self.font_manager.render_text(status_text, 'medium', UIColors.TEXT_PRIMARY)
        status_rect = status_surface.get_rect(x=x + 10, centery=y + height // 2)
        screen.blit(status_surface, status_rect)
        
        # Current magnitude
        if len(self.accel_history) > 0:
            magnitude = np.linalg.norm(self.current_accel)
            mag_text = f"Magnitude: {magnitude:.3f}"
            mag_surface = self.font_manager.render_text(mag_text, 'small', UIColors.TEXT_PRIMARY)
            mag_rect = mag_surface.get_rect(right=x + width - 10, centery=y + height // 2)
            screen.blit(mag_surface, mag_rect)
    
    def _draw_sensor_waveform(self, screen, x: int, y: int, width: int, height: int,
                             data_history: deque, y_range: Tuple[float, float], 
                             title: str, current_values: np.ndarray):
        """Draw waveform for a single sensor type"""
        # Background
        pygame.draw.rect(screen, UIColors.WAVEFORM_BACKGROUND, (x, y, width, height))
        pygame.draw.rect(screen, UIColors.BORDER, (x, y, width, height), 1)
        
        # Title and current values
        title_surface = self.font_manager.render_text(title, 'small', UIColors.TEXT_SECONDARY)
        screen.blit(title_surface, (x + 5, y + 5))
        
        # Current values display
        self._draw_current_values(screen, x + 250, y + 5, current_values)
        
        # Grid
        self._draw_grid(screen, x, y, width, height, y_range)
        
        # Zero line
        zero_y = y + height // 2
        pygame.draw.line(screen, UIColors.WAVEFORM_ZERO_LINE, (x, zero_y), (x + width, zero_y), 2)
        
        # Range labels
        self._draw_range_labels(screen, x, y, height, y_range)
        
        # Waveform data
        if len(data_history) > 1:
            self._draw_waveform_lines(screen, x, y, width, height, data_history, y_range)
    
    def _draw_current_values(self, screen, x: int, y: int, values: np.ndarray):
        """Draw current X, Y, Z values"""
        axis_labels = ['X', 'Y', 'Z']
        
        for i, (label, value, color) in enumerate(zip(axis_labels, values, [self.colors['x'], self.colors['y'], self.colors['z']])):
            value_text = f"{label}: {value:+.3f}"
            value_surface = self.font_manager.render_text(value_text, 'small', color)
            screen.blit(value_surface, (x + i * 80, y))
    
    def _draw_grid(self, screen, x: int, y: int, width: int, height: int, y_range: Tuple[float, float]):
        """Draw grid lines"""
        # Horizontal grid lines
        for i in range(1, 5):
            grid_y = y + (i * height // 5)
            pygame.draw.line(screen, UIColors.WAVEFORM_GRID, (x, grid_y), (x + width, grid_y), 1)
        
        # Vertical grid lines
        for i in range(1, 10):
            grid_x = x + (i * width // 10)
            pygame.draw.line(screen, UIColors.WAVEFORM_GRID, (grid_x, y), (grid_x, y + height), 1)
    
    def _draw_range_labels(self, screen, x: int, y: int, height: int, y_range: Tuple[float, float]):
        """Draw Y-axis range labels"""
        # Top label
        top_text = self.font_manager.render_text(f"+{y_range[1]:.1f}", 'tiny', UIColors.TEXT_SECONDARY)
        screen.blit(top_text, (x + 5, y + 2))
        
        # Zero label
        zero_text = self.font_manager.render_text("0", 'tiny', UIColors.TEXT_SECONDARY)
        screen.blit(zero_text, (x + 5, y + height // 2 - 8))
        
        # Bottom label
        bottom_text = self.font_manager.render_text(f"{y_range[0]:.1f}", 'tiny', UIColors.TEXT_SECONDARY)
        screen.blit(bottom_text, (x + 5, y + height - 15))
    
    def _draw_waveform_lines(self, screen, x: int, y: int, width: int, height: int,
                            data_history: deque, y_range: Tuple[float, float]):
        """Draw the actual waveform lines"""
        data_array = np.array(list(data_history))
        if len(data_array) < 2:
            return
        
        n_samples = len(data_array)
        
        # Draw each axis (X, Y, Z)
        for axis_idx in range(3):
            color = [self.colors['x'], self.colors['y'], self.colors['z']][axis_idx]
            values = data_array[:, axis_idx]
            
            # Create points for line drawing
            points = []
            for i, value in enumerate(values):
                # X position (right to left scrolling)
                plot_x = x + width - int((i / max(1, n_samples - 1)) * width)
                
                # Y position (clamp and normalize)
                clamped_value = np.clip(value, y_range[0], y_range[1])
                normalized = (clamped_value - y_range[0]) / (y_range[1] - y_range[0])
                plot_y = y + height - int(normalized * height)
                
                points.append((plot_x, plot_y))
            
            # Draw waveform line
            if len(points) > 1:
                # Reverse points for right-to-left scrolling
                points.reverse()
                try:
                    pygame.draw.lines(screen, color, False, points, 2)
                except ValueError:
                    # Handle edge case where points are invalid
                    pass
    
    def has_recent_data(self, timeout: float = 5.0) -> bool:
        """Check if device has recent data"""
        return time.time() - self.last_update < timeout


class WaveformExporter:
    """Handles exporting waveform data to files"""
    
    def __init__(self):
        self.export_formats = ['csv', 'json', 'numpy']
    
    def export_device_data(self, device_waveform: DeviceWaveform, 
                          filename: str, format: str = 'csv') -> bool:
        """
        Export device waveform data to file
        
        Args:
            device_waveform: DeviceWaveform instance
            filename: Output filename
            format: Export format ('csv', 'json', 'numpy')
            
        Returns:
            True if export successful
        """
        try:
            if format == 'csv':
                return self._export_csv(device_waveform, filename)
            elif format == 'json':
                return self._export_json(device_waveform, filename)
            elif format == 'numpy':
                return self._export_numpy(device_waveform, filename)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False
    
    def _export_csv(self, device_waveform: DeviceWaveform, filename: str) -> bool:
        """Export to CSV format"""
        import csv
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            header = ['timestamp', 'accel_x', 'accel_y', 'accel_z']
            if len(device_waveform.gyro_history) > 0:
                header.extend(['gyro_x', 'gyro_y', 'gyro_z'])
            writer.writerow(header)
            
            # Data
            timestamps = list(device_waveform.timestamps)
            accel_data = list(device_waveform.accel_history)
            gyro_data = list(device_waveform.gyro_history)
            
            for i in range(len(accel_data)):
                row = [timestamps[i] if i < len(timestamps) else 0.0]
                row.extend(accel_data[i])
                
                if i < len(gyro_data):
                    row.extend(gyro_data[i])
                
                writer.writerow(row)
        
        return True
    
    def _export_json(self, device_waveform: DeviceWaveform, filename: str) -> bool:
        """Export to JSON format"""
        import json
        
        data = {
            'device_name': device_waveform.device_name,
            'export_time': time.time(),
            'frequency': device_waveform.frequency,
            'timestamps': list(device_waveform.timestamps),
            'accelerometer': [list(a) for a in device_waveform.accel_history],
            'gyroscope': [list(g) for g in device_waveform.gyro_history]
        }
        
        with open(filename, 'w') as jsonfile:
            json.dump(data, jsonfile, indent=2)
        
        return True
    
    def _export_numpy(self, device_waveform: DeviceWaveform, filename: str) -> bool:
        """Export to NumPy format"""
        data = {
            'device_name': device_waveform.device_name,
            'timestamps': np.array(device_waveform.timestamps),
            'accelerometer': np.array(device_waveform.accel_history),
            'gyroscope': np.array(device_waveform.gyro_history),
            'frequency': device_waveform.frequency
        }
        
        np.savez(filename, **data)
        return True


class WaveformAnalyzer:
    """Analyzes waveform data for statistics and patterns"""
    
    def __init__(self):
        pass
    
    def calculate_statistics(self, data: np.ndarray) -> Dict[str, float]:
        """Calculate basic statistics for waveform data"""
        if len(data) == 0:
            return {'min': 0, 'max': 0, 'mean': 0, 'std': 0, 'rms': 0}
        
        return {
            'min': np.min(data),
            'max': np.max(data),
            'mean': np.mean(data),
            'std': np.std(data),
            'rms': np.sqrt(np.mean(data**2))
        }
    
    def detect_peaks(self, data: np.ndarray, threshold: float = None) -> List[int]:
        """Detect peaks in waveform data"""
        if len(data) < 3:
            return []
        
        if threshold is None:
            threshold = np.std(data) * 2
        
        peaks = []
        for i in range(1, len(data) - 1):
            if (data[i] > data[i-1] and data[i] > data[i+1] and 
                abs(data[i]) > threshold):
                peaks.append(i)
        
        return peaks
    
    def calculate_frequency_spectrum(self, data: np.ndarray, 
                                   sample_rate: float = 30.0) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate frequency spectrum using FFT"""
        if len(data) < 4:
            return np.array([]), np.array([])
        
        # Apply window to reduce spectral leakage
        windowed_data = data * np.hanning(len(data))
        
        # Compute FFT
        fft = np.fft.fft(windowed_data)
        freqs = np.fft.fftfreq(len(data), 1.0 / sample_rate)
        
        # Take only positive frequencies
        positive_freqs = freqs[:len(freqs)//2]
        magnitude = np.abs(fft[:len(fft)//2])
        
        return positive_freqs, magnitude


def test_waveform_panel():
    """Test waveform panel functionality"""
    try:
        import pygame
        pygame.init()
        
        screen = pygame.display.set_mode((800, 600))
        font_manager = FontManager()
        
        # Create waveform panel
        panel = WaveformPanel(screen, 10, 10, 780, 580, font_manager)
        
        # Create test data
        test_data = {
            'phone': {
                'accelerometer_history': [np.random.randn(3) for _ in range(100)],
                'gyroscope_history': [np.random.randn(3) * 0.1 for _ in range(100)],
                'current_accel': np.array([0.1, -9.8, 0.2]),
                'current_gyro': np.array([0.01, -0.02, 0.005]),
                'frequency': 30.0,
                'is_active': True
            }
        }
        
        # Test update and render
        panel.update(test_data)
        panel.render()
        
        print("WaveformPanel test passed")
        return True
        
    except Exception as e:
        print(f"WaveformPanel test failed: {e}")
        return False
    finally:
        pygame.quit()


if __name__ == "__main__":
    test_waveform_panel()