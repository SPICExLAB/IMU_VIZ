"""Reference coordinate system panel showing global frame with identity quaternion"""

import pygame
import numpy as np
from scipy.spatial.transform import Rotation as R
from ..utils.colors import Colors
from ..utils.fonts import FontManager
from ..utils.renderer_3d import Renderer3D

class ReferencePanel:
    """Shows the global coordinate system using identity quaternion"""
    
    def __init__(self, screen, x, y, width, height):
        self.screen = screen
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        self.font_manager = FontManager()
        self.renderer = Renderer3D(screen)
        
        # Center of the reference visualization
        self.ref_center = (self.x + self.width - 120, self.y + 50)
    
    def draw(self):
        """Draw the reference panel"""
        # Title
        title = self.font_manager.render_text("Global Coordinate System", 'large', Colors.TEXT)
        self.screen.blit(title, (self.x + 20, self.y))
        
        # Draw coordinate explanations
        self._draw_coordinate_explanations()
        
        # Draw reference coordinate system
        self._draw_reference_system()
    
    def _draw_coordinate_explanations(self):
        """Draw axis explanations on the left side"""
        explanations = [
            ("X-axis (Red):", "LEFT", Colors.AXIS_X),
            ("Y-axis (Green):", "UP", Colors.AXIS_Y),
            ("Z-axis (Blue):", "FORWARD", Colors.AXIS_Z)
        ]
        
        start_y = self.y + 50
        
        for i, (axis_name, direction, color) in enumerate(explanations):
            y_pos = start_y + i * 25
            
            # Axis name
            axis_text = self.font_manager.render_text(axis_name, 'small', color)
            self.screen.blit(axis_text, (self.x + 20, y_pos))
            
            # Direction explanation
            dir_text = self.font_manager.render_text(direction, 'small', Colors.TEXT_TERTIARY)
            self.screen.blit(dir_text, (self.x + 120, y_pos))
    
    def _draw_reference_system(self):
        """Draw the 3D reference coordinate system"""
        # Background circle
        pygame.draw.circle(self.screen, (30, 30, 40), self.ref_center, 55)
        pygame.draw.circle(self.screen, (100, 100, 120), self.ref_center, 55, 2)
        
        # Use identity quaternion (no rotation) for the global frame
        global_quat = np.array([0, 0, 0, 1])  # Identity quaternion [x, y, z, w]
        
        # Use the 3D renderer with the global frame type
        axis_colors = [Colors.AXIS_X, Colors.AXIS_Y, Colors.AXIS_Z]
        self.renderer.draw_3d_axes(
            self.ref_center, 
            global_quat,
            axis_length=45, 
            axis_colors=axis_colors, 
            font_manager=self.font_manager,
            device_type='global'  # Special device type for global frame
        )
        
        # Reference label
        ref_title = self.font_manager.render_text("X:left, Y:up, Z:forward", 'small', Colors.TEXT)
        ref_title_rect = ref_title.get_rect(center=(self.ref_center[0], self.ref_center[1] + 70))
        self.screen.blit(ref_title, ref_title_rect)