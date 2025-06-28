"""Device panel component with enhanced calibration indicators"""

import pygame
import numpy as np
from scipy.spatial.transform import Rotation as R
from ..utils.colors import Colors
from ..utils.fonts import FontManager
from ..utils.renderer_3d import Renderer3D

class DevicePanel:
    """Individual device 3D visualization panel with enhanced calibration indicators"""
    
    def __init__(self, screen, device_name, position_info):
        self.screen = screen
        self.device_name = device_name
        self.position_info = position_info
        self.center = position_info['center']
        self.size = position_info['size']
        self.is_active = position_info['active']
        
        self.renderer = Renderer3D(screen)
        self.font_manager = FontManager()
        
        # Device display names
        self.display_names = {
            'phone': 'Phone',
            'headphone': 'AirPods', 
            'watch': 'Watch',
            'glasses': 'AR Glasses'
        }
        
        # Gravity toggle button for glasses (will be set when drawing)
        self.gravity_button_rect = None
    
    def draw(self, device_data=None, is_calibrated=False, gravity_enabled=True):
        """Draw the device panel with optional gravity toggle"""
        if self.is_active and device_data:
            self._draw_active_device(device_data, is_calibrated, gravity_enabled)
        else:
            self._draw_inactive_device()
    
    def _draw_active_device(self, device_data, is_calibrated, gravity_enabled):
        """Draw active device with 3D visualization"""
        x, y, w, h = self.position_info['bounds']
        
        # Draw device name and info ABOVE the box
        status = "UNCAL" if not is_calibrated else "CAL"
        freq_text = f" @ {device_data['frequency']:.1f}Hz" if device_data['frequency'] > 0 else ""
        title_text = f"{status} {self.display_names[self.device_name].upper()}"
        
        # Title above box
        title_color = Colors.CALIBRATED if is_calibrated else Colors.UNCALIBRATED
        title_surface = self.font_manager.render_text(title_text, 'medium', title_color)
        title_rect = title_surface.get_rect(centerx=self.center[0], bottom=y - 5)
        self.screen.blit(title_surface, title_rect)
        
        # Sample info above box
        info_text = f"{device_data['sample_count']} samples{freq_text}"
        info_surface = self.font_manager.render_text(info_text, 'small', Colors.TEXT_SECONDARY)
        info_rect = info_surface.get_rect(centerx=self.center[0], bottom=y - 25)
        self.screen.blit(info_surface, info_rect)
        
        # Draw box background
        pygame.draw.rect(self.screen, Colors.PANEL, (x, y, w, h))
        
        # Draw border with different color based on calibration status
        border_color = Colors.CALIBRATED if is_calibrated else Colors.get_device_color(self.device_name)
        pygame.draw.rect(self.screen, border_color, (x, y, w, h), 2)
        
        # Draw calibration indicator
        if is_calibrated:
            self._draw_calibration_indicator(x, y, w, h)
        
        # Draw gravity toggle button for AR glasses
        if self.device_name == 'glasses':
            self._draw_gravity_toggle_button(x, y, w, h, gravity_enabled)
        
        # Draw 3D device (adjust size based on device type and box size)
        if self.device_name == 'glasses':
            # AR Glasses - use appropriate scaling for horizontal glasses
            device_size = min(w, h) * 0.15  # Slightly larger for better visibility
        else:
            # Other devices
            device_size = self.size * 0.25
        
        device_center = (self.center[0], self.center[1])
        
        # Draw device coordinate system info
        if self.device_name == 'phone' or self.device_name == 'watch':
            frame_text = "X:right, Y:up, Z:backward"
        elif self.device_name == 'headphone':
            frame_text = "X:right, Z:up, Y:forward"
        elif self.device_name == 'glasses':
            frame_text = "X:right, Y:up, Z:forward"
        else:
            frame_text = "Device coordinates"
            
        frame_surface = self.font_manager.render_text(frame_text, 'tiny', Colors.TEXT_SECONDARY)
        frame_rect = frame_surface.get_rect(centerx=self.center[0], y=y + 5)
        self.screen.blit(frame_surface, frame_rect)
        
        # Draw calibration status message
        if is_calibrated:
            cal_text = "Showing rotation relative to calibration"
        else:
            cal_text = "Showing absolute orientation"
            
        cal_surface = self.font_manager.render_text(cal_text, 'tiny', title_color)
        cal_rect = cal_surface.get_rect(centerx=self.center[0], y=y + 20)
        self.screen.blit(cal_surface, cal_rect)
        
        # Draw the 3D device with its axes
        self._draw_3d_device(device_center, device_data['quaternion'], 
                           Colors.get_device_color(self.device_name), device_size)
        
        # Draw additional info for glasses
        if self.device_name == 'glasses':
            self._draw_glasses_info(device_data, x, y, w, h, gravity_enabled)
        
        # Draw calibration prompt if not calibrated
        if not is_calibrated:
            self._draw_calibrate_prompt(x, y, w, h)
    
    def _draw_calibration_indicator(self, x, y, w, h):
        """Draw calibration status indicator"""
        # Draw a small indicator in the corner to show device is calibrated
        indicator_size = 12
        indicator_margin = 8
        
        # Draw in top-left corner
        indicator_rect = pygame.Rect(
            x + indicator_margin, 
            y + indicator_margin, 
            indicator_size, 
            indicator_size
        )
        
        # Draw indicator
        pygame.draw.rect(self.screen, Colors.CALIBRATED, indicator_rect)
        pygame.draw.rect(self.screen, Colors.TEXT, indicator_rect, 1)
        
        # Draw checkmark
        checkmark_points = [
            (x + indicator_margin + 2, y + indicator_margin + 6),
            (x + indicator_margin + 5, y + indicator_margin + 9),
            (x + indicator_margin + 10, y + indicator_margin + 3)
        ]
        pygame.draw.lines(self.screen, Colors.TEXT, False, checkmark_points, 2)
    
    def _draw_gravity_toggle_button(self, x, y, w, h, gravity_enabled):
        """Draw gravity toggle button in bottom right corner of glasses panel"""
        button_size = 30
        button_margin = 5
        button_x = x + w - button_size - button_margin
        button_y = y + h - button_size - button_margin
        
        # Store button rect for click detection
        self.gravity_button_rect = pygame.Rect(button_x, button_y, button_size, button_size)
        
        # Button colors based on state
        if gravity_enabled:
            button_color = (100, 200, 100)  # Green when gravity removal enabled
            text_color = (0, 0, 0)
            button_text = "G"
        else:
            button_color = (200, 100, 100)  # Red when gravity removal disabled
            text_color = (255, 255, 255)
            button_text = "G"
        
        # Draw button background
        pygame.draw.rect(self.screen, button_color, self.gravity_button_rect)
        pygame.draw.rect(self.screen, Colors.TEXT, self.gravity_button_rect, 2)
        
        # Draw button text
        text_surface = self.font_manager.render_text(button_text, 'small', text_color)
        text_rect = text_surface.get_rect(center=self.gravity_button_rect.center)
        self.screen.blit(text_surface, text_rect)
        
        # Tooltip text near button
        tooltip_text = "Remove gravity" if gravity_enabled else "Include gravity"
        tooltip_surface = self.font_manager.render_text(tooltip_text, 'tiny', Colors.TEXT_TERTIARY)
        tooltip_x = button_x - tooltip_surface.get_width() - 10
        tooltip_y = button_y + (button_size - tooltip_surface.get_height()) // 2
        self.screen.blit(tooltip_surface, (tooltip_x, tooltip_y))
    
    def _draw_3d_device(self, center, quaternion, color, device_size):
        """Draw 3D device representation with device-specific coordinate handling"""
        # Get device vertices
        vertices = self.renderer.create_device_vertices(self.device_name, device_size)
        
        # Apply quaternion rotation DIRECTLY - no transformations
        if quaternion is not None and np.linalg.norm(quaternion) > 0:
            try:
                rotation = R.from_quat(quaternion)
                vertices = rotation.apply(vertices)
            except Exception:
                pass
        
        # Project to 2D
        projected = [self.renderer.orthographic_project(vertex, center, scale=1.5) 
                    for vertex in vertices]
        
        # Define faces
        faces = [
            [0, 1, 2, 3],  # Bottom face
            [4, 7, 6, 5],  # Top face
            [0, 4, 5, 1],  # Front face
            [2, 6, 7, 3],  # Back face
            [0, 3, 7, 4],  # Left face
            [1, 5, 6, 2]   # Right face
        ]
        
        # Calculate face depths for proper ordering
        face_depths = []
        for i, face in enumerate(faces):
            face_center = np.mean([vertices[j] for j in face], axis=0)
            depth = face_center[2]
            face_depths.append((depth, i, face))
        
        # Sort faces by depth (back to front)
        face_depths.sort(key=lambda x: x[0])
        
        # Draw faces
        for depth, face_idx, face in face_depths:
            face_points = [projected[j] for j in face]
            
            # Calculate face color based on lighting
            face_normal = self.renderer.calculate_face_normal(vertices, face)
            light_intensity = max(0.3, abs(face_normal[2]))
            
            face_color = tuple(int(c * light_intensity) for c in color)
            
            try:
                pygame.draw.polygon(self.screen, face_color, face_points)
                pygame.draw.polygon(self.screen, tuple(min(255, c + 40) for c in face_color), 
                                face_points, 2)
            except:
                # Fallback to wireframe
                for i in range(len(face)):
                    start = face_points[i]
                    end = face_points[(i + 1) % len(face)]
                    pygame.draw.line(self.screen, color, start, end, 2)
        
        # Draw coordinate axes with device-specific handling
        if self.device_name == 'glasses':
            axis_length = device_size * 0.5  # Appropriate for glasses
        else:
            axis_length = device_size * 0.8
            
        axis_colors = [Colors.AXIS_X, Colors.AXIS_Y, Colors.AXIS_Z]
        # PASS DEVICE TYPE TO RENDERER
        self.renderer.draw_3d_axes(center, quaternion, axis_length, 
                                axis_colors=axis_colors, 
                                font_manager=self.font_manager,
                                device_type=self.device_name)
    
    def _draw_glasses_info(self, device_data, x, y, w, h, gravity_enabled):
        """Draw additional info specific to AR glasses"""
        # Show gravity removal status
        gravity_status = "Gravity: Removed" if gravity_enabled else "Gravity: Included"
        gravity_color = (100, 200, 100) if gravity_enabled else (200, 100, 100)
        gravity_surface = self.font_manager.render_text(gravity_status, 'tiny', gravity_color)
        gravity_rect = gravity_surface.get_rect(centerx=x + w//2, y=y + 40)
        self.screen.blit(gravity_surface, gravity_rect)
        
        if 'euler' in device_data and device_data['euler'] is not None:
            euler = device_data['euler']
            nod, tilt, turn = euler[0], euler[1], euler[2]
            
            # Show head movement info at bottom of box (above the button)
            info_y = y + h - 65  # Higher to make room for button
            
            # NOD (up/down) - X rotation in your coordinate system
            nod_text = f"NOD: {nod:+5.1f}°"
            nod_color = Colors.AXIS_X if abs(nod) > 5 else Colors.TEXT_TERTIARY
            nod_surface = self.font_manager.render_text(nod_text, 'tiny', nod_color)
            self.screen.blit(nod_surface, (x + 5, info_y))

            # TURN (left/right rotation) - Y rotation
            turn_text = f"TURN: {turn:+5.1f}°"
            turn_color = Colors.AXIS_Y if abs(turn) > 5 else Colors.TEXT_TERTIARY
            turn_surface = self.font_manager.render_text(turn_text, 'tiny', turn_color)
            self.screen.blit(turn_surface, (x + 5, info_y + 12))
            
            # TILT (left/right) - Z rotation
            tilt_text = f"TILT: {tilt:+5.1f}°"
            tilt_color = Colors.AXIS_Z if abs(tilt) > 5 else Colors.TEXT_TERTIARY
            tilt_surface = self.font_manager.render_text(tilt_text, 'tiny', tilt_color)
            self.screen.blit(tilt_surface, (x + 5, info_y + 24))
    
    def _draw_inactive_device(self):
        """Draw inactive/waiting device"""
        x, y, w, h = self.position_info['bounds']
        
        # Draw dashed border
        dash_length = 10
        gap_length = 5
        color = Colors.WAITING
        
        # Top and bottom edges
        for i in range(0, int(w), dash_length + gap_length):
            end = min(i + dash_length, w)
            pygame.draw.line(self.screen, color, (x + i, y), (x + end, y), 2)
            pygame.draw.line(self.screen, color, (x + i, y + h), (x + end, y + h), 2)
        
        # Left and right edges
        for i in range(0, int(h), dash_length + gap_length):
            end = min(i + dash_length, h)
            pygame.draw.line(self.screen, color, (x, y + i), (x, y + end), 2)
            pygame.draw.line(self.screen, color, (x + w, y + i), (x + w, y + end), 2)
        
        # Device name
        text = self.font_manager.render_text(self.display_names[self.device_name], 'small', color)
        text_rect = text.get_rect(center=self.center)
        self.screen.blit(text, text_rect)
        
        # Status - special message for AR glasses
        if self.device_name == 'glasses':
            status_text = self.font_manager.render_text("Run Unity app on glasses", 'tiny', color)
        else:
            status_text = self.font_manager.render_text("Waiting for data...", 'tiny', color)
        
        status_rect = status_text.get_rect(centerx=self.center[0], y=self.center[1] + 15)
        self.screen.blit(status_text, status_rect)
    
    def handle_click(self, pos):
        """Handle click events on the device panel"""
        # Check gravity toggle button for glasses
        if (self.device_name == 'glasses' and 
            self.gravity_button_rect and 
            self.gravity_button_rect.collidepoint(pos)):
            return 'toggle_gravity'
        
        return None
    
    def _draw_calibrate_prompt(self, x, y, w, h):
        """Draw calibration prompt at bottom of active device box"""
        button_text = "Press CALIBRATE to set reference orientation"
        button_surface = self.font_manager.render_text(button_text, 'tiny', Colors.UNCALIBRATED)
        button_rect = button_surface.get_rect(centerx=self.center[0], bottom=y + h - 5)
        self.screen.blit(button_surface, button_rect)