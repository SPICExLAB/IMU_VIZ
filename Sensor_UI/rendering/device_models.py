"""
Sensor_UI/rendering/device_models.py - 3D device models
Device-specific 3D models with proper proportions and visual differentiation
"""

import numpy as np
import logging
import math
from typing import Dict, List, Tuple

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

logger = logging.getLogger(__name__)


class DeviceModels:
    """3D models for different device types"""
    
    def __init__(self):
        self.models = {}
        self._initialize_models()
        logger.info("DeviceModels initialized")
    
    def _initialize_models(self):
        """Initialize 3D models for all device types"""
        self.models = {
            'phone': PhoneModel(),
            'watch': WatchModel(),
            'headphone': HeadphoneModel(),
            'glasses': GlassesModel()
        }
    
    def draw_device(self, device_type: str, scale: float = 1.0):
        """
        Draw 3D model for specified device type
        
        Args:
            device_type: Type of device to draw
            scale: Scale factor for the model
        """
        if not OPENGL_AVAILABLE:
            return
        
        if device_type in self.models:
            glPushMatrix()
            glScalef(scale, scale, scale)
            self.models[device_type].draw()
            glPopMatrix()
        else:
            logger.warning(f"Unknown device type: {device_type}")
            self._draw_fallback_cube(scale)
    
    def _draw_fallback_cube(self, scale: float = 1.0):
        """Draw a simple cube as fallback"""
        glPushMatrix()
        glScalef(scale, scale, scale)
        
        size = 0.5
        glBegin(GL_QUADS)
        
        # Define cube faces with normals
        faces = [
            # Front face
            ([ size, -size,  size], [ size,  size,  size], [-size,  size,  size], [-size, -size,  size], [0, 0, 1]),
            # Back face  
            ([-size, -size, -size], [-size,  size, -size], [ size,  size, -size], [ size, -size, -size], [0, 0, -1]),
            # Top face
            ([-size,  size, -size], [-size,  size,  size], [ size,  size,  size], [ size,  size, -size], [0, 1, 0]),
            # Bottom face
            ([ size, -size, -size], [ size, -size,  size], [-size, -size,  size], [-size, -size, -size], [0, -1, 0]),
            # Right face
            ([ size, -size, -size], [ size,  size, -size], [ size,  size,  size], [ size, -size,  size], [1, 0, 0]),
            # Left face
            ([-size, -size,  size], [-size,  size,  size], [-size,  size, -size], [-size, -size, -size], [-1, 0, 0])
        ]
        
        for face in faces:
            glNormal3f(*face[4])  # Set normal
            for vertex in face[:4]:  # Draw vertices
                glVertex3f(*vertex)
        
        glEnd()
        glPopMatrix()
    
    def get_device_bounds(self, device_type: str) -> Tuple[float, float, float]:
        """
        Get bounding box dimensions for device type
        
        Returns:
            Tuple of (width, height, depth)
        """
        if device_type in self.models:
            return self.models[device_type].get_bounds()
        return (1.0, 1.0, 1.0)  # Default cube bounds
    
    def cleanup(self):
        """Clean up device models"""
        for model in self.models.values():
            if hasattr(model, 'cleanup'):
                model.cleanup()
        logger.info("DeviceModels cleaned up")


