"""
Sensor_UI/rendering/coordinate_system.py - Coordinate system management
Proper coordinate transformations and axis visualization
"""

import numpy as np
import logging
import math
from typing import Tuple, Optional
from scipy.spatial.transform import Rotation as R

try:
    from OpenGL.GL import *
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

logger = logging.getLogger(__name__)


class CoordinateSystem:
    """Manages coordinate system transformations and visualization"""
    
    def __init__(self):
        self.global_frame = np.eye(3)  # Global reference frame (identity)
        
        # Standard colors for axes (RGB)
        self.axis_colors = {
            'x': (1.0, 0.2, 0.2),  # Red for X-axis
            'y': (0.2, 1.0, 0.2),  # Green for Y-axis  
            'z': (0.2, 0.2, 1.0)   # Blue for Z-axis
        }
        
        # Coordinate system convention: Right-hand rule
        # X: Right (positive X points right)
        # Y: Up (positive Y points up)
        # Z: Forward (positive Z points toward viewer/out of screen)
        
        logger.info("CoordinateSystem initialized with right-hand convention")
    
    def draw_axes_3d(self, rotation_matrix: np.ndarray, length: float = 1.5, 
                     thickness: float = 3.0, show_labels: bool = True):
        """
        Draw 3D coordinate axes with proper orientations
        
        Args:
            rotation_matrix: 3x3 rotation matrix representing device orientation
            length: Length of each axis
            thickness: Line thickness for axes
            show_labels: Whether to show axis labels
        """
        if not OPENGL_AVAILABLE:
            return
        
        # Define unit vectors for each axis
        axes = {
            'x': np.array([1, 0, 0]),
            'y': np.array([0, 1, 0]), 
            'z': np.array([0, 0, 1])
        }
        
        # Apply rotation to each axis
        rotated_axes = {}
        for axis_name, axis_vector in axes.items():
            rotated_axes[axis_name] = rotation_matrix @ axis_vector
        
        # Draw each axis
        glDisable(GL_LIGHTING)  # Draw axes without lighting for clarity
        
        for axis_name, rotated_vector in rotated_axes.items():
            color = self.axis_colors[axis_name]
            glColor3f(*color)
            
            # Draw axis line
            end_point = rotated_vector * length
            self._draw_axis_arrow((0, 0, 0), end_point, thickness)
            
            # Draw axis label if requested
            if show_labels:
                label_position = end_point * 1.2
                self._draw_axis_label(axis_name.upper(), label_position)
        
        glEnable(GL_LIGHTING)
    
    def _draw_axis_arrow(self, start: Tuple[float, float, float], 
                        end: np.ndarray, thickness: float):
        """Draw an arrow representing a coordinate axis"""
        # Draw main line
        glLineWidth(thickness)
        glBegin(GL_LINES)
        glVertex3f(*start)
        glVertex3f(*end)
        glEnd()
        
        # Draw arrowhead
        arrow_length = 0.2
        arrow_width = 0.1
        
        # Calculate direction and perpendicular vectors
        direction = end / np.linalg.norm(end)
        
        # Find perpendicular vectors for arrowhead
        if abs(direction[1]) < 0.9:
            perp1 = np.cross(direction, [0, 1, 0])
        else:
            perp1 = np.cross(direction, [1, 0, 0])
        
        perp1 = perp1 / np.linalg.norm(perp1)
        perp2 = np.cross(direction, perp1)
        
        # Arrowhead base point
        base = end - direction * arrow_length
        
        # Arrowhead vertices
        v1 = base + perp1 * arrow_width
        v2 = base - perp1 * arrow_width
        v3 = base + perp2 * arrow_width
        v4 = base - perp2 * arrow_width
        
        # Draw arrowhead triangles
        glBegin(GL_TRIANGLES)
        
        # Side 1
        glVertex3f(*end)
        glVertex3f(*v1)
        glVertex3f(*v3)
        
        # Side 2
        glVertex3f(*end)
        glVertex3f(*v3)
        glVertex3f(*v2)
        
        # Side 3
        glVertex3f(*end)
        glVertex3f(*v2)
        glVertex3f(*v4)
        
        # Side 4
        glVertex3f(*end)
        glVertex3f(*v4)
        glVertex3f(*v1)
        
        glEnd()
    
    def _draw_axis_label(self, label: str, position: np.ndarray):
        """Draw text label for coordinate axis"""
        # For now, draw a small cube as placeholder for text
        # In a full implementation, this would render actual text
        glPushMatrix()
        glTranslatef(*position)
        
        # Small cube to represent label
        size = 0.05
        glBegin(GL_QUADS)
        
        # Simple cube faces (abbreviated for space)
        s = size
        vertices = [
            [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s],  # Front
            [-s, -s, -s], [-s, s, -s], [s, s, -s], [s, -s, -s],  # Back
        ]
        
        # Front face
        for vertex in vertices[:4]:
            glVertex3f(*vertex)
        
        glEnd()
        glPopMatrix()
    
    def transform_vector_to_global(self, vector: np.ndarray, 
                                  device_rotation: np.ndarray) -> np.ndarray:
        """
        Transform a vector from device coordinate system to global frame
        
        Args:
            vector: Vector in device coordinate system
            device_rotation: Device rotation matrix (3x3)
            
        Returns:
            Vector in global coordinate system
        """
        return device_rotation @ vector
    
    def transform_vector_to_device(self, vector: np.ndarray, 
                                  device_rotation: np.ndarray) -> np.ndarray:
        """
        Transform a vector from global coordinate system to device frame
        
        Args:
            vector: Vector in global coordinate system
            device_rotation: Device rotation matrix (3x3)
            
        Returns:
            Vector in device coordinate system
        """
        return device_rotation.T @ vector
    
    def calculate_relative_rotation(self, rotation1: np.ndarray, 
                                  rotation2: np.ndarray) -> np.ndarray:
        """
        Calculate relative rotation between two orientations
        
        Args:
            rotation1: First rotation matrix (3x3)
            rotation2: Second rotation matrix (3x3)
            
        Returns:
            Relative rotation matrix from rotation1 to rotation2
        """
        return rotation2 @ rotation1.T
    
    def quaternion_to_rotation_matrix(self, quaternion: np.ndarray) -> np.ndarray:
        """
        Convert quaternion [x, y, z, w] to rotation matrix
        
        Args:
            quaternion: Quaternion array [x, y, z, w]
            
        Returns:
            3x3 rotation matrix
        """
        if len(quaternion) != 4:
            logger.warning("Invalid quaternion length")
            return np.eye(3)
        
        try:
            # Use scipy for robust conversion
            rotation = R.from_quat(quaternion)
            return rotation.as_matrix()
        except Exception as e:
            logger.error(f"Error converting quaternion to matrix: {e}")
            return np.eye(3)
    
    def rotation_matrix_to_quaternion(self, rotation_matrix: np.ndarray) -> np.ndarray:
        """
        Convert rotation matrix to quaternion [x, y, z, w]
        
        Args:
            rotation_matrix: 3x3 rotation matrix
            
        Returns:
            Quaternion array [x, y, z, w]
        """
        if rotation_matrix.shape != (3, 3):
            logger.warning("Invalid rotation matrix shape")
            return np.array([0, 0, 0, 1])
        
        try:
            rotation = R.from_matrix(rotation_matrix)
            return rotation.as_quat()
        except Exception as e:
            logger.error(f"Error converting matrix to quaternion: {e}")
            return np.array([0, 0, 0, 1])
    
    def euler_to_rotation_matrix(self, euler_angles: np.ndarray, 
                                sequence: str = 'xyz') -> np.ndarray:
        """
        Convert Euler angles to rotation matrix
        
        Args:
            euler_angles: Euler angles in radians [roll, pitch, yaw]
            sequence: Rotation sequence (default: 'xyz')
            
        Returns:
            3x3 rotation matrix
        """
        try:
            rotation = R.from_euler(sequence, euler_angles)
            return rotation.as_matrix()
        except Exception as e:
            logger.error(f"Error converting Euler to matrix: {e}")
            return np.eye(3)
    
    def rotation_matrix_to_euler(self, rotation_matrix: np.ndarray, 
                                sequence: str = 'xyz') -> np.ndarray:
        """
        Convert rotation matrix to Euler angles
        
        Args:
            rotation_matrix: 3x3 rotation matrix
            sequence: Rotation sequence (default: 'xyz')
            
        Returns:
            Euler angles in radians [roll, pitch, yaw]
        """
        try:
            rotation = R.from_matrix(rotation_matrix)
            return rotation.as_euler(sequence)
        except Exception as e:
            logger.error(f"Error converting matrix to Euler: {e}")
            return np.array([0, 0, 0])
    
    def normalize_rotation_matrix(self, rotation_matrix: np.ndarray) -> np.ndarray:
        """
        Normalize rotation matrix to ensure orthogonality
        
        Args:
            rotation_matrix: Potentially non-orthogonal 3x3 matrix
            
        Returns:
            Orthogonal rotation matrix
        """
        try:
            # Use SVD to find closest orthogonal matrix
            U, _, Vt = np.linalg.svd(rotation_matrix)
            
            # Ensure proper rotation (det = 1, not reflection)
            if np.linalg.det(U @ Vt) < 0:
                Vt[-1, :] *= -1
            
            return U @ Vt
        except Exception as e:
            logger.error(f"Error normalizing rotation matrix: {e}")
            return np.eye(3)
    
    def apply_device_specific_transform(self, quaternion: np.ndarray, 
                                      device_type: str) -> np.ndarray:
        """
        Apply device-specific coordinate transformations
        
        Args:
            quaternion: Device quaternion [x, y, z, w]
            device_type: Type of device ('phone', 'watch', 'headphone', 'glasses')
            
        Returns:
            Transformed rotation matrix
        """
        # Convert quaternion to rotation matrix
        rotation_matrix = self.quaternion_to_rotation_matrix(quaternion)
        
        # Device-specific coordinate frame adjustments
        if device_type == 'phone':
            # iPhone coordinate system typically matches global frame
            # No additional transformation needed
            pass
        
        elif device_type == 'watch':
            # Apple Watch may need rotation based on wrist orientation
            # Typically worn with screen facing up
            pass
        
        elif device_type == 'headphone':
            # AirPods coordinate system adjustments
            # May need transformation from ear-relative to head-relative coordinates
            pass
        
        elif device_type == 'glasses':
            # AR Glasses coordinate system
            # Transform from glasses frame to head frame
            # Glasses frame: typically X:right, Y:forward, Z:up (when worn)
            # Global frame: X:right, Y:up, Z:forward
            
            # Rotation to align glasses frame with global frame
            glasses_to_global = np.array([
                [1,  0,  0],  # X stays the same (right)
                [0,  0,  1],  # Y becomes Z (forward -> up)
                [0, -1,  0]   # Z becomes -Y (up -> forward)
            ])
            
            rotation_matrix = glasses_to_global @ rotation_matrix
        
        return rotation_matrix
    
    def get_alignment_error(self, rotation1: np.ndarray, 
                           rotation2: np.ndarray) -> float:
        """
        Calculate alignment error between two rotations in degrees
        
        Args:
            rotation1: First rotation matrix
            rotation2: Second rotation matrix
            
        Returns:
            Alignment error in degrees
        """
        try:
            # Calculate relative rotation
            relative_rotation = self.calculate_relative_rotation(rotation1, rotation2)
            
            # Convert to angle-axis representation
            rotation = R.from_matrix(relative_rotation)
            rotvec = rotation.as_rotvec()
            
            # Calculate rotation angle
            angle_rad = np.linalg.norm(rotvec)
            angle_deg = np.degrees(angle_rad)
            
            return angle_deg
        except Exception as e:
            logger.error(f"Error calculating alignment error: {e}")
            return 0.0
    
    def create_reference_frame(self, reference_quaternion: np.ndarray) -> np.ndarray:
        """
        Create reference frame from a reference device orientation
        
        Args:
            reference_quaternion: Quaternion of reference device [x, y, z, w]
            
        Returns:
            Reference frame rotation matrix
        """
        return self.quaternion_to_rotation_matrix(reference_quaternion)
    
    def align_to_reference(self, device_quaternion: np.ndarray, 
                          reference_frame: np.ndarray) -> np.ndarray:
        """
        Align device orientation to reference frame
        
        Args:
            device_quaternion: Device quaternion [x, y, z, w]
            reference_frame: Reference frame rotation matrix
            
        Returns:
            Aligned rotation matrix
        """
        device_rotation = self.quaternion_to_rotation_matrix(device_quaternion)
        
        # Calculate alignment transformation
        alignment_transform = reference_frame.T @ device_rotation
        
        return alignment_transform
    
    def draw_reference_frame(self, length: float = 2.0, alpha: float = 0.5):
        """
        Draw the global reference coordinate system
        
        Args:
            length: Length of reference axes
            alpha: Transparency of reference axes
        """
        if not OPENGL_AVAILABLE:
            return
        
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        
        # Draw reference axes with transparency
        for axis_name, axis_vector in [('x', [1, 0, 0]), ('y', [0, 1, 0]), ('z', [0, 0, 1])]:
            color = self.axis_colors[axis_name]
            glColor4f(color[0], color[1], color[2], alpha)
            
            # Draw dashed line for reference
            self._draw_dashed_line((0, 0, 0), np.array(axis_vector) * length)
        
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
    
    def _draw_dashed_line(self, start: Tuple[float, float, float], 
                         end: np.ndarray, dash_length: float = 0.1):
        """Draw a dashed line"""
        direction = end - np.array(start)
        total_length = np.linalg.norm(direction)
        
        if total_length < 1e-6:
            return
        
        direction = direction / total_length
        
        glBegin(GL_LINES)
        
        pos = 0.0
        while pos < total_length:
            # Draw dash
            start_pos = np.array(start) + direction * pos
            end_pos = np.array(start) + direction * min(pos + dash_length, total_length)
            
            glVertex3f(*start_pos)
            glVertex3f(*end_pos)
            
            pos += dash_length * 2  # Skip gap
        
        glEnd()
    
    def validate_rotation_matrix(self, matrix: np.ndarray) -> bool:
        """
        Validate that a matrix is a proper rotation matrix
        
        Args:
            matrix: Matrix to validate
            
        Returns:
            True if valid rotation matrix
        """
        if matrix.shape != (3, 3):
            return False
        
        # Check if orthogonal (R * R.T = I)
        identity_check = np.allclose(matrix @ matrix.T, np.eye(3), atol=1e-6)
        
        # Check if determinant is 1 (proper rotation, not reflection)
        det_check = np.isclose(np.linalg.det(matrix), 1.0, atol=1e-6)
        
        return identity_check and det_check
    
    def cleanup(self):
        """Clean up coordinate system resources"""
        # No specific cleanup needed for coordinate system
        logger.info("CoordinateSystem cleaned up")


