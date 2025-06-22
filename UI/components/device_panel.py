"""Device panel component for 3D visualization with AR Glasses support"""

import pygame
import numpy as np
from scipy.spatial.transform import Rotation as R
from ..utils.colors import Colors
from ..utils.fonts import FontManager
from ..utils.renderer_3d import Renderer3D

class DevicePanel:
    """Individual device 3D visualization panel with AR Glasses support"""
    
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
    
    def draw(self, device_data=None, is_calibrated=False):
        """Draw the device panel"""
        if self.is_active and device_data:
            self._draw_active_device(device_data, is_calibrated)
        else:
            self._draw_inactive_device()
    
    def _draw_active_device(self, device_data, is_calibrated):
        """Draw active device with 3D visualization"""
        x, y, w, h = self.position_info['bounds']
        
        # Draw device name and info ABOVE the box
        status = "UNCAL" if not is_calibrated else ""
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
        pygame.draw.rect(self.screen, Colors.get_device_color(self.device_name), (x, y, w, h), 2)
        
        # Draw 3D device (adjust size based on device type and box size)
        if self.device_name == 'glasses':
            # AR Glasses - use appropriate scaling for horizontal glasses
            device_size = min(w, h) * 0.12  # Smaller base size for glasses proportions
        else:
            # Other devices
            device_size = self.size * 0.25
        
        device_center = (self.center[0], self.center[1])
        
        self._draw_3d_device(device_center, device_data['quaternion'], 
                           Colors.get_device_color(self.device_name), device_size)
        
        # Draw calibrate button at bottom of box
        if not is_calibrated:
            self._draw_calibrate_prompt(x, y, w, h)
    
    def _draw_3d_device(self, center, quaternion, color, device_size):
        """Draw 3D device representation"""
        # Get device vertices (now includes glasses shape)
        vertices = self.renderer.create_device_vertices(self.device_name, device_size)
        
        # Apply quaternion rotation
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
        
        # Draw coordinate axes (smaller for glasses)
        if self.device_name == 'glasses':
            axis_length = device_size * 0.6  # Shorter axes for glasses
        else:
            axis_length = device_size * 0.8
            
        axis_colors = [Colors.AXIS_X, Colors.AXIS_Y, Colors.AXIS_Z]
        self.renderer.draw_3d_axes(center, quaternion, axis_length, 
                                 axis_colors=axis_colors, 
                                 font_manager=self.font_manager)
    
    def _draw_inactive_device(self):
        """Draw inactive/waiting device"""
        x, y, w, h = self.position_info['bounds']
        
        # Draw dashed border
        dash_length = 10
        gap_length = 5
        color = Colors.WAITING
        
        # Top and bottom edges
        for i in range(0, w, dash_length + gap_length):
            end = min(i + dash_length, w)
            pygame.draw.line(self.screen, color, (x + i, y), (x + end, y), 2)
            pygame.draw.line(self.screen, color, (x + i, y + h), (x + end, y + h), 2)
        
        # Left and right edges
        for i in range(0, h, dash_length + gap_length):
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
    
    def _draw_calibrate_prompt(self, x, y, w, h):
        """Draw calibration prompt at bottom of active device box"""
        button_text = "CALIBRATE"
        button_surface = self.font_manager.render_text(button_text, 'tiny', Colors.UNCALIBRATED)
        button_rect = button_surface.get_rect(centerx=self.center[0], bottom=y + h - 5)
        self.screen.blit(button_surface, button_rect)