"""
Sensor_UI/utils/fonts.py - Font management for the UI
"""

import pygame
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class FontManager:
    """Manages fonts for the UI application"""
    
    def __init__(self):
        self.fonts = {}
        self._font_cache = {}
        self._initialize_fonts()
    
    def _initialize_fonts(self):
        """Initialize all fonts used in the application"""
        try:
            # Define font sizes
            font_sizes = {
                'tiny': 12,
                'small': 14,
                'medium': 16,
                'large': 20,
                'xlarge': 24,
                'title': 32
            }
            
            # Try to load system fonts first
            system_fonts = [
                'Arial',
                'Helvetica',
                'DejaVu Sans',
                'Liberation Sans',
                'Segoe UI'
            ]
            
            selected_font = None
            for font_name in system_fonts:
                try:
                    test_font = pygame.font.SysFont(font_name, 16)
                    if test_font:
                        selected_font = font_name
                        logger.info(f"Using system font: {font_name}")
                        break
                except:
                    continue
            
            # Create fonts
            for size_name, size in font_sizes.items():
                try:
                    if selected_font:
                        self.fonts[size_name] = pygame.font.SysFont(selected_font, size)
                    else:
                        # Fall back to default font
                        self.fonts[size_name] = pygame.font.Font(None, size)
                except Exception as e:
                    logger.warning(f"Failed to create {size_name} font: {e}")
                    # Ultimate fallback
                    self.fonts[size_name] = pygame.font.Font(None, size)
            
            logger.info("FontManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize fonts: {e}")
            # Create minimal fallback fonts
            self._create_fallback_fonts()
    
    def _create_fallback_fonts(self):
        """Create fallback fonts if initialization fails"""
        fallback_sizes = {
            'tiny': 12,
            'small': 14,
            'medium': 16,
            'large': 20,
            'xlarge': 24,
            'title': 32
        }
        
        for size_name, size in fallback_sizes.items():
            self.fonts[size_name] = pygame.font.Font(None, size)
    
    def get_font(self, size: str = 'medium') -> pygame.font.Font:
        """Get font by size name"""
        return self.fonts.get(size, self.fonts.get('medium'))
    
    def render_text(self, text: str, size: str = 'medium', color: Tuple[int, int, int] = (255, 255, 255), 
                   antialias: bool = True, background: Tuple[int, int, int] = None) -> pygame.Surface:
        """
        Render text with specified font size and color
        
        Args:
            text: Text to render
            size: Font size name
            color: Text color (R, G, B)
            antialias: Enable antialiasing
            background: Background color (None for transparent)
            
        Returns:
            pygame.Surface with rendered text
        """
        try:
            # Create cache key
            cache_key = (text, size, color, antialias, background)
            
            # Check cache first
            if cache_key in self._font_cache:
                return self._font_cache[cache_key]
            
            font = self.get_font(size)
            
            if background:
                surface = font.render(text, antialias, color, background)
            else:
                surface = font.render(text, antialias, color)
            
            # Cache the result (limit cache size)
            if len(self._font_cache) < 1000:
                self._font_cache[cache_key] = surface
            
            return surface
            
        except Exception as e:
            logger.error(f"Error rendering text '{text}': {e}")
            # Return fallback surface
            fallback_font = pygame.font.Font(None, 16)
            return fallback_font.render(text, True, color)
    
    def get_text_size(self, text: str, size: str = 'medium') -> Tuple[int, int]:
        """
        Get the width and height of rendered text
        
        Args:
            text: Text to measure
            size: Font size name
            
        Returns:
            Tuple of (width, height)
        """
        try:
            font = self.get_font(size)
            return font.size(text)
        except Exception as e:
            logger.error(f"Error measuring text '{text}': {e}")
            return (100, 20)  # Fallback size
    
    def render_multiline_text(self, text: str, size: str = 'medium', 
                             color: Tuple[int, int, int] = (255, 255, 255),
                             max_width: int = None, line_spacing: int = 5) -> pygame.Surface:
        """
        Render multiline text
        
        Args:
            text: Text to render (use \\n for line breaks)
            size: Font size name
            color: Text color
            max_width: Maximum width before word wrapping
            line_spacing: Extra spacing between lines
            
        Returns:
            pygame.Surface with rendered multiline text
        """
        lines = text.split('\n')
        font = self.get_font(size)
        
        # Measure text
        line_surfaces = []
        max_line_width = 0
        line_height = font.get_height()
        
        for line in lines:
            if max_width and font.size(line)[0] > max_width:
                # Word wrap
                wrapped_lines = self._wrap_text(line, font, max_width)
                for wrapped_line in wrapped_lines:
                    surface = self.render_text(wrapped_line, size, color)
                    line_surfaces.append(surface)
                    max_line_width = max(max_line_width, surface.get_width())
            else:
                surface = self.render_text(line, size, color)
                line_surfaces.append(surface)
                max_line_width = max(max_line_width, surface.get_width())
        
        # Create combined surface
        total_height = len(line_surfaces) * line_height + (len(line_surfaces) - 1) * line_spacing
        combined_surface = pygame.Surface((max_line_width, total_height), pygame.SRCALPHA)
        
        # Blit all lines
        y_offset = 0
        for line_surface in line_surfaces:
            combined_surface.blit(line_surface, (0, y_offset))
            y_offset += line_height + line_spacing
        
        return combined_surface
    
    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> list:
        """Wrap text to fit within maximum width"""
        words = text.split(' ')
        lines = []
        current_line = ''
        
        for word in words:
            test_line = current_line + (' ' if current_line else '') + word
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def clear_cache(self):
        """Clear the font cache"""
        self._font_cache.clear()
    
    def get_available_sizes(self) -> list:
        """Get list of available font sizes"""
        return list(self.fonts.keys())