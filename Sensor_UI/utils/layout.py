"""
Sensor_UI/utils/layout.py - Layout management for UI components
"""

import logging
from typing import Dict, Tuple, Any

logger = logging.getLogger(__name__)

class LayoutManager:
    """Manages layout of UI components"""
    
    def __init__(self, window_width: int, window_height: int):
        self.window_width = window_width
        self.window_height = window_height
        
        # Layout constants
        self.PANEL_MARGIN = 10
        self.DEVICE_PANEL_SIZE = 200
        self.CONTROL_PANEL_HEIGHT = 100
        self.STATUS_PANEL_HEIGHT = 80
        
        # Calculate basic layout dimensions
        self.device_area_width = 600  # Left side for device panels
        self.waveform_area_width = window_width - self.device_area_width - 3 * self.PANEL_MARGIN
        
        logger.info(f"LayoutManager initialized for {window_width}x{window_height}")
    
    def calculate_layout(self) -> Dict[str, Dict[str, int]]:
        """Calculate positions and sizes for all UI areas"""
        layout = {}
        
        # Device visualization area (left side)
        layout['device_area'] = {
            'x': self.PANEL_MARGIN,
            'y': self.PANEL_MARGIN,
            'width': self.device_area_width,
            'height': self.window_height - self.CONTROL_PANEL_HEIGHT - 3 * self.PANEL_MARGIN
        }
        
        # Waveform area (right side)
        layout['waveform_area'] = {
            'x': self.device_area_width + 2 * self.PANEL_MARGIN,
            'y': self.PANEL_MARGIN,
            'width': self.waveform_area_width,
            'height': self.window_height - self.STATUS_PANEL_HEIGHT - 3 * self.PANEL_MARGIN
        }
        
        # Control panel (bottom left)
        layout['control_area'] = {
            'x': self.PANEL_MARGIN,
            'y': self.window_height - self.CONTROL_PANEL_HEIGHT - self.PANEL_MARGIN,
            'width': self.device_area_width,
            'height': self.CONTROL_PANEL_HEIGHT
        }
        
        # Status panel (bottom right)
        layout['status_area'] = {
            'x': self.device_area_width + 2 * self.PANEL_MARGIN,
            'y': self.window_height - self.STATUS_PANEL_HEIGHT - self.PANEL_MARGIN,
            'width': self.waveform_area_width,
            'height': self.STATUS_PANEL_HEIGHT
        }
        
        return layout
    
    def calculate_device_positions(self, device_area: Dict[str, int]) -> Dict[str, Dict[str, int]]:
        """Calculate positions for individual device panels within the device area"""
        positions = {}
        
        # Device panel dimensions
        panel_width = self.DEVICE_PANEL_SIZE
        panel_height = self.DEVICE_PANEL_SIZE
        
        # Calculate grid layout (2x2 for 4 devices)
        cols = 2
        rows = 2
        
        # Calculate spacing
        total_width = cols * panel_width
        total_height = rows * panel_height
        
        h_spacing = (device_area['width'] - total_width) // (cols + 1)
        v_spacing = (device_area['height'] - total_height) // (rows + 1)
        
        # Device layout order
        device_layout = [
            ('phone', 0, 0),      # Top left
            ('watch', 1, 0),      # Top right
            ('headphone', 0, 1),  # Bottom left
            ('glasses', 1, 1)     # Bottom right
        ]
        
        for device_name, col, row in device_layout:
            x = device_area['x'] + h_spacing + col * (panel_width + h_spacing)
            y = device_area['y'] + v_spacing + row * (panel_height + v_spacing)
            
            positions[device_name] = {
                'x': x,
                'y': y,
                'width': panel_width,
                'height': panel_height
            }
        
        return positions
    
    def calculate_waveform_layout(self, waveform_area: Dict[str, int], 
                                 num_devices: int) -> Dict[str, Dict[str, int]]:
        """Calculate layout for waveform displays"""
        if num_devices == 0:
            return {}
        
        # Each device gets equal vertical space
        device_height = (waveform_area['height'] - (num_devices + 1) * self.PANEL_MARGIN) // num_devices
        
        layout = {}
        current_y = waveform_area['y'] + self.PANEL_MARGIN
        
        device_names = ['phone', 'watch', 'headphone', 'glasses']
        
        for i in range(min(num_devices, len(device_names))):
            device_name = device_names[i]
            layout[device_name] = {
                'x': waveform_area['x'],
                'y': current_y,
                'width': waveform_area['width'],
                'height': device_height
            }
            current_y += device_height + self.PANEL_MARGIN
        
        return layout
    
    def get_optimal_device_panel_size(self, device_area: Dict[str, int], 
                                     num_active_devices: int) -> Tuple[int, int]:
        """Calculate optimal device panel size based on number of active devices"""
        if num_active_devices <= 1:
            # Single large panel
            return min(device_area['width'] - 2 * self.PANEL_MARGIN, 
                      device_area['height'] - 2 * self.PANEL_MARGIN), \
                   min(device_area['width'] - 2 * self.PANEL_MARGIN, 
                      device_area['height'] - 2 * self.PANEL_MARGIN)
        
        elif num_active_devices <= 2:
            # Two panels side by side
            width = (device_area['width'] - 3 * self.PANEL_MARGIN) // 2
            height = device_area['height'] - 2 * self.PANEL_MARGIN
            return width, height
        
        elif num_active_devices <= 4:
            # 2x2 grid
            width = (device_area['width'] - 3 * self.PANEL_MARGIN) // 2
            height = (device_area['height'] - 3 * self.PANEL_MARGIN) // 2
            return width, height
        
        else:
            # More than 4 devices - use smaller panels
            cols = 3
            rows = 2
            width = (device_area['width'] - (cols + 1) * self.PANEL_MARGIN) // cols
            height = (device_area['height'] - (rows + 1) * self.PANEL_MARGIN) // rows
            return width, height
    
    def calculate_adaptive_device_layout(self, device_area: Dict[str, int], 
                                       active_devices: list) -> Dict[str, Dict[str, int]]:
        """Calculate adaptive layout based on which devices are active"""
        positions = {}
        num_active = len(active_devices)
        
        if num_active == 0:
            return self.calculate_device_positions(device_area)  # Default layout
        
        # Get optimal panel size
        panel_width, panel_height = self.get_optimal_device_panel_size(device_area, num_active)
        
        if num_active == 1:
            # Single device - center it
            device_name = active_devices[0]
            x = device_area['x'] + (device_area['width'] - panel_width) // 2
            y = device_area['y'] + (device_area['height'] - panel_height) // 2
            
            positions[device_name] = {
                'x': x, 'y': y,
                'width': panel_width,
                'height': panel_height
            }
        
        elif num_active == 2:
            # Two devices side by side
            spacing = (device_area['width'] - 2 * panel_width) // 3
            y = device_area['y'] + (device_area['height'] - panel_height) // 2
            
            for i, device_name in enumerate(active_devices):
                x = device_area['x'] + spacing + i * (panel_width + spacing)
                positions[device_name] = {
                    'x': x, 'y': y,
                    'width': panel_width,
                    'height': panel_height
                }
        
        elif num_active <= 4:
            # 2x2 grid
            cols = 2
            rows = 2
            h_spacing = (device_area['width'] - cols * panel_width) // (cols + 1)
            v_spacing = (device_area['height'] - rows * panel_height) // (rows + 1)
            
            for i, device_name in enumerate(active_devices):
                col = i % cols
                row = i // cols
                
                x = device_area['x'] + h_spacing + col * (panel_width + h_spacing)
                y = device_area['y'] + v_spacing + row * (panel_height + v_spacing)
                
                positions[device_name] = {
                    'x': x, 'y': y,
                    'width': panel_width,
                    'height': panel_height
                }
        
        else:
            # More than 4 devices - use 3x2 grid
            cols = 3
            rows = 2
            h_spacing = (device_area['width'] - cols * panel_width) // (cols + 1)
            v_spacing = (device_area['height'] - rows * panel_height) // (rows + 1)
            
            for i, device_name in enumerate(active_devices[:6]):  # Max 6 devices
                col = i % cols
                row = i // cols
                
                x = device_area['x'] + h_spacing + col * (panel_width + h_spacing)
                y = device_area['y'] + v_spacing + row * (panel_height + v_spacing)
                
                positions[device_name] = {
                    'x': x, 'y': y,
                    'width': panel_width,
                    'height': panel_height
                }
        
        return positions
    
    def get_button_layout(self, area: Dict[str, int], num_buttons: int, 
                         button_width: int = 100, button_height: int = 30) -> list:
        """Calculate button positions within an area"""
        if num_buttons == 0:
            return []
        
        # Calculate spacing
        total_width = num_buttons * button_width + (num_buttons - 1) * self.PANEL_MARGIN
        start_x = area['x'] + (area['width'] - total_width) // 2
        button_y = area['y'] + (area['height'] - button_height) // 2
        
        buttons = []
        for i in range(num_buttons):
            x = start_x + i * (button_width + self.PANEL_MARGIN)
            buttons.append({
                'x': x,
                'y': button_y,
                'width': button_width,
                'height': button_height
            })
        
        return buttons
    
    def calculate_text_area(self, area: Dict[str, int], num_lines: int, 
                           line_height: int = 20) -> Dict[str, int]:
        """Calculate optimal text area within given area"""
        total_text_height = num_lines * line_height
        
        # Center text vertically if there's extra space
        if total_text_height < area['height']:
            y_offset = (area['height'] - total_text_height) // 2
        else:
            y_offset = 0
        
        return {
            'x': area['x'] + self.PANEL_MARGIN,
            'y': area['y'] + y_offset,
            'width': area['width'] - 2 * self.PANEL_MARGIN,
            'height': min(total_text_height, area['height'])
        }
    
    def get_responsive_font_size(self, area_width: int, text_length: int) -> str:
        """Get appropriate font size based on available width and text length"""
        # Estimate character width (rough approximation)
        char_width_estimates = {
            'tiny': 7,
            'small': 9,
            'medium': 11,
            'large': 14,
            'xlarge': 17
        }
        
        # Try different font sizes
        for size in ['xlarge', 'large', 'medium', 'small', 'tiny']:
            estimated_width = text_length * char_width_estimates[size]
            if estimated_width <= area_width * 0.9:  # Leave some margin
                return size
        
        return 'tiny'  # Fallback
    
    def scale_layout_for_dpi(self, dpi_scale: float) -> None:
        """Scale layout dimensions for different DPI settings"""
        self.PANEL_MARGIN = int(self.PANEL_MARGIN * dpi_scale)
        self.DEVICE_PANEL_SIZE = int(self.DEVICE_PANEL_SIZE * dpi_scale)
        self.CONTROL_PANEL_HEIGHT = int(self.CONTROL_PANEL_HEIGHT * dpi_scale)
        self.STATUS_PANEL_HEIGHT = int(self.STATUS_PANEL_HEIGHT * dpi_scale)
        
        logger.info(f"Layout scaled for DPI: {dpi_scale}")
    
    def get_layout_info(self) -> Dict[str, Any]:
        """Get current layout configuration info"""
        return {
            'window_size': (self.window_width, self.window_height),
            'device_area_width': self.device_area_width,
            'waveform_area_width': self.waveform_area_width,
            'panel_margin': self.PANEL_MARGIN,
            'device_panel_size': self.DEVICE_PANEL_SIZE,
            'control_panel_height': self.CONTROL_PANEL_HEIGHT,
            'status_panel_height': self.STATUS_PANEL_HEIGHT
        }