class BaseDeviceModel:
    """Base class for device 3D models"""
    
    def __init__(self, width: float, height: float, depth: float):
        self.width = width
        self.height = height
        self.depth = depth
    
    def draw(self):
        """Draw the device model - to be implemented by subclasses"""
        raise NotImplementedError
    
    def get_bounds(self) -> Tuple[float, float, float]:
        """Get model bounding box"""
        return (self.width, self.height, self.depth)
    
    def draw_rounded_rect(self, width: float, height: float, depth: float, 
                         corner_radius: float = 0.05):
        """Draw a rounded rectangular prism"""
        # Simplified rounded rect - draw main body + corner cylinders
        
        # Main body (slightly smaller to accommodate rounded corners)
        w, h, d = width - 2*corner_radius, height - 2*corner_radius, depth
        
        glBegin(GL_QUADS)
        
        # Front and back faces
        glNormal3f(0, 0, 1)
        glVertex3f(-w/2, -h/2, d/2)
        glVertex3f(w/2, -h/2, d/2)
        glVertex3f(w/2, h/2, d/2)
        glVertex3f(-w/2, h/2, d/2)
        
        glNormal3f(0, 0, -1)
        glVertex3f(-w/2, -h/2, -d/2)
        glVertex3f(-w/2, h/2, -d/2)
        glVertex3f(w/2, h/2, -d/2)
        glVertex3f(w/2, -h/2, -d/2)
        
        # Top and bottom faces
        glNormal3f(0, 1, 0)
        glVertex3f(-w/2, h/2, -d/2)
        glVertex3f(-w/2, h/2, d/2)
        glVertex3f(w/2, h/2, d/2)
        glVertex3f(w/2, h/2, -d/2)
        
        glNormal3f(0, -1, 0)
        glVertex3f(-w/2, -h/2, -d/2)
        glVertex3f(w/2, -h/2, -d/2)
        glVertex3f(w/2, -h/2, d/2)
        glVertex3f(-w/2, -h/2, d/2)
        
        # Left and right faces
        glNormal3f(1, 0, 0)
        glVertex3f(w/2, -h/2, -d/2)
        glVertex3f(w/2, h/2, -d/2)
        glVertex3f(w/2, h/2, d/2)
        glVertex3f(w/2, -h/2, d/2)
        
        glNormal3f(-1, 0, 0)
        glVertex3f(-w/2, -h/2, -d/2)
        glVertex3f(-w/2, -h/2, d/2)
        glVertex3f(-w/2, h/2, d/2)
        glVertex3f(-w/2, h/2, -d/2)
        
        glEnd()


class PhoneModel(BaseDeviceModel):
    """iPhone 3D model"""
    
    def __init__(self):
        # iPhone proportions (approximately)
        super().__init__(width=0.8, height=1.6, depth=0.1)
        self.corner_radius = 0.05
        self.screen_border = 0.05
    
    def draw(self):
        """Draw iPhone model"""
        # Main body
        self.draw_rounded_rect(self.width, self.height, self.depth, self.corner_radius)
        
        # Screen (darker area on front)
        glPushMatrix()
        glTranslatef(0, 0, self.depth/2 + 0.001)  # Slightly forward
        
        # Darker color for screen
        current_color = glGetFloatv(GL_CURRENT_COLOR)
        glColor4f(current_color[0] * 0.3, current_color[1] * 0.3, current_color[2] * 0.3, current_color[3])
        
        screen_w = self.width - 2 * self.screen_border
        screen_h = self.height - 2 * self.screen_border
        
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glVertex3f(-screen_w/2, -screen_h/2, 0)
        glVertex3f(screen_w/2, -screen_h/2, 0)
        glVertex3f(screen_w/2, screen_h/2, 0)
        glVertex3f(-screen_w/2, screen_h/2, 0)
        glEnd()
        
        # Restore color
        glColor4f(*current_color)
        
        # Home button (small circle at bottom)
        glTranslatef(0, -self.height/2 + 0.15, 0.001)
        quadric = gluNewQuadric()
        gluDisk(quadric, 0, 0.03, 16, 1)
        gluDeleteQuadric(quadric)
        
        glPopMatrix()
        
        # Camera (small circle at top back)
        glPushMatrix()
        glTranslatef(0.2, self.height/2 - 0.15, -self.depth/2 - 0.001)
        quadric = gluNewQuadric()
        gluDisk(quadric, 0, 0.02, 12, 1)
        gluDeleteQuadric(quadric)
        glPopMatrix()


class WatchModel(BaseDeviceModel):
    """Apple Watch 3D model"""
    
    def __init__(self):
        # Apple Watch proportions
        super().__init__(width=0.9, height=0.9, depth=0.25)
        self.corner_radius = 0.1
        self.crown_radius = 0.03
        self.crown_height = 0.05
    
    def draw(self):
        """Draw Apple Watch model"""
        # Main body (square with rounded corners)
        self.draw_rounded_rect(self.width, self.height, self.depth, self.corner_radius)
        
        # Screen (on top face)
        glPushMatrix()
        glTranslatef(0, 0, self.depth/2 + 0.001)
        
        # Darker screen color
        current_color = glGetFloatv(GL_CURRENT_COLOR)
        glColor4f(current_color[0] * 0.2, current_color[1] * 0.2, current_color[2] * 0.2, current_color[3])
        
        screen_size = 0.7
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glVertex3f(-screen_size/2, -screen_size/2, 0)
        glVertex3f(screen_size/2, -screen_size/2, 0)
        glVertex3f(screen_size/2, screen_size/2, 0)
        glVertex3f(-screen_size/2, screen_size/2, 0)
        glEnd()
        
        # Restore color
        glColor4f(*current_color)
        glPopMatrix()
        
        # Digital Crown (on right side)
        glPushMatrix()
        glTranslatef(self.width/2 + self.crown_height/2, 0.2, 0)
        glRotatef(90, 0, 1, 0)  # Orient cylinder horizontally
        
        quadric = gluNewQuadric()
        gluCylinder(quadric, self.crown_radius, self.crown_radius, self.crown_height, 12, 1)
        gluDeleteQuadric(quadric)
        glPopMatrix()
        
        # Side button (smaller cylinder below crown)
        glPushMatrix()
        glTranslatef(self.width/2 + self.crown_height/2, -0.1, 0)
        glRotatef(90, 0, 1, 0)
        
        quadric = gluNewQuadric()
        gluCylinder(quadric, self.crown_radius * 0.7, self.crown_radius * 0.7, self.crown_height, 8, 1)
        gluDeleteQuadric(quadric)
        glPopMatrix()


class HeadphoneModel(BaseDeviceModel):
    """AirPods/Headphone 3D model"""
    
    def __init__(self):
        # AirPods case proportions
        super().__init__(width=0.6, height=0.45, depth=0.25)
        self.corner_radius = 0.08
    
    def draw(self):
        """Draw AirPods case model"""
        # Main case body
        self.draw_rounded_rect(self.width, self.height, self.depth, self.corner_radius)
        
        # Lid line (indicating opening)
        glPushMatrix()
        glTranslatef(0, 0, self.depth/2 + 0.001)
        
        # Darker line color
        current_color = glGetFloatv(GL_CURRENT_COLOR)
        glColor4f(current_color[0] * 0.5, current_color[1] * 0.5, current_color[2] * 0.5, current_color[3])
        
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glVertex3f(-self.width/2 + 0.05, 0, 0)
        glVertex3f(self.width/2 - 0.05, 0, 0)
        glEnd()
        
        # Restore color
        glColor4f(*current_color)
        glPopMatrix()
        
        # LED indicator (small dot)
        glPushMatrix()
        glTranslatef(0, -self.height/2 + 0.08, self.depth/2 + 0.001)
        
        # Bright color for LED
        glColor4f(0.2, 1.0, 0.2, 1.0)  # Green LED
        
        quadric = gluNewQuadric()
        gluDisk(quadric, 0, 0.01, 8, 1)
        gluDeleteQuadric(quadric)
        
        # Restore color
        glColor4f(*current_color)
        glPopMatrix()


class GlassesModel(BaseDeviceModel):
    """AR Glasses 3D model"""
    
    def __init__(self):
        # AR glasses proportions
        super().__init__(width=1.4, height=0.5, depth=0.15)
        self.lens_radius = 0.2
        self.bridge_width = 0.15
        self.temple_length = 0.8
        self.temple_width = 0.03
    
    def draw(self):
        """Draw AR glasses model"""
        # Left lens
        self._draw_lens(-self.lens_radius - self.bridge_width/2, 0, 0)
        
        # Right lens
        self._draw_lens(self.lens_radius + self.bridge_width/2, 0, 0)
        
        # Bridge (connecting the lenses)
        self._draw_bridge()
        
        # Left temple
        self._draw_temple(-self.lens_radius - self.bridge_width/2, 0, 0, -1)
        
        # Right temple
        self._draw_temple(self.lens_radius + self.bridge_width/2, 0, 0, 1)
        
        # Nose pads
        self._draw_nose_pads()
    
    def _draw_lens(self, x: float, y: float, z: float):
        """Draw a single lens"""
        glPushMatrix()
        glTranslatef(x, y, z)
        
        # Lens frame (torus for rim)
        glPushMatrix()
        self._draw_torus(self.lens_radius * 0.9, self.lens_radius, 12, 24)
        glPopMatrix()
        
        # Lens surface (transparent disk)
        current_color = glGetFloatv(GL_CURRENT_COLOR)
        glColor4f(current_color[0] * 0.3, current_color[1] * 0.3, current_color[2] * 0.7, 0.3)  # Blue tint
        
        quadric = gluNewQuadric()
        gluDisk(quadric, 0, self.lens_radius * 0.9, 24, 1)
        gluDeleteQuadric(quadric)
        
        # Restore color
        glColor4f(*current_color)
        
        glPopMatrix()
    
    def _draw_bridge(self):
        """Draw the bridge connecting the lenses"""
        glPushMatrix()
        glTranslatef(0, 0, 0)
        
        # Bridge as a small cylinder
        glRotatef(90, 0, 1, 0)
        quadric = gluNewQuadric()
        gluCylinder(quadric, 0.015, 0.015, self.bridge_width, 8, 1)
        gluDeleteQuadric(quadric)
        
        glPopMatrix()
    
    def _draw_temple(self, start_x: float, start_y: float, start_z: float, direction: int):
        """Draw a temple arm"""
        glPushMatrix()
        glTranslatef(start_x, start_y, start_z)
        
        # Temple arm as cylinder
        glRotatef(90 * direction, 0, 1, 0)
        quadric = gluNewQuadric()
        gluCylinder(quadric, self.temple_width, self.temple_width, self.temple_length, 8, 1)
        gluDeleteQuadric(quadric)
        
        # Temple tip (slightly thicker)
        glTranslatef(0, 0, self.temple_length)
        gluCylinder(quadric, self.temple_width * 1.2, self.temple_width * 1.2, 0.05, 8, 1)
        gluDeleteQuadric(quadric)
        
        glPopMatrix()
    
    def _draw_nose_pads(self):
        """Draw nose pads"""
        pad_offset = 0.08
        
        # Left nose pad
        glPushMatrix()
        glTranslatef(-pad_offset, -0.15, 0.02)
        glScalef(0.5, 0.5, 0.5)
        quadric = gluNewQuadric()
        gluSphere(quadric, 0.02, 8, 8)
        gluDeleteQuadric(quadric)
        glPopMatrix()
        
        # Right nose pad
        glPushMatrix()
        glTranslatef(pad_offset, -0.15, 0.02)
        glScalef(0.5, 0.5, 0.5)
        quadric = gluNewQuadric()
        gluSphere(quadric, 0.02, 8, 8)
        gluDeleteQuadric(quadric)
        glPopMatrix()
    
    def _draw_torus(self, inner_radius: float, outer_radius: float, 
                   sides: int, rings: int):
        """Draw a torus (doughnut shape) for lens rim"""
        for i in range(rings):
            theta1 = i * 2.0 * math.pi / rings
            theta2 = (i + 1) * 2.0 * math.pi / rings
            
            glBegin(GL_QUAD_STRIP)
            
            for j in range(sides + 1):
                phi = j * 2.0 * math.pi / sides
                
                # First ring
                cos_theta1, sin_theta1 = math.cos(theta1), math.sin(theta1)
                cos_phi, sin_phi = math.cos(phi), math.sin(phi)
                
                x1 = cos_theta1 * (outer_radius + inner_radius * cos_phi)
                y1 = sin_theta1 * (outer_radius + inner_radius * cos_phi)
                z1 = inner_radius * sin_phi
                
                nx1 = cos_theta1 * cos_phi
                ny1 = sin_theta1 * cos_phi
                nz1 = sin_phi
                
                glNormal3f(nx1, ny1, nz1)
                glVertex3f(x1, y1, z1)
                
                # Second ring
                cos_theta2, sin_theta2 = math.cos(theta2), math.sin(theta2)
                
                x2 = cos_theta2 * (outer_radius + inner_radius * cos_phi)
                y2 = sin_theta2 * (outer_radius + inner_radius * cos_phi)
                z2 = inner_radius * sin_phi
                
                nx2 = cos_theta2 * cos_phi
                ny2 = sin_theta2 * cos_phi
                nz2 = sin_phi
                
                glNormal3f(nx2, ny2, nz2)
                glVertex3f(x2, y2, z2)
            
            glEnd()


class DeviceAnimator:
    """Handles device model animations and state changes"""
    
    def __init__(self):
        self.animations = {}
        self.animation_time = 0.0
        
    def update(self, delta_time: float):
        """Update animations"""
        self.animation_time += delta_time
        
        # Clean up finished animations
        finished = [name for name, anim in self.animations.items() if anim.is_finished()]
        for name in finished:
            del self.animations[name]
    
    def add_pulse_animation(self, device_name: str, duration: float = 2.0):
        """Add pulsing animation for device connection"""
        self.animations[f"{device_name}_pulse"] = PulseAnimation(duration)
    
    def add_rotation_animation(self, device_name: str, axis: str = 'y', speed: float = 30.0):
        """Add rotation animation"""
        self.animations[f"{device_name}_rotate"] = RotationAnimation(axis, speed)
    
    def get_scale_factor(self, device_name: str) -> float:
        """Get current scale factor for device"""
        pulse_anim = self.animations.get(f"{device_name}_pulse")
        if pulse_anim:
            return pulse_anim.get_scale(self.animation_time)
        return 1.0
    
    def get_rotation_angle(self, device_name: str) -> Tuple[float, str]:
        """Get current rotation angle and axis for device"""
        rotate_anim = self.animations.get(f"{device_name}_rotate")
        if rotate_anim:
            return rotate_anim.get_angle(self.animation_time), rotate_anim.axis
        return 0.0, 'y'


class PulseAnimation:
    """Pulsing scale animation"""
    
    def __init__(self, duration: float):
        self.duration = duration
        self.start_time = None
    
    def get_scale(self, current_time: float) -> float:
        if self.start_time is None:
            self.start_time = current_time
        
        elapsed = current_time - self.start_time
        if elapsed >= self.duration:
            return 1.0
        
        # Sine wave pulse
        progress = elapsed / self.duration
        pulse = 1.0 + 0.1 * math.sin(progress * 4 * math.pi)
        return pulse
    
    def is_finished(self) -> bool:
        return False  # Pulse continues indefinitely


class RotationAnimation:
    """Continuous rotation animation"""
    
    def __init__(self, axis: str, speed: float):
        self.axis = axis
        self.speed = speed  # degrees per second
        self.start_time = None
    
    def get_angle(self, current_time: float) -> float:
        if self.start_time is None:
            self.start_time = current_time
        
        elapsed = current_time - self.start_time
        return (elapsed * self.speed) % 360.0
    
    def is_finished(self) -> bool:
        return False  # Rotation continues indefinitely


class DeviceVisualEffects:
    """Visual effects for device models"""
    
    def __init__(self):
        self.effects = {}
    
    def add_connection_effect(self, device_name: str):
        """Add visual effect when device connects"""
        # Green glow effect
        self.effects[f"{device_name}_connect"] = {
            'type': 'glow',
            'color': (0.2, 1.0, 0.2, 0.8),
            'duration': 2.0,
            'start_time': None
        }
    
    def add_calibration_effect(self, device_name: str):
        """Add visual effect during calibration"""
        # Blue pulse effect
        self.effects[f"{device_name}_calibrate"] = {
            'type': 'pulse',
            'color': (0.2, 0.2, 1.0, 0.6),
            'duration': 3.0,
            'start_time': None
        }
    
    def add_error_effect(self, device_name: str):
        """Add visual effect for errors"""
        # Red flash effect
        self.effects[f"{device_name}_error"] = {
            'type': 'flash',
            'color': (1.0, 0.2, 0.2, 0.9),
            'duration': 1.0,
            'start_time': None
        }
    
    def update_and_render_effects(self, current_time: float):
        """Update and render all active effects"""
        finished_effects = []
        
        for effect_name, effect in self.effects.items():
            if effect['start_time'] is None:
                effect['start_time'] = current_time
            
            elapsed = current_time - effect['start_time']
            
            if elapsed >= effect['duration']:
                finished_effects.append(effect_name)
                continue
            
            # Render effect based on type
            if effect['type'] == 'glow':
                self._render_glow_effect(effect, elapsed)
            elif effect['type'] == 'pulse':
                self._render_pulse_effect(effect, elapsed)
            elif effect['type'] == 'flash':
                self._render_flash_effect(effect, elapsed)
        
        # Clean up finished effects
        for effect_name in finished_effects:
            del self.effects[effect_name]
    
    def _render_glow_effect(self, effect: dict, elapsed: float):
        """Render glow effect around device"""
        progress = elapsed / effect['duration']
        alpha = effect['color'][3] * (1.0 - progress)  # Fade out
        
        glEnable(GL_BLEND)
        glColor4f(effect['color'][0], effect['color'][1], effect['color'][2], alpha)
        
        # Draw enlarged wireframe
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glLineWidth(3.0)
        glPushMatrix()
        scale = 1.0 + 0.2 * (1.0 - progress)
        glScalef(scale, scale, scale)
        
        # Draw simple wireframe cube
        size = 0.6
        glBegin(GL_LINE_LOOP)
        glVertex3f(-size, -size, size)
        glVertex3f(size, -size, size)
        glVertex3f(size, size, size)
        glVertex3f(-size, size, size)
        glEnd()
        
        glPopMatrix()
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glDisable(GL_BLEND)
    
    def _render_pulse_effect(self, effect: dict, elapsed: float):
        """Render pulsing effect"""
        progress = elapsed / effect['duration']
        pulse = 0.5 + 0.5 * math.sin(progress * 8 * math.pi)
        alpha = effect['color'][3] * pulse
        
        glEnable(GL_BLEND)
        glColor4f(effect['color'][0], effect['color'][1], effect['color'][2], alpha)
        
        # Draw pulsing outline
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glLineWidth(2.0 + pulse * 2.0)
        
        # Simple outline shape
        size = 0.5
        glBegin(GL_LINE_LOOP)
        glVertex3f(-size, -size, 0)
        glVertex3f(size, -size, 0)
        glVertex3f(size, size, 0)
        glVertex3f(-size, size, 0)
        glEnd()
        
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glDisable(GL_BLEND)
    
    def _render_flash_effect(self, effect: dict, elapsed: float):
        """Render flash effect"""
        progress = elapsed / effect['duration']
        
        # Quick flash that fades out
        if progress < 0.1:
            alpha = effect['color'][3]
        else:
            alpha = effect['color'][3] * (1.0 - (progress - 0.1) / 0.9)
        
        glEnable(GL_BLEND)
        glColor4f(effect['color'][0], effect['color'][1], effect['color'][2], alpha)
        
        # Draw flash overlay
        glPushMatrix()
        glScalef(1.1, 1.1, 1.1)
        
        # Simple flash quad
        glBegin(GL_QUADS)
        glVertex3f(-0.6, -0.6, 0)
        glVertex3f(0.6, -0.6, 0)
        glVertex3f(0.6, 0.6, 0)
        glVertex3f(-0.6, 0.6, 0)
        glEnd()
        
        glPopMatrix()
        glDisable(GL_BLEND)


def test_device_models():
    """Test device models functionality"""
    if not OPENGL_AVAILABLE:
        print("OpenGL not available for testing device models")
        return False
    
    try:
        # Initialize pygame for OpenGL context
        import pygame
        pygame.init()
        pygame.display.set_mode((800, 600), pygame.OPENGL | pygame.DOUBLEBUF)
        
        # Create device models
        models = DeviceModels()
        
        print("Device models initialized successfully")
        print("Available models:", list(models.models.keys()))
        
        # Test bounds
        for device_type in models.models.keys():
            bounds = models.get_device_bounds(device_type)
            print(f"{device_type} bounds: {bounds}")
        
        return True
        
    except Exception as e:
        print(f"Device models test failed: {e}")
        return False
    finally:
        pygame.quit()


if __name__ == "__main__":
    test_device_models()