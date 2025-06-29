"""3D rendering utilities with consistent coordinate systems and calibration visualization"""

import numpy as np
import pygame
import math
from scipy.spatial.transform import Rotation as R
import logging

logger = logging.getLogger(__name__)

class Renderer3D:
    """Handles 3D rendering operations with calibration-aware coordinate handling"""
    
    # Device 3D scales (for different shapes)
    DEVICE_SCALES = {
        'phone': (0.4, 1.0, 0.08),      # iPhone: thin rectangle
        'headphone': (0.25, 0.25, 0.25),   # AirPods: smaller cube
        'watch': (0.8, 0.8, 0.3),       # Watch: square with depth
        'glasses': (1.5, 0.5, 0.1)      # AR Glasses: wide horizontal
    }
    
    def __init__(self, screen):
        self.screen = screen
    
    def orthographic_project(self, point_3d: np.ndarray, center: tuple, scale: float = 1.0) -> tuple:
        """Orthographic projection (no perspective distortion)"""
        x, y, z = point_3d
        
        # Simple orthographic projection - just ignore Z for projection
        screen_x = int(center[0] + x * scale)
        screen_y = int(center[1] - y * scale)  # Flip Y for screen coordinates
        
        return screen_x, screen_y
    
    def create_device_vertices(self, device_type: str, size: float):
        """Create device-specific 3D vertices"""
        scale_x, scale_y, scale_z = self.DEVICE_SCALES.get(device_type, (0.5, 0.5, 0.5))
        
        # Special handling for glasses to create a proper glasses shape
        if device_type == 'glasses':
            # Create AR glasses shape with correct proportions
            vertices = np.array([
                # Bottom face (glasses frame bottom)
                [-scale_x, -scale_y, -scale_z],    # 0: left-bottom-back
                [scale_x, -scale_y, -scale_z],     # 1: right-bottom-back  
                [scale_x, -scale_y, scale_z],      # 2: right-bottom-front
                [-scale_x, -scale_y, scale_z],     # 3: left-bottom-front
                # Top face (glasses frame top)
                [-scale_x, scale_y, -scale_z],     # 4: left-top-back
                [scale_x, scale_y, -scale_z],      # 5: right-top-back
                [scale_x, scale_y, scale_z],       # 6: right-top-front
                [-scale_x, scale_y, scale_z]       # 7: left-top-front
            ]) * size
        else:
            # Standard rectangular device
            vertices = np.array([
                # Bottom face
                [-scale_x, -scale_y, -scale_z],
                [scale_x, -scale_y, -scale_z],
                [scale_x, scale_y, -scale_z],
                [-scale_x, scale_y, -scale_z],
                # Top face  
                [-scale_x, -scale_y, scale_z],
                [scale_x, -scale_y, scale_z],
                [scale_x, scale_y, scale_z],
                [-scale_x, scale_y, scale_z]
            ]) * size
        
        return vertices
    
    def calculate_face_normal(self, vertices: np.ndarray, face: list) -> np.ndarray:
        """Calculate face normal for lighting"""
        if len(face) < 3:
            return np.array([0, 0, 1])
        
        # Get three points of the face
        p1, p2, p3 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
        
        # Calculate normal using cross product
        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2)
        
        # Normalize
        norm = np.linalg.norm(normal)
        if norm > 0:
            normal = normal / norm
        
        return normal
    
    def draw_arrow(self, center: tuple, direction: np.ndarray, color: tuple, length: float = 30):
        """Draw simple line arrow"""
        # Normalize direction
        if np.linalg.norm(direction) == 0:
            return
        
        direction = direction / np.linalg.norm(direction)
        
        # Calculate end point
        end_x = center[0] + direction[0] * length
        end_y = center[1] + direction[1] * length
        end_point = (end_x, end_y)
        
        # Draw main line
        pygame.draw.line(self.screen, color, center, end_point, 3)
        
        # Draw arrowhead
        # Calculate perpendicular vector for arrowhead
        perp = np.array([-direction[1], direction[0], 0])  # 2D perpendicular
        
        # Arrowhead size
        arrow_size = 8
        
        # Calculate arrowhead points
        arrow_back = np.array([
            end_x - direction[0] * arrow_size,
            end_y - direction[1] * arrow_size
        ])
        
        # Two sides of arrowhead
        arrow_left = arrow_back + perp[:2] * arrow_size * 0.5
        arrow_right = arrow_back - perp[:2] * arrow_size * 0.5
        
        # Draw arrowhead
        pygame.draw.line(self.screen, color, end_point, tuple(arrow_left.astype(int)), 3)
        pygame.draw.line(self.screen, color, end_point, tuple(arrow_right.astype(int)), 3)
    
    def draw_3d_axes(self, center, quaternion, axis_length=40, 
                axes_directions=None, axis_colors=None, 
                font_manager=None, device_type='phone', 
                is_calibrated=False, is_reference=False):
        """
        Draw 3D coordinate axes with consistent device-specific coordinate systems.
        
        This properly handles the global reference frame vs device local frames.
        """
        # Use provided colors or defaults
        if axis_colors is None:
            axis_colors = [(255, 60, 60), (60, 255, 60), (60, 60, 255)]  # R, G, B
        
        # If axes directions are provided, use them directly
        if axes_directions is not None:
            pass  # Use the pre-rotated directions
        # Otherwise, define initial axes based on device type
        else:
            if device_type == 'global':
                # Global reference frame always has fixed axes:
                # X pointing left, Y pointing up, Z pointing forward (into screen)
                axes_directions = np.array([
                    [-1, 0, 0],   # X-axis (Red) - Left
                    [0, 1, 0],    # Y-axis (Green) - Up
                    [0, 0, -1]    # Z-axis (Blue) - Forward (into screen)
                ])
            elif device_type == 'headphone':
                # For headphones, use the world frame axes
                # The quaternion is already transformed to world frame in preprocessing
                axes_directions = np.array([
                    [-1, 0, 0],   # X-axis (Red) - Left
                    [0, 1, 0],    # Y-axis (Green) - Up
                    [0, 0, -1]    # Z-axis (Blue) - Forward (into screen)
                ])
            else:
                # For phone/watch, use their native coordinate systems
                if device_type == 'phone' or device_type == 'watch':
                    # Phone/Watch: X-right, Y-up, Z-toward user
                    axes_directions = np.array([
                        [1, 0, 0],    # X-axis (Red) - Right
                        [0, 1, 0],    # Y-axis (Green) - Up
                        [0, 0, 1]     # Z-axis (Blue) - Toward user
                    ])
                    # IMPORTANT: For calibrated reference devices, show axes in global frame
                    # This ensures the visualization matches the physical orientation
                    if is_calibrated and is_reference:
                        y_flip = R.from_euler('y', 180, degrees=True)
                        axes_directions = y_flip.apply(axes_directions)
                elif device_type == 'glasses':
                    # AR Glasses: X-right, Y-up, Z-forward
                    axes_directions = np.array([
                        [1, 0, 0],    # X-axis (Red) - Right
                        [0, 1, 0],    # Y-axis (Green) - Up
                        [0, 0, -1]    # Z-axis (Blue) - Forward (into screen)
                    ])
                else:
                    # Default to standard right-handed system
                    axes_directions = np.array([
                        [1, 0, 0],    # X-axis (Red)
                        [0, 1, 0],    # Y-axis (Green)
                        [0, 0, 1]     # Z-axis (Blue)
                    ])
        
        # Apply quaternion rotation to the axes
        # For headphones, this quaternion is already in world frame
        # For other devices (except global), apply the rotation
        if device_type != 'global' and quaternion is not None and np.linalg.norm(quaternion) > 0:
            try:
                rotation = R.from_quat(quaternion)
                # Apply rotation to the axes
                axes_directions = rotation.apply(axes_directions)
            except Exception as e:
                logger.error(f"Error rotating axes: {e}")
        
        # Get axis labels
        axis_labels = ['X', 'Y', 'Z']
        
        # Draw arrows
        for i, (direction, color, label) in enumerate(zip(axes_directions, axis_colors, axis_labels)):
            # For Y axis, flip the screen direction
            screen_direction = direction.copy()
            screen_direction[1] = -screen_direction[1]  # Flip Y for screen coordinates
            
            # Draw arrow
            self.draw_arrow(center, screen_direction, color, length=axis_length)
            
            # Draw label if font_manager provided
            if font_manager:
                # Calculate label position
                label_pos = (
                    center[0] + screen_direction[0] * (axis_length + 15),
                    center[1] + screen_direction[1] * (axis_length + 15)
                )
                
                label_text = font_manager.render_text(label, 'small', color)
                
                label_bg = pygame.Surface((label_text.get_width() + 4, label_text.get_height() + 4))
                label_bg.fill((0, 0, 0))
                label_bg.set_alpha(128)
                
                self.screen.blit(label_bg, (label_pos[0] - 2, label_pos[1] - 2))
                self.screen.blit(label_text, label_pos)