class DeviceCoordinateFrames:
    """Manages coordinate frames for different device types"""
    
    def __init__(self):
        # Define standard coordinate frames for each device type
        self.device_frames = {
            'phone': {
                'description': 'Phone held upright, screen facing user',
                'x_axis': 'Right when looking at screen',
                'y_axis': 'Up toward top of screen', 
                'z_axis': 'Out of screen toward user'
            },
            'watch': {
                'description': 'Watch worn on left wrist, screen facing up',
                'x_axis': 'Right when looking at screen',
                'y_axis': 'Up toward top of screen',
                'z_axis': 'Out of screen toward user'
            },
            'headphone': {
                'description': 'AirPods in ears, standard wearing position',
                'x_axis': 'Right ear direction',
                'y_axis': 'Up toward top of head',
                'z_axis': 'Forward in head direction'
            },
            'glasses': {
                'description': 'AR glasses worn normally on head',
                'x_axis': 'Right temple direction', 
                'y_axis': 'Up toward top of head',
                'z_axis': 'Forward in viewing direction'
            }
        }
        
        logger.info("DeviceCoordinateFrames initialized")
    
    def get_device_frame_info(self, device_type: str) -> dict:
        """Get coordinate frame information for a device type"""
        return self.device_frames.get(device_type, {
            'description': 'Unknown device type',
            'x_axis': 'Unknown',
            'y_axis': 'Unknown', 
            'z_axis': 'Unknown'
        })
    
    def get_transformation_matrix(self, from_device: str, to_device: str) -> np.ndarray:
        """
        Get transformation matrix between device coordinate frames
        
        Args:
            from_device: Source device type
            to_device: Target device type
            
        Returns:
            3x3 transformation matrix
        """
        # For now, return identity - in full implementation, this would
        # return actual transformation matrices between device frames
        return np.eye(3)


def test_coordinate_system():
    """Test coordinate system functionality"""
    coord_sys = CoordinateSystem()
    
    # Test quaternion to matrix conversion
    test_quat = np.array([0, 0, 0, 1])  # Identity quaternion
    matrix = coord_sys.quaternion_to_rotation_matrix(test_quat)
    
    print("Identity quaternion to matrix:")
    print(matrix)
    print("Is valid rotation matrix:", coord_sys.validate_rotation_matrix(matrix))
    
    # Test 90-degree rotation around Z-axis
    rotation_90z = R.from_euler('z', 90, degrees=True)
    quat_90z = rotation_90z.as_quat()
    matrix_90z = coord_sys.quaternion_to_rotation_matrix(quat_90z)
    
    print("\n90-degree Z rotation:")
    print(matrix_90z)
    print("Is valid rotation matrix:", coord_sys.validate_rotation_matrix(matrix_90z))
    
    # Test device-specific transformation
    glasses_matrix = coord_sys.apply_device_specific_transform(test_quat, 'glasses')
    print("\nGlasses frame transformation:")
    print(glasses_matrix)
    
    return True


if __name__ == "__main__":
    test_coordinate_system()