class ResponsiveLayout(LayoutManager):
    """Extended layout manager with responsive design capabilities"""
    
    def __init__(self, window_width: int, window_height: int):
        super().__init__(window_width, window_height)
        
        # Breakpoints for responsive design
        self.SMALL_SCREEN_WIDTH = 1024
        self.MEDIUM_SCREEN_WIDTH = 1280
        self.LARGE_SCREEN_WIDTH = 1600
        
        # Adjust layout based on screen size
        self._adjust_for_screen_size()
    
    def _adjust_for_screen_size(self):
        """Adjust layout parameters based on screen size"""
        if self.window_width < self.SMALL_SCREEN_WIDTH:
            # Small screen adjustments
            self.device_area_width = int(self.window_width * 0.4)
            self.DEVICE_PANEL_SIZE = 150
            self.CONTROL_PANEL_HEIGHT = 80
            self.STATUS_PANEL_HEIGHT = 60
            
        elif self.window_width < self.MEDIUM_SCREEN_WIDTH:
            # Medium screen adjustments
            self.device_area_width = int(self.window_width * 0.42)
            self.DEVICE_PANEL_SIZE = 180
            
        elif self.window_width < self.LARGE_SCREEN_WIDTH:
            # Large screen adjustments
            self.device_area_width = int(self.window_width * 0.45)
            self.DEVICE_PANEL_SIZE = 220
        
        else:
            # Extra large screen adjustments
            self.device_area_width = int(self.window_width * 0.4)
            self.DEVICE_PANEL_SIZE = 250
            self.CONTROL_PANEL_HEIGHT = 120
            self.STATUS_PANEL_HEIGHT = 100
        
        # Recalculate waveform area width
        self.waveform_area_width = self.window_width - self.device_area_width - 3 * self.PANEL_MARGIN
        
        logger.info(f"Layout adjusted for screen size: {self.window_width}x{self.window_height}")
    
    def get_screen_size_category(self) -> str:
        """Get screen size category for responsive adjustments"""
        if self.window_width < self.SMALL_SCREEN_WIDTH:
            return 'small'
        elif self.window_width < self.MEDIUM_SCREEN_WIDTH:
            return 'medium'
        elif self.window_width < self.LARGE_SCREEN_WIDTH:
            return 'large'
        else:
            return 'xlarge'