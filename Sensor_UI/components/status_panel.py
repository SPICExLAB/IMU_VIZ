"""
Sensor_UI/components/status_panel.py - Status panel for system monitoring
Shows device connections, performance metrics, and system status
"""

import pygame
import time
import logging
from typing import Dict, Any, Tuple, List

from ..utils.colors import UIColors
from ..utils.fonts import FontManager

logger = logging.getLogger(__name__)


class StatusPanel:
    """Status panel showing system information and device states"""
    
    def __init__(self, screen, x: int, y: int, width: int, height: int, font_manager: FontManager):
        self.screen = screen
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font_manager = font_manager
        
        # Status information
        self.status_info = {
            'active_devices': 0,
            'device_info': [],
            'fps': 0.0,
            'selected_device': None,
            'calibration_active': False,
            'gravity_removal': True
        }
        
        # Performance tracking
        self.last_update = time.time()
        self.update_interval = 1.0  # Update every second
        
        # Display names
        self.device_display_names = {
            'phone': 'iPhone',
            'watch': 'Apple Watch',
            'headphone': 'AirPods',
            'glasses': 'AR Glasses'
        }
        
        logger.info("StatusPanel initialized")
    
    def update(self, status_info: Dict[str, Any]):
        """Update status panel information"""
        self.status_info.update(status_info)
        self.last_update = time.time()
    
    def render(self):
        """Render the status panel"""
        # Clear panel background
        pygame.draw.rect(self.screen, UIColors.PANEL_BACKGROUND, 
                        (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, UIColors.BORDER, 
                        (self.x, self.y, self.width, self.height), 2)
        
        # Draw title
        title_text = self.font_manager.render_text("System Status", 'large', UIColors.TEXT_PRIMARY)
        title_rect = title_text.get_rect(x=self.x + 10, y=self.y + 5)
        self.screen.blit(title_text, title_rect)
        
        # Draw status sections
        self._draw_connection_status()
        self._draw_performance_info()
        self._draw_system_status()
    
    def _draw_connection_status(self):
        """Draw device connection status"""
        section_x = self.x + 10
        section_y = self.y + 30
        section_width = 200
        
        # Section title
        title = self.font_manager.render_text("Connections", 'medium', UIColors.TEXT_SECONDARY)
        self.screen.blit(title, (section_x, section_y))
        
        # Device count
        device_count = self.status_info['active_devices']
        count_text = f"Active: {device_count} device{'s' if device_count != 1 else ''}"
        count_color = UIColors.SUCCESS if device_count > 0 else UIColors.ERROR
        count_surface = self.font_manager.render_text(count_text, 'small', count_color)
        self.screen.blit(count_surface, (section_x, section_y + 20))
        
        # Device details
        device_info = self.status_info.get('device_info', [])
        for i, device in enumerate(device_info[:3]):  # Show max 3 devices
            device_name = self.device_display_names.get(device['name'], device['name'].title())
            
            # Device status indicator
            status_color = UIColors.SUCCESS if device.get('frequency', 0) > 0 else UIColors.WARNING
            
            # Device text with frequency
            device_text = f"• {device_name}: {device.get('frequency', 0):.1f}Hz"
            device_surface = self.font_manager.render_text(device_text, 'small', status_color)
            self.screen.blit(device_surface, (section_x + 5, section_y + 40 + i * 15))
            
            # Sample count (if available)
            if 'sample_count' in device:
                samples_text = f"({device['sample_count']} samples)"
                samples_surface = self.font_manager.render_text(samples_text, 'tiny', UIColors.TEXT_SECONDARY)
                self.screen.blit(samples_surface, (section_x + 130, section_y + 40 + i * 15))
    
    def _draw_performance_info(self):
        """Draw performance information"""
        section_x = self.x + 220
        section_y = self.y + 30
        
        # Section title
        title = self.font_manager.render_text("Performance", 'medium', UIColors.TEXT_SECONDARY)
        self.screen.blit(title, (section_x, section_y))
        
        # UI FPS
        fps = self.status_info['fps']
        fps_text = f"UI FPS: {fps:.1f}"
        fps_color = UIColors.SUCCESS if fps > 45 else UIColors.WARNING if fps > 25 else UIColors.ERROR
        fps_surface = self.font_manager.render_text(fps_text, 'small', fps_color)
        self.screen.blit(fps_surface, (section_x, section_y + 20))
        
        # Total data rate
        device_info = self.status_info.get('device_info', [])
        total_rate = sum(device.get('frequency', 0) for device in device_info)
        rate_text = f"Data Rate: {total_rate:.0f} Hz"
        rate_color = UIColors.SUCCESS if total_rate > 0 else UIColors.TEXT_SECONDARY
        rate_surface = self.font_manager.render_text(rate_text, 'small', rate_color)
        self.screen.blit(rate_surface, (section_x, section_y + 35))
        
        # Update freshness
        time_since_update = time.time() - self.last_update
        if time_since_update < 1.0:
            update_text = "Live"
            update_color = UIColors.SUCCESS
        elif time_since_update < 5.0:
            update_text = f"{time_since_update:.1f}s ago"
            update_color = UIColors.WARNING
        else:
            update_text = "Stale"
            update_color = UIColors.ERROR
        
        update_surface = self.font_manager.render_text(f"Updated: {update_text}", 'small', update_color)
        self.screen.blit(update_surface, (section_x, section_y + 50))
    
    def _draw_system_status(self):
        """Draw system status indicators"""
        section_x = self.x + 400
        section_y = self.y + 30
        
        # Section title
        title = self.font_manager.render_text("System", 'medium', UIColors.TEXT_SECONDARY)
        self.screen.blit(title, (section_x, section_y))
        
        # Selected device
        selected = self.status_info.get('selected_device')
        if selected:
            selected_name = self.device_display_names.get(selected, selected.title())
            selected_text = f"Selected: {selected_name}"
            selected_surface = self.font_manager.render_text(selected_text, 'small', UIColors.ACCENT)
            self.screen.blit(selected_surface, (section_x, section_y + 20))
        else:
            no_selection = self.font_manager.render_text("No device selected", 'small', UIColors.TEXT_SECONDARY)
            self.screen.blit(no_selection, (section_x, section_y + 20))
        
        # Calibration status
        device_info = self.status_info.get('device_info', [])
        calibrated_count = sum(1 for device in device_info if device.get('is_calibrated', False))
        total_devices = len(device_info)
        
        if total_devices > 0:
            if calibrated_count == total_devices:
                calibration_text = "All calibrated"
                calibration_color = UIColors.SUCCESS
            elif calibrated_count > 0:
                calibration_text = f"{calibrated_count}/{total_devices} calibrated"
                calibration_color = UIColors.WARNING
            else:
                calibration_text = "Not calibrated"
                calibration_color = UIColors.ERROR
        else:
            calibration_text = "No devices"
            calibration_color = UIColors.TEXT_SECONDARY
        
        calibration_surface = self.font_manager.render_text(calibration_text, 'small', calibration_color)
        self.screen.blit(calibration_surface, (section_x, section_y + 35))
        
        # Gravity removal status (for AR glasses)
        gravity_status = self.status_info.get('gravity_removal', True)
        gravity_text = f"Gravity: {'Removed' if gravity_status else 'Included'}"
        gravity_color = UIColors.SUCCESS if gravity_status else UIColors.WARNING
        gravity_surface = self.font_manager.render_text(gravity_text, 'small', gravity_color)
        self.screen.blit(gravity_surface, (section_x, section_y + 50))
    
    def is_point_inside(self, pos: Tuple[int, int]) -> bool:
        """Check if point is inside the status panel"""
        return (self.x <= pos[0] <= self.x + self.width and 
                self.y <= pos[1] <= self.y + self.height)
    
    def get_device_summary(self) -> str:
        """Get a text summary of device status"""
        device_info = self.status_info.get('device_info', [])
        if not device_info:
            return "No devices connected"
        
        device_names = []
        for device in device_info:
            name = self.device_display_names.get(device['name'], device['name'].title())
            freq = device.get('frequency', 0)
            if freq > 0:
                device_names.append(f"{name} ({freq:.0f}Hz)")
            else:
                device_names.append(f"{name} (inactive)")
        
        return f"Connected: {', '.join(device_names)}"
    
    def get_performance_summary(self) -> str:
        """Get a text summary of system performance"""
        fps = self.status_info['fps']
        device_info = self.status_info.get('device_info', [])
        total_rate = sum(device.get('frequency', 0) for device in device_info)
        
        fps_status = "Good" if fps > 45 else "Fair" if fps > 25 else "Poor"
        return f"Performance: {fps_status} ({fps:.1f} FPS, {total_rate:.0f} Hz data rate)"
    
    def has_active_devices(self) -> bool:
        """Check if there are any active devices"""
        return self.status_info['active_devices'] > 0
    
    def get_calibration_status(self) -> Tuple[int, int]:
        """Get calibration status as (calibrated_count, total_count)"""
        device_info = self.status_info.get('device_info', [])
        calibrated_count = sum(1 for device in device_info if device.get('is_calibrated', False))
        total_count = len(device_info)
        return calibrated_count, total_count


class NetworkStatusIndicator:
    """Shows network connection and data flow status"""
    
    def __init__(self, screen, x: int, y: int, font_manager: FontManager):
        self.screen = screen
        self.x = x
        self.y = y
        self.font_manager = font_manager
        self.width = 150
        self.height = 60
        
        # Network status
        self.ports_listening = []
        self.last_packet_time = {}
        self.packet_counts = {}
        
    def update(self, listening_ports: List[int], packet_stats: Dict[str, int]):
        """Update network status"""
        self.ports_listening = listening_ports
        self.packet_counts = packet_stats
        
        # Update last packet times
        current_time = time.time()
        for packet_type, count in packet_stats.items():
            if packet_type in self.last_packet_time:
                if count > self.packet_counts.get(packet_type, 0):
                    self.last_packet_time[packet_type] = current_time
            else:
                self.last_packet_time[packet_type] = current_time
    
    def render(self):
        """Render network status indicator"""
        # Background
        pygame.draw.rect(self.screen, UIColors.PANEL_BACKGROUND,
                        (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, UIColors.BORDER,
                        (self.x, self.y, self.width, self.height), 1)
        
        # Title
        title = self.font_manager.render_text("Network", 'small', UIColors.TEXT_SECONDARY)
        self.screen.blit(title, (self.x + 5, self.y + 5))
        
        # Listening ports
        if self.ports_listening:
            ports_text = f"Ports: {', '.join(map(str, self.ports_listening))}"
            ports_surface = self.font_manager.render_text(ports_text, 'tiny', UIColors.TEXT_PRIMARY)
            self.screen.blit(ports_surface, (self.x + 5, self.y + 20))
        else:
            no_ports = self.font_manager.render_text("No ports listening", 'tiny', UIColors.ERROR)
            self.screen.blit(no_ports, (self.x + 5, self.y + 20))
        
        # Packet statistics
        current_time = time.time()
        y_offset = 35
        
        for packet_type, count in self.packet_counts.items():
            # Time since last packet
            last_time = self.last_packet_time.get(packet_type, 0)
            time_since = current_time - last_time
            
            # Status color based on recency
            if time_since < 1.0:
                status_color = UIColors.SUCCESS
                status_text = "Live"
            elif time_since < 5.0:
                status_color = UIColors.WARNING
                status_text = f"{time_since:.1f}s"
            else:
                status_color = UIColors.ERROR
                status_text = "Stale"
            
            # Packet type and count
            packet_text = f"{packet_type.upper()}: {count}"
            packet_surface = self.font_manager.render_text(packet_text, 'tiny', UIColors.TEXT_PRIMARY)
            self.screen.blit(packet_surface, (self.x + 5, self.y + y_offset))
            
            # Status indicator
            status_surface = self.font_manager.render_text(status_text, 'tiny', status_color)
            self.screen.blit(status_surface, (self.x + 80, self.y + y_offset))
            
            y_offset += 12


class DeviceHealthMonitor:
    """Monitors individual device health and connection quality"""
    
    def __init__(self, screen, x: int, y: int, font_manager: FontManager):
        self.screen = screen
        self.x = x
        self.y = y
        self.font_manager = font_manager
        self.width = 200
        self.height = 100
        
        # Device health data
        self.device_health = {}
        
    def update_device_health(self, device_name: str, frequency: float, 
                           last_update: float, sample_count: int):
        """Update health metrics for a device"""
        current_time = time.time()
        
        if device_name not in self.device_health:
            self.device_health[device_name] = {
                'frequency_history': deque(maxlen=10),
                'last_update': last_update,
                'sample_count': sample_count,
                'connection_quality': 'Unknown'
            }
        
        health = self.device_health[device_name]
        health['frequency_history'].append(frequency)
        health['last_update'] = last_update
        health['sample_count'] = sample_count
        
        # Calculate connection quality
        time_since_update = current_time - last_update
        avg_frequency = sum(health['frequency_history']) / len(health['frequency_history'])
        
        if time_since_update > 5.0:
            health['connection_quality'] = 'Disconnected'
        elif avg_frequency < 5.0:
            health['connection_quality'] = 'Poor'
        elif avg_frequency < 20.0:
            health['connection_quality'] = 'Fair'
        else:
            health['connection_quality'] = 'Good'
    
    def render(self):
        """Render device health monitor"""
        # Background
        pygame.draw.rect(self.screen, UIColors.PANEL_BACKGROUND,
                        (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, UIColors.BORDER,
                        (self.x, self.y, self.width, self.height), 1)
        
        # Title
        title = self.font_manager.render_text("Device Health", 'small', UIColors.TEXT_SECONDARY)
        self.screen.blit(title, (self.x + 5, self.y + 5))
        
        # Device health status
        y_offset = 20
        
        for device_name, health in self.device_health.items():
            quality = health['connection_quality']
            
            # Quality color
            if quality == 'Good':
                quality_color = UIColors.SUCCESS
            elif quality == 'Fair':
                quality_color = UIColors.WARNING
            elif quality == 'Poor':
                quality_color = UIColors.ERROR
            else:
                quality_color = UIColors.TEXT_SECONDARY
            
            # Device name
            device_surface = self.font_manager.render_text(f"{device_name.title()}:", 'tiny', UIColors.TEXT_PRIMARY)
            self.screen.blit(device_surface, (self.x + 5, self.y + y_offset))
            
            # Quality indicator
            quality_surface = self.font_manager.render_text(quality, 'tiny', quality_color)
            self.screen.blit(quality_surface, (self.x + 80, self.y + y_offset))
            
            # Sample count
            samples_text = f"({health['sample_count']})"
            samples_surface = self.font_manager.render_text(samples_text, 'tiny', UIColors.TEXT_SECONDARY)
            self.screen.blit(samples_surface, (self.x + 130, self.y + y_offset))
            
            y_offset += 15
        
        if not self.device_health:
            no_devices = self.font_manager.render_text("No devices connected", 'tiny', UIColors.TEXT_SECONDARY)
            self.screen.blit(no_devices, (self.x + 5, self.y + 25))


def test_status_panel():
    """Test status panel functionality"""
    try:
        import pygame
        pygame.init()
        
        screen = pygame.display.set_mode((800, 100))
        font_manager = FontManager()
        
        # Create status panel
        status_panel = StatusPanel(screen, 10, 10, 780, 80, font_manager)
        
        # Test data
        status_info = {
            'active_devices': 2,
            'device_info': [
                {'name': 'phone', 'frequency': 30.0, 'is_calibrated': False, 'sample_count': 1500},
                {'name': 'watch', 'frequency': 25.0, 'is_calibrated': True, 'sample_count': 1200}
            ],
            'fps': 60.0,
            'selected_device': 'phone',
            'calibration_active': False,
            'gravity_removal': True
        }
        
        # Test update and render
        status_panel.update(status_info)
        status_panel.render()
        
        print("StatusPanel test passed")
        print("Device summary:", status_panel.get_device_summary())
        print("Performance summary:", status_panel.get_performance_summary())
        print("Calibration status:", status_panel.get_calibration_status())
        
        return True
        
    except Exception as e:
        print(f"StatusPanel test failed: {e}")
        return False
    finally:
        pygame.quit()


if __name__ == "__main__":
    test_status_panel()