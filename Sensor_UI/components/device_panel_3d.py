"""
Sensor_UI/components/device_panel_3d.py - Real 3D OpenGL device visualization
Proper 3D rendering with correct coordinate systems
"""

import pygame
import numpy as np
import logging
from scipy.spatial.transform import Rotation as R
from typing import Optional, Dict, Any, Tuple
import math

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    import pygame.locals
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    logging.warning("OpenGL not available, falling back to 2D rendering")

from ..utils.colors import UIColors
from ..rendering.opengl_renderer import OpenGLRenderer
from ..rendering.device_models import DeviceModels
from ..rendering.coordinate_system import CoordinateSystem

logger = logging.getLogger(__name__)


class DevicePanel3D:
    """3D device visualization panel with real OpenGL rendering"""
    
    def __init__(self, screen, device_name: str, x: int, y: int, width: int, height: int, font_manager):
        self.screen = screen
        self.device_name = device_name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font_manager = font_manager
        
        # Device state
        self.device_data = None
        self.is_active = False
        self.is_selected = False
        self.is_calibrated = False
        self.gravity_enabled = True
        
        # 3D rendering
        self.use_opengl = OPENGL_AVAILABLE
        self.opengl_renderer = None
        self.device_models = None
        self.coordinate_system = None
        
        # Camera controls
        self.camera_rotation_x = 20.0  # Initial X rotation
        self.camera_rotation_y = 45.0  # Initial Y rotation
        self.camera_distance = 3.0
        self.mouse_dragging = False
        self.last_mouse_pos = None
        
        # Display names
        self.display_names = {
            'phone': 'iPhone',
            'watch': 'Apple Watch',
            'headphone': 'AirPods',
            'glasses': 'AR Glasses'
        }
        
        self._initialize_3d_rendering()
        logger.info(f"DevicePanel3D initialized for {device_name} ({'OpenGL' if self.use_opengl else '2D fallback'})")
    
    def _initialize_3d_rendering(self):
        """Initialize 3D rendering components"""
        if self.use_opengl:
            try:
                # Initialize OpenGL components
                self.opengl_renderer = OpenGLRenderer(self.width, self.height)
                self.device_models = DeviceModels()
                self.coordinate_system = CoordinateSystem()
                
                # Set up viewport for this panel
                self._setup_opengl_viewport()
                
            except Exception as e:
                logger.error(f"Failed to initialize OpenGL for {self.device_name}: {e}")
                self.use_opengl = False
    
    def _setup_opengl_viewport(self):
        """Setup OpenGL viewport and projection for this panel"""
        if not self.use_opengl or not self.opengl_renderer:
            return
        
        # Set viewport to panel area
        glViewport(self.x, self.screen.get_height() - (self.y + self.height), 
                  self.width, self.height)
        
        # Set projection matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        
        aspect_ratio = self.width / self.height
        gluPerspective(45.0, aspect_ratio, 0.1, 100.0)
        
        # Set modelview matrix
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
    
    def update(self, device_data: Optional[Dict[str, Any]], is_active: bool, 
               is_selected: bool, is_calibrated: bool, gravity_enabled: bool):
        """Update device panel with new data"""
        self.device_data = device_data
        self.is_active = is_active
        self.is_selected = is_selected
        self.is_calibrated = is_calibrated
        self.gravity_enabled = gravity_enabled
    
    def render(self):
        """Render the device panel"""
        # Draw panel background and border
        self._draw_panel_background()
        
        if self.is_active and self.device_data:
            # Draw active device
            if self.use_opengl:
                self._render_3d_device()
            else:
                self._render_2d_fallback()
            
            # Draw device info overlay
            self._draw_device_info()
        else:
            # Draw inactive device placeholder
            self._draw_inactive_device()
    
    def _draw_panel_background(self):
        """Draw panel background and border"""
        # Determine colors based on device state
        if self.is_selected:
            border_color = UIColors.ACCENT
            border_width = 4
        elif self.is_active:
            if self.is_calibrated:
                border_color = UIColors.SUCCESS
            else:
                border_color = UIColors.get_device_color(self.device_name)
            border_width = 2
        else:
            border_color = UIColors.BORDER_INACTIVE
            border_width = 1
        
        background_color = UIColors.PANEL_BACKGROUND
        
        # Draw background
        pygame.draw.rect(self.screen, background_color, (self.x, self.y, self.width, self.height))
        
        # Draw border
        pygame.draw.rect(self.screen, border_color, (self.x, self.y, self.width, self.height), border_width)
        
        # Draw corner indicator for device type
        corner_size = 20
        corner_color = UIColors.get_device_color(self.device_name)
        pygame.draw.polygon(self.screen, corner_color, [
            (self.x, self.y),
            (self.x + corner_size, self.y),
            (self.x, self.y + corner_size)
        ])
    
    def _render_3d_device(self):
        """Render device using OpenGL 3D graphics"""
        if not self.opengl_renderer or not self.device_data:
            return
        
        try:
            # Setup viewport for this panel
            self._setup_opengl_viewport()
            
            # Clear depth buffer for this panel area
            glEnable(GL_SCISSOR_TEST)
            glScissor(self.x, self.screen.get_height() - (self.y + self.height), 
                     self.width, self.height)
            glClear(GL_DEPTH_BUFFER_BIT)
            glDisable(GL_SCISSOR_TEST)
            
            # Setup camera
            glLoadIdentity()
            
            # Camera positioning
            camera_x = self.camera_distance * math.sin(math.radians(self.camera_rotation_y)) * math.cos(math.radians(self.camera_rotation_x))
            camera_y = self.camera_distance * math.sin(math.radians(self.camera_rotation_x))
            camera_z = self.camera_distance * math.cos(math.radians(self.camera_rotation_y)) * math.cos(math.radians(self.camera_rotation_x))
            
            gluLookAt(camera_x, camera_y, camera_z,  # Camera position
                     0, 0, 0,                        # Look at origin
                     0, 1, 0)                        # Up vector
            
            # Enable lighting
            self._setup_lighting()
            
            # Get device quaternion
            quaternion = self.device_data.get('quaternion', np.array([0, 0, 0, 1]))
            
            # Draw coordinate system axes
            self._draw_3d_coordinate_axes(quaternion)
            
            # Draw device model
            self._draw_3d_device_model(quaternion)
            
            # Disable lighting
            glDisable(GL_LIGHTING)
            
        except Exception as e:
            logger.error(f"Error rendering 3D device {self.device_name}: {e}")
            # Fall back to 2D rendering
            self._render_2d_fallback()
    
    def _setup_lighting(self):
        """Setup OpenGL lighting"""
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        
        # Light position
        light_pos = [2.0, 2.0, 2.0, 1.0]
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        
        # Light colors
        light_ambient = [0.3, 0.3, 0.3, 1.0]
        light_diffuse = [0.8, 0.8, 0.8, 1.0]
        light_specular = [1.0, 1.0, 1.0, 1.0]
        
        glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
        glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)
        
        # Enable color material
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    def _draw_3d_coordinate_axes(self, quaternion: np.ndarray):
        """Draw 3D coordinate system axes"""
        if not self.coordinate_system:
            return
        
        try:
            # Convert quaternion to rotation matrix
            if np.linalg.norm(quaternion) > 0:
                rotation = R.from_quat(quaternion)
                rotation_matrix = rotation.as_matrix()
            else:
                rotation_matrix = np.eye(3)
            
            # Draw axes
            self.coordinate_system.draw_axes_3d(rotation_matrix, length=1.5, thickness=0.05)
            
        except Exception as e:
            logger.error(f"Error drawing coordinate axes: {e}")
    
    def _draw_3d_device_model(self, quaternion: np.ndarray):
        """Draw 3D device model"""
        if not self.device_models:
            return
        
        try:
            # Apply device rotation
            glPushMatrix()
            
            if np.linalg.norm(quaternion) > 0:
                # Convert quaternion to rotation matrix
                rotation = R.from_quat(quaternion)
                rotation_matrix = rotation.as_matrix().flatten()
                
                # Apply rotation (OpenGL uses column-major matrices)
                rotation_matrix_gl = np.array([
                    rotation_matrix[0], rotation_matrix[3], rotation_matrix[6], 0,
                    rotation_matrix[1], rotation_matrix[4], rotation_matrix[7], 0,
                    rotation_matrix[2], rotation_matrix[5], rotation_matrix[8], 0,
                    0, 0, 0, 1
                ], dtype=np.float32)
                
                glMultMatrixf(rotation_matrix_gl)
            
            # Set device color
            device_color = UIColors.get_device_color(self.device_name)
            color_normalized = [c / 255.0 for c in device_color] + [1.0]
            glColor4fv(color_normalized)
            
            # Draw device model
            self.device_models.draw_device(self.device_name)
            
            glPopMatrix()
            
        except Exception as e:
            logger.error(f"Error drawing device model: {e}")
    
    def _render_2d_fallback(self):
        """Fallback 2D rendering when OpenGL is not available"""
        if not self.device_data:
            return
        
        # Calculate center of panel
        center_x = self.x + self.width // 2
        center_y = self.y + self.height // 2
        
        # Draw simple 2D representation
        device_size = min(self.width, self.height) // 4
        device_color = UIColors.get_device_color(self.device_name)
        
        # Draw device shape based on type
        if self.device_name == 'phone':
            # Rectangle for phone
            rect = pygame.Rect(center_x - device_size//2, center_y - device_size, 
                             device_size, device_size * 2)
            pygame.draw.rect(self.screen, device_color, rect)
            pygame.draw.rect(self.screen, UIColors.TEXT_PRIMARY, rect, 2)
        
        elif self.device_name == 'watch':
            # Square for watch
            rect = pygame.Rect(center_x - device_size//2, center_y - device_size//2, 
                             device_size, device_size)
            pygame.draw.rect(self.screen, device_color, rect)
            pygame.draw.rect(self.screen, UIColors.TEXT_PRIMARY, rect, 2)
        
        elif self.device_name == 'headphone':
            # Circle for AirPods
            pygame.draw.circle(self.screen, device_color, (center_x, center_y), device_size//2)
            pygame.draw.circle(self.screen, UIColors.TEXT_PRIMARY, (center_x, center_y), device_size//2, 2)
        
        elif self.device_name == 'glasses':
            # Glasses shape
            lens_radius = device_size // 3
            lens_y = center_y
            left_lens_x = center_x - lens_radius - 5
            right_lens_x = center_x + lens_radius + 5
            
            # Draw lenses
            pygame.draw.circle(self.screen, device_color, (left_lens_x, lens_y), lens_radius)
            pygame.draw.circle(self.screen, device_color, (right_lens_x, lens_y), lens_radius)
            
            # Draw bridge
            pygame.draw.line(self.screen, device_color, 
                           (left_lens_x + lens_radius, lens_y), 
                           (right_lens_x - lens_radius, lens_y), 3)
        
        # Draw simplified orientation indicator
        self._draw_2d_orientation_indicator(center_x, center_y + device_size + 20)
    
    def _draw_2d_orientation_indicator(self, x: int, y: int):
        """Draw 2D orientation indicator"""
        if not self.device_data:
            return
        
        quaternion = self.device_data.get('quaternion', np.array([0, 0, 0, 1]))
        
        try:
            # Convert quaternion to Euler angles for simple display
            if np.linalg.norm(quaternion) > 0:
                rotation = R.from_quat(quaternion)
                euler = rotation.as_euler('xyz', degrees=True)
                
                # Draw simple arrow indicating orientation
                arrow_length = 30
                angle = math.radians(euler[2])  # Use yaw angle
                
                end_x = x + arrow_length * math.cos(angle)
                end_y = y + arrow_length * math.sin(angle)
                
                pygame.draw.line(self.screen, UIColors.ACCENT, (x, y), (end_x, end_y), 3)
                
                # Draw arrowhead
                arrowhead_length = 8
                arrowhead_angle = math.pi / 6
                
                left_x = end_x - arrowhead_length * math.cos(angle - arrowhead_angle)
                left_y = end_y - arrowhead_length * math.sin(angle - arrowhead_angle)
                right_x = end_x - arrowhead_length * math.cos(angle + arrowhead_angle)
                right_y = end_y - arrowhead_length * math.sin(angle + arrowhead_angle)
                
                pygame.draw.polygon(self.screen, UIColors.ACCENT, 
                                  [(end_x, end_y), (left_x, left_y), (right_x, right_y)])
        
        except Exception as e:
            logger.error(f"Error drawing 2D orientation indicator: {e}")
    
    def _draw_device_info(self):
        """Draw device information overlay"""
        if not self.device_data:
            return
        
        # Device name and status
        display_name = self.display_names.get(self.device_name, self.device_name.title())
        status = "CAL" if self.is_calibrated else "UNCAL"
        
        name_text = f"{status} {display_name}"
        name_surface = self.font_manager.render_text(name_text, 'small', UIColors.TEXT_PRIMARY)
        name_rect = name_surface.get_rect(centerx=self.x + self.width//2, y=self.y + 5)
        self.screen.blit(name_surface, name_rect)
        
        # Frequency and sample count
        frequency = self.device_data.get('frequency', 0)
        sample_count = self.device_data.get('sample_count', 0)
        
        info_text = f"{frequency:.1f}Hz | {sample_count} samples"
        info_surface = self.font_manager.render_text(info_text, 'tiny', UIColors.TEXT_SECONDARY)
        info_rect = info_surface.get_rect(centerx=self.x + self.width//2, y=self.y + 25)
        self.screen.blit(info_surface, info_rect)
        
        # Orientation values (for AR glasses)
        if self.device_name == 'glasses' and 'euler' in self.device_data:
            euler = self.device_data['euler']
            orientation_text = f"Roll: {euler[0]:.1f}° Pitch: {euler[1]:.1f}° Yaw: {euler[2]:.1f}°"
            orientation_surface = self.font_manager.render_text(orientation_text, 'tiny', UIColors.TEXT_SECONDARY)
            orientation_rect = orientation_surface.get_rect(centerx=self.x + self.width//2, y=self.y + self.height - 40)
            self.screen.blit(orientation_surface, orientation_rect)
        
        # Gravity removal status for AR glasses
        if self.device_name == 'glasses':
            gravity_text = f"Gravity: {'Removed' if self.gravity_enabled else 'Included'}"
            gravity_color = UIColors.SUCCESS if self.gravity_enabled else UIColors.WARNING
            gravity_surface = self.font_manager.render_text(gravity_text, 'tiny', gravity_color)
            gravity_rect = gravity_surface.get_rect(centerx=self.x + self.width//2, y=self.y + self.height - 25)
            self.screen.blit(gravity_surface, gravity_rect)
        
        # Current sensor values
        if 'accelerometer' in self.device_data:
            accel = self.device_data['accelerometer']
            magnitude = np.linalg.norm(accel)
            accel_text = f"Accel: {magnitude:.2f} m/s²"
            accel_surface = self.font_manager.render_text(accel_text, 'tiny', UIColors.TEXT_SECONDARY)
            accel_rect = accel_surface.get_rect(x=self.x + 5, y=self.y + self.height - 15)
            self.screen.blit(accel_surface, accel_rect)
    
    def _draw_inactive_device(self):
        """Draw inactive device placeholder"""
        # Device name
        display_name = self.display_names.get(self.device_name, self.device_name.title())
        name_surface = self.font_manager.render_text(display_name, 'medium', UIColors.TEXT_INACTIVE)
        name_rect = name_surface.get_rect(center=(self.x + self.width//2, self.y + self.height//2 - 20))
        self.screen.blit(name_surface, name_rect)
        
        # Status message
        if self.device_name == 'glasses':
            status_text = "Run Unity app"
        else:
            status_text = "Waiting for connection..."
        
        status_surface = self.font_manager.render_text(status_text, 'small', UIColors.TEXT_INACTIVE)
        status_rect = status_surface.get_rect(center=(self.x + self.width//2, self.y + self.height//2 + 10))
        self.screen.blit(status_surface, status_rect)
        
        # Draw dashed border for inactive state
        self._draw_dashed_border()
    
    def _draw_dashed_border(self):
        """Draw dashed border for inactive devices"""
        dash_length = 10
        gap_length = 5
        color = UIColors.BORDER_INACTIVE
        
        # Top and bottom edges
        x = self.x
        while x < self.x + self.width:
            end_x = min(x + dash_length, self.x + self.width)
            pygame.draw.line(self.screen, color, (x, self.y), (end_x, self.y), 2)
            pygame.draw.line(self.screen, color, (x, self.y + self.height), (end_x, self.y + self.height), 2)
            x += dash_length + gap_length
        
        # Left and right edges
        y = self.y
        while y < self.y + self.height:
            end_y = min(y + dash_length, self.y + self.height)
            pygame.draw.line(self.screen, color, (self.x, y), (self.x, end_y), 2)
            pygame.draw.line(self.screen, color, (self.x + self.width, y), (self.x + self.width, end_y), 2)
            y += dash_length + gap_length
    
    def handle_mouse_event(self, event):
        """Handle mouse events for camera control"""
        if not self.use_opengl:
            return False
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_point_inside(event.pos):
                self.mouse_dragging = True
                self.last_mouse_pos = event.pos
                return True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            self.mouse_dragging = False
            self.last_mouse_pos = None
        
        elif event.type == pygame.MOUSEMOTION and self.mouse_dragging:
            if self.last_mouse_pos:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                
                # Update camera rotation
                self.camera_rotation_y += dx * 0.5
                self.camera_rotation_x -= dy * 0.5
                
                # Clamp X rotation
                self.camera_rotation_x = max(-89, min(89, self.camera_rotation_x))
                
                self.last_mouse_pos = event.pos
                return True
        
        elif event.type == pygame.MOUSEWHEEL:
            if self.is_point_inside(pygame.mouse.get_pos()):
                # Zoom in/out
                self.camera_distance *= (0.9 if event.y > 0 else 1.1)
                self.camera_distance = max(1.0, min(10.0, self.camera_distance))
                return True
        
        return False
    
    def is_point_inside(self, pos: Tuple[int, int]) -> bool:
        """Check if point is inside this panel"""
        x, y = pos
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)
    
    def reset_camera(self):
        """Reset camera to default position"""
        self.camera_rotation_x = 20.0
        self.camera_rotation_y = 45.0
        self.camera_distance = 3.0
    
    def get_device_name(self) -> str:
        """Get device name"""
        return self.device_name
    
    def get_display_name(self) -> str:
        """Get display name"""
        return self.display_names.get(self.device_name, self.device_name.title())
    
    def cleanup(self):
        """Clean up OpenGL resources"""
        if self.opengl_renderer:
            self.opengl_renderer.cleanup()
        
        if self.device_models:
            self.device_models.cleanup()
        
        if self.coordinate_system:
            self.coordinate_system.cleanup()
        
        logger.info(f"DevicePanel3D cleanup completed for {self.device_name}")


class DevicePanelManager:
    """Manages multiple device panels and their interactions"""
    
    def __init__(self, screen, font_manager, layout_config):
        self.screen = screen
        self.font_manager = font_manager
        self.layout_config = layout_config
        
        # Device panels
        self.panels = {}
        self.selected_panel = None
        
        # Create panels for all device types
        self._create_device_panels()
    
    def _create_device_panels(self):
        """Create device panels based on layout configuration"""
        device_names = ['phone', 'watch', 'headphone', 'glasses']
        
        for device_name in device_names:
            if device_name in self.layout_config:
                config = self.layout_config[device_name]
                
                self.panels[device_name] = DevicePanel3D(
                    screen=self.screen,
                    device_name=device_name,
                    x=config['x'],
                    y=config['y'],
                    width=config['width'],
                    height=config['height'],
                    font_manager=self.font_manager
                )
    
    def update_all(self, device_data_dict: Dict[str, Any], selected_device: Optional[str] = None):
        """Update all device panels with new data"""
        for device_name, panel in self.panels.items():
            device_data = device_data_dict.get(device_name)
            is_active = device_data is not None and device_data.get('is_active', False)
            is_selected = device_name == selected_device
            is_calibrated = device_data.get('is_calibrated', False) if device_data else False
            gravity_enabled = device_data.get('gravity_enabled', True) if device_data else True
            
            panel.update(device_data, is_active, is_selected, is_calibrated, gravity_enabled)
    
    def render_all(self):
        """Render all device panels"""
        for panel in self.panels.values():
            panel.render()
    
    def handle_mouse_event(self, event) -> Optional[str]:
        """Handle mouse events for all panels"""
        for device_name, panel in self.panels.items():
            if panel.handle_mouse_event(event):
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.selected_panel = device_name
                return device_name
        return None
    
    def get_panel(self, device_name: str) -> Optional[DevicePanel3D]:
        """Get specific device panel"""
        return self.panels.get(device_name)
    
    def get_selected_panel(self) -> Optional[str]:
        """Get currently selected panel"""
        return self.selected_panel
    
    def set_selected_panel(self, device_name: Optional[str]):
        """Set selected panel"""
        self.selected_panel = device_name
    
    def reset_all_cameras(self):
        """Reset camera positions for all panels"""
        for panel in self.panels.values():
            panel.reset_camera()
    
    def cleanup(self):
        """Clean up all panels"""
        for panel in self.panels.values():
            panel.cleanup()
        self.panels.clear()