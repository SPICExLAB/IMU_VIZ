"""
Sensor_UI/rendering/opengl_renderer.py - OpenGL rendering engine
Core 3D rendering functionality with proper coordinate systems
"""

import numpy as np
import logging
import math
from typing import Tuple, List, Optional

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    import pygame
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

logger = logging.getLogger(__name__)


class OpenGLRenderer:
    """Core OpenGL rendering engine for 3D visualization"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.is_initialized = False
        
        if OPENGL_AVAILABLE:
            self._initialize_opengl()
        else:
            logger.warning("OpenGL not available")
    
    def _initialize_opengl(self):
        """Initialize OpenGL settings"""
        try:
            # Enable depth testing
            glEnable(GL_DEPTH_TEST)
            glDepthFunc(GL_LEQUAL)
            
            # Enable blending for transparency
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # Enable smooth shading
            glShadeModel(GL_SMOOTH)
            
            # Set clear color (transparent)
            glClearColor(0.0, 0.0, 0.0, 0.0)
            
            # Improve line quality
            glEnable(GL_LINE_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
            
            # Improve polygon quality
            glEnable(GL_POLYGON_SMOOTH)
            glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
            
            self.is_initialized = True
            logger.info("OpenGL renderer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenGL: {e}")
            self.is_initialized = False
    
    def setup_viewport(self, x: int, y: int, width: int, height: int):
        """Setup viewport for rendering in a specific area"""
        if not self.is_initialized:
            return
        
        glViewport(x, y, width, height)
        
        # Setup projection matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        
        aspect_ratio = width / height if height > 0 else 1.0
        gluPerspective(45.0, aspect_ratio, 0.1, 100.0)
        
        # Setup modelview matrix
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
    
    def setup_camera(self, distance: float, rotation_x: float, rotation_y: float):
        """Setup camera position and orientation"""
        if not self.is_initialized:
            return
        
        # Convert angles to radians
        rx = math.radians(rotation_x)
        ry = math.radians(rotation_y)
        
        # Calculate camera position
        camera_x = distance * math.sin(ry) * math.cos(rx)
        camera_y = distance * math.sin(rx)
        camera_z = distance * math.cos(ry) * math.cos(rx)
        
        # Set camera
        gluLookAt(camera_x, camera_y, camera_z,  # Camera position
                 0, 0, 0,                        # Look at origin
                 0, 1, 0)                        # Up vector
    
    def setup_lighting(self):
        """Setup OpenGL lighting"""
        if not self.is_initialized:
            return
        
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        
        # Light position (slightly above and to the right)
        light_pos = [2.0, 3.0, 2.0, 1.0]
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        
        # Ambient light (soft overall illumination)
        light_ambient = [0.3, 0.3, 0.3, 1.0]
        glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
        
        # Diffuse light (main directional light)
        light_diffuse = [0.8, 0.8, 0.8, 1.0]
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
        
        # Specular light (highlights)
        light_specular = [1.0, 1.0, 1.0, 1.0]
        glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)
        
        # Enable color material
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Material properties
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50.0)
    
    def disable_lighting(self):
        """Disable OpenGL lighting"""
        if not self.is_initialized:
            return
        
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
    
    def clear_depth_buffer(self, x: int, y: int, width: int, height: int):
        """Clear depth buffer for a specific area"""
        if not self.is_initialized:
            return
        
        glEnable(GL_SCISSOR_TEST)
        glScissor(x, y, width, height)
        glClear(GL_DEPTH_BUFFER_BIT)
        glDisable(GL_SCISSOR_TEST)
    
    def draw_cube(self, size: float = 1.0):
        """Draw a basic cube centered at origin"""
        if not self.is_initialized:
            return
        
        s = size / 2.0
        
        glBegin(GL_QUADS)
        
        # Front face
        glNormal3f(0.0, 0.0, 1.0)
        glVertex3f(-s, -s, s)
        glVertex3f(s, -s, s)
        glVertex3f(s, s, s)
        glVertex3f(-s, s, s)
        
        # Back face
        glNormal3f(0.0, 0.0, -1.0)
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, -s, -s)
        
        # Top face
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(-s, s, -s)
        glVertex3f(-s, s, s)
        glVertex3f(s, s, s)
        glVertex3f(s, s, -s)
        
        # Bottom face
        glNormal3f(0.0, -1.0, 0.0)
        glVertex3f(-s, -s, -s)
        glVertex3f(s, -s, -s)
        glVertex3f(s, -s, s)
        glVertex3f(-s, -s, s)
        
        # Right face
        glNormal3f(1.0, 0.0, 0.0)
        glVertex3f(s, -s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, s, s)
        glVertex3f(s, -s, s)
        
        # Left face
        glNormal3f(-1.0, 0.0, 0.0)
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, -s, s)
        glVertex3f(-s, s, s)
        glVertex3f(-s, s, -s)
        
        glEnd()
    
    def draw_sphere(self, radius: float = 1.0, slices: int = 16, stacks: int = 16):
        """Draw a sphere centered at origin"""
        if not self.is_initialized:
            return
        
        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluSphere(quadric, radius, slices, stacks)
        gluDeleteQuadric(quadric)
    
    def draw_cylinder(self, radius: float = 1.0, height: float = 2.0, slices: int = 16):
        """Draw a cylinder centered at origin"""
        if not self.is_initialized:
            return
        
        glPushMatrix()
        glTranslatef(0, -height/2, 0)
        
        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluCylinder(quadric, radius, radius, height, slices, 1)
        gluDeleteQuadric(quadric)
        
        glPopMatrix()
    
    def draw_line(self, start: Tuple[float, float, float], 
                  end: Tuple[float, float, float], thickness: float = 2.0):
        """Draw a 3D line between two points"""
        if not self.is_initialized:
            return
        
        glLineWidth(thickness)
        glBegin(GL_LINES)
        glVertex3f(*start)
        glVertex3f(*end)
        glEnd()
    
    def draw_arrow(self, start: Tuple[float, float, float], 
                   end: Tuple[float, float, float], 
                   arrow_size: float = 0.1, thickness: float = 3.0):
        """Draw a 3D arrow from start to end point"""
        if not self.is_initialized:
            return
        
        # Draw main line
        self.draw_line(start, end, thickness)
        
        # Calculate arrow direction
        direction = np.array(end) - np.array(start)
        length = np.linalg.norm(direction)
        
        if length < 1e-6:
            return
        
        direction = direction / length
        
        # Create arrowhead
        glPushMatrix()
        glTranslatef(*end)
        
        # Align with direction vector
        if abs(direction[1]) < 0.99:  # Avoid gimbal lock
            up = np.array([0, 1, 0])
        else:
            up = np.array([1, 0, 0])
        
        right = np.cross(direction, up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, direction)
        
        # Draw cone for arrowhead
        glBegin(GL_TRIANGLES)
        
        cone_base = np.array(end) - direction * arrow_size * 2
        cone_radius = arrow_size
        
        # Create cone vertices
        num_sides = 8
        for i in range(num_sides):
            angle1 = 2 * math.pi * i / num_sides
            angle2 = 2 * math.pi * (i + 1) / num_sides
            
            p1 = cone_base + cone_radius * (math.cos(angle1) * right + math.sin(angle1) * up)
            p2 = cone_base + cone_radius * (math.cos(angle2) * right + math.sin(angle2) * up)
            
            # Triangle from tip to base edge
            glVertex3f(0, 0, 0)  # Tip (translated to end point)
            glVertex3f(*(p1 - np.array(end)))
            glVertex3f(*(p2 - np.array(end)))
        
        glEnd()
        glPopMatrix()
    
    def set_color(self, color: Tuple[float, float, float], alpha: float = 1.0):
        """Set current rendering color"""
        if not self.is_initialized:
            return
        
        # Normalize color values if they're in 0-255 range
        if any(c > 1.0 for c in color):
            color = tuple(c / 255.0 for c in color)
        
        glColor4f(color[0], color[1], color[2], alpha)
    
    def push_matrix(self):
        """Push current transformation matrix"""
        if self.is_initialized:
            glPushMatrix()
    
    def pop_matrix(self):
        """Pop transformation matrix"""
        if self.is_initialized:
            glPopMatrix()
    
    def translate(self, x: float, y: float, z: float):
        """Apply translation"""
        if self.is_initialized:
            glTranslatef(x, y, z)
    
    def rotate(self, angle: float, x: float, y: float, z: float):
        """Apply rotation (angle in degrees)"""
        if self.is_initialized:
            glRotatef(angle, x, y, z)
    
    def scale(self, x: float, y: float, z: float):
        """Apply scaling"""
        if self.is_initialized:
            glScalef(x, y, z)
    
    def apply_rotation_matrix(self, rotation_matrix: np.ndarray):
        """Apply a 3x3 rotation matrix"""
        if not self.is_initialized or rotation_matrix.shape != (3, 3):
            return
        
        # Convert to OpenGL 4x4 matrix (column-major)
        gl_matrix = np.array([
            rotation_matrix[0, 0], rotation_matrix[1, 0], rotation_matrix[2, 0], 0,
            rotation_matrix[0, 1], rotation_matrix[1, 1], rotation_matrix[2, 1], 0,
            rotation_matrix[0, 2], rotation_matrix[1, 2], rotation_matrix[2, 2], 0,
            0, 0, 0, 1
        ], dtype=np.float32)
        
        glMultMatrixf(gl_matrix)
    
    def render_text_3d(self, text: str, position: Tuple[float, float, float], 
                       font_size: float = 0.1):
        """Render 3D text at given position (basic implementation)"""
        if not self.is_initialized:
            return
        
        # This is a placeholder - proper 3D text rendering would require
        # either bitmap fonts or vector font rendering
        glPushMatrix()
        glTranslatef(*position)
        glScalef(font_size, font_size, font_size)
        
        # Simple character rendering using lines (for demonstration)
        # In a full implementation, you'd use proper font rendering
        glBegin(GL_LINES)
        # Basic letter shapes could be drawn here
        glEnd()
        
        glPopMatrix()
    
    def get_opengl_info(self) -> dict:
        """Get OpenGL version and capability information"""
        if not self.is_initialized:
            return {"available": False}
        
        try:
            return {
                "available": True,
                "vendor": glGetString(GL_VENDOR).decode() if glGetString(GL_VENDOR) else "Unknown",
                "renderer": glGetString(GL_RENDERER).decode() if glGetString(GL_RENDERER) else "Unknown",
                "version": glGetString(GL_VERSION).decode() if glGetString(GL_VERSION) else "Unknown",
                "shading_language": glGetString(GL_SHADING_LANGUAGE_VERSION).decode() if glGetString(GL_SHADING_LANGUAGE_VERSION) else "Unknown"
            }
        except Exception as e:
            logger.error(f"Error getting OpenGL info: {e}")
            return {"available": True, "error": str(e)}
    
    def cleanup(self):
        """Clean up OpenGL resources"""
        if self.is_initialized:
            # Clean up any allocated resources
            self.is_initialized = False
            logger.info("OpenGL renderer cleaned up")


class RenderContext:
    """Context manager for OpenGL rendering operations"""
    
    def __init__(self, renderer: OpenGLRenderer, x: int, y: int, width: int, height: int):
        self.renderer = renderer
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def __enter__(self):
        if self.renderer.is_initialized:
            self.renderer.setup_viewport(self.x, self.y, self.width, self.height)
            self.renderer.clear_depth_buffer(self.x, self.y, self.width, self.height)
        return self.renderer
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Any cleanup needed after rendering
        pass


def create_rotation_matrix_from_quaternion(quaternion: np.ndarray) -> np.ndarray:
    """Convert quaternion [x, y, z, w] to 3x3 rotation matrix"""
    if len(quaternion) != 4:
        return np.eye(3)
    
    x, y, z, w = quaternion
    
    # Normalize quaternion
    norm = np.sqrt(x*x + y*y + z*z + w*w)
    if norm < 1e-8:
        return np.eye(3)
    
    x, y, z, w = x/norm, y/norm, z/norm, w/norm
    
    # Create rotation matrix
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - z*w), 2*(x*z + y*w)],
        [2*(x*y + z*w), 1 - 2*(x*x + z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x*x + y*y)]
    ])


def test_opengl_renderer():
    """Test OpenGL renderer functionality"""
    if not OPENGL_AVAILABLE:
        print("OpenGL not available for testing")
        return False
    
    try:
        # Initialize pygame for OpenGL context
        import pygame
        pygame.init()
        pygame.display.set_mode((800, 600), pygame.OPENGL | pygame.DOUBLEBUF)
        
        # Create renderer
        renderer = OpenGLRenderer(800, 600)
        
        if renderer.is_initialized:
            print("OpenGL renderer test passed")
            print("OpenGL info:", renderer.get_opengl_info())
            return True
        else:
            print("OpenGL renderer test failed - not initialized")
            return False
            
    except Exception as e:
        print(f"OpenGL renderer test failed: {e}")
        return False
    finally:
        pygame.quit()


if __name__ == "__main__":
    test_opengl_renderer()