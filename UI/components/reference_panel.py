"""Reference coordinate system panel"""

import pygame
import numpy as np
from ..utils.colors import Colors
from ..utils.fonts import FontManager
from ..utils.renderer_3d import Renderer3D

class ReferencePanel:
    """Shows the reference coordinate system"""
    
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
        title = self.font_manager.render_text("Device Orientations", 'large', Colors.TEXT)
        self.screen.blit(title, (self.x + 20, self.y))
        
        subtitle = self.font_manager.render_text("Orthographic view", 'small', Colors.TEXT_SECONDARY)
        self.screen.blit(subtitle, (self.x + 20, self.y + 35))
        
        # Draw coordinate explanations
        self._draw_coordinate_explanations()
        
        # Draw reference coordinate system
        self._draw_reference_system()
    
    def _draw_coordinate_explanations(self):
        """Draw axis explanations on the left side"""
        explanations = [
            ("X-axis (Red):", "Right", Colors.AXIS_X),
            ("Y-axis (Green):", "Up", Colors.AXIS_Y),
            ("Z-axis (Blue):", "To user*", Colors.AXIS_Z)
        ]
        
        start_y = self.y + 70
        
        for i, (axis_name, direction, color) in enumerate(explanations):
            y_pos = start_y + i * 25
            
            # Axis name
            axis_text = self.font_manager.render_text(axis_name, 'small', color)
            self.screen.blit(axis_text, (self.x + 20, y_pos))
            
            # Direction explanation
            dir_text = self.font_manager.render_text(direction, 'small', Colors.TEXT_TERTIARY)
            self.screen.blit(dir_text, (self.x + 120, y_pos))
        
        # # Add note about glasses coordinate system
        # note_y = start_y + 80
        # note_text = self.font_manager.render_text("*AR Glasses: Z is backward", 'tiny', Colors.GLASSES)
        # self.screen.blit(note_text, (self.x + 20, note_y))
    
    def _draw_reference_system(self):
        """Draw the 3D reference coordinate system"""
        # Background circle
        pygame.draw.circle(self.screen, (30, 30, 40), self.ref_center, 55)
        pygame.draw.circle(self.screen, (100, 100, 120), self.ref_center, 55, 2)
        
        # Draw reference axes with simple arrows
        # Y is up in 3D space, but we need to flip for screen coordinates
        axes_directions = np.array([
            [1, 0, 0],    # X - Right (Red)
            [0, -1, 0],   # Y - Up (negative for screen Y)
            [0, 0, 1]     # Z - Toward user (Blue)
        ])
        
        axis_colors = [Colors.AXIS_X, Colors.AXIS_Y, Colors.AXIS_Z]
        axis_labels = ['X', 'Y', 'Z']
        
        for i, (direction, color, label) in enumerate(zip(axes_directions, axis_colors, axis_labels)):
            # Draw simple arrow
            self.renderer.draw_arrow(self.ref_center, direction, color, length=45)
            
            # Label positions
            label_pos = (
                self.ref_center[0] + direction[0] * 60,
                self.ref_center[1] + direction[1] * 60
            )
            label_text = self.font_manager.render_text(label, 'small', color)
            
            # Add background for better visibility
            label_bg = pygame.Surface((label_text.get_width() + 4, label_text.get_height() + 4))
            label_bg.fill((0, 0, 0))
            label_bg.set_alpha(128)
            
            self.screen.blit(label_bg, (label_pos[0] - 2, label_pos[1] - 2))
            self.screen.blit(label_text, label_pos)
        
        # Reference label
        ref_title = self.font_manager.render_text("Reference", 'small', Colors.TEXT)
        ref_title_rect = ref_title.get_rect(center=(self.ref_center[0], self.ref_center[1] + 70))
        self.screen.blit(ref_title, ref_title_rect)