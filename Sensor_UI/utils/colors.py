"""
Sensor_UI/utils/colors.py - UI color scheme and device colors
"""

class UIColors:
    """Centralized color scheme for the UI"""
    
    # Background colors
    BACKGROUND = (20, 24, 32)
    PANEL_BACKGROUND = (32, 38, 48)
    
    # Text colors
    TEXT_PRIMARY = (255, 255, 255)
    TEXT_SECONDARY = (180, 190, 200)
    TEXT_INACTIVE = (120, 130, 140)
    TEXT_TERTIARY = (100, 110, 120)
    
    # Border colors
    BORDER = (80, 90, 100)
    BORDER_INACTIVE = (60, 70, 80)
    
    # Status colors
    SUCCESS = (50, 200, 50)      # Green - calibrated/connected
    WARNING = (255, 200, 50)     # Yellow - warning states
    ERROR = (255, 80, 80)        # Red - errors
    ACCENT = (100, 150, 255)     # Blue - selected/highlighted
    
    # Device-specific colors
    DEVICE_PHONE = (255, 100, 100)        # Red - iPhone
    DEVICE_WATCH = (100, 150, 255)        # Blue - Apple Watch
    DEVICE_HEADPHONE = (100, 255, 100)    # Green - AirPods
    DEVICE_GLASSES = (255, 150, 50)       # Orange - AR Glasses
    
    # Coordinate axis colors (standard RGB)
    AXIS_X = (255, 60, 60)    # Red - X axis
    AXIS_Y = (60, 255, 60)    # Green - Y axis
    AXIS_Z = (60, 60, 255)    # Blue - Z axis
    
    # Waveform colors
    WAVEFORM_BACKGROUND = (25, 30, 38)
    WAVEFORM_GRID = (50, 60, 70)
    WAVEFORM_ZERO_LINE = (100, 110, 120)
    
    # Button colors
    BUTTON_NORMAL = (70, 80, 100)
    BUTTON_HOVER = (90, 100, 120)
    BUTTON_PRESSED = (50, 60, 80)
    
    @classmethod
    def get_device_color(cls, device_name: str):
        """Get color for specific device type"""
        device_colors = {
            'phone': cls.DEVICE_PHONE,
            'watch': cls.DEVICE_WATCH,
            'headphone': cls.DEVICE_HEADPHONE,
            'glasses': cls.DEVICE_GLASSES
        }
        return device_colors.get(device_name.lower(), cls.TEXT_SECONDARY)
    
    @classmethod
    def get_axis_color(cls, axis_index: int):
        """Get color for coordinate axis (0=X, 1=Y, 2=Z)"""
        axis_colors = [cls.AXIS_X, cls.AXIS_Y, cls.AXIS_Z]
        return axis_colors[axis_index] if 0 <= axis_index < 3 else cls.TEXT_SECONDARY
    
    @classmethod
    def blend_colors(cls, color1, color2, factor: float):
        """Blend two colors with given factor (0.0 = color1, 1.0 = color2)"""
        factor = max(0.0, min(1.0, factor))
        return tuple(int(c1 + (c2 - c1) * factor) for c1, c2 in zip(color1, color2))
    
    @classmethod
    def darken_color(cls, color, factor: float):
        """Darken a color by given factor (0.0 = black, 1.0 = original)"""
        factor = max(0.0, min(1.0, factor))
        return tuple(int(c * factor) for c in color)
    
    @classmethod
    def lighten_color(cls, color, factor: float):
        """Lighten a color by given factor (0.0 = original, 1.0 = white)"""
        factor = max(0.0, min(1.0, factor))
        return tuple(int(c + (255 - c) * factor) for c in color)