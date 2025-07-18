/**
 * Mathematical utilities for IMU sensor data processing
 * Handles quaternion operations, rotation matrices, and coordinate transformations
 */

/**
 * Convert quaternion to Euler angles (roll, pitch, yaw) in degrees
 * @param {Array<number>} quaternion - [x, y, z, w] quaternion
 * @returns {Array<number>} [roll, pitch, yaw] in degrees
 */
function quaternionToEuler(quaternion) {
  try {
    const [x, y, z, w] = quaternion;
    
    // Roll (x-axis rotation)
    const sinr_cosp = 2 * (w * x + y * z);
    const cosr_cosp = 1 - 2 * (x * x + y * y);
    const roll = Math.atan2(sinr_cosp, cosr_cosp);

    // Pitch (y-axis rotation)
    const sinp = 2 * (w * y - z * x);
    let pitch;
    if (Math.abs(sinp) >= 1) {
      pitch = Math.sign(sinp) * Math.PI / 2;
    } else {
      pitch = Math.asin(sinp);
    }

    // Yaw (z-axis rotation)
    const siny_cosp = 2 * (w * z + x * y);
    const cosy_cosp = 1 - 2 * (y * y + z * z);
    const yaw = Math.atan2(siny_cosp, cosy_cosp);

    // Convert to degrees
    return [
      roll * 180 / Math.PI,
      pitch * 180 / Math.PI,
      yaw * 180 / Math.PI
    ];
  } catch (error) {
    console.warn('Failed to convert quaternion to Euler:', error);
    return [0, 0, 0];
  }
}

/**
 * Convert quaternion to Euler angles in radians (for internal use)
 * @param {Array<number>} quaternion - [x, y, z, w] quaternion
 * @returns {Array<number>} [roll, pitch, yaw] in radians
 */
function quaternionToEulerRadians(quaternion) {
  const [x, y, z, w] = quaternion;
  
  // Roll (x-axis rotation)
  const sinr_cosp = 2 * (w * x + y * z);
  const cosr_cosp = 1 - 2 * (x * x + y * y);
  const roll = Math.atan2(sinr_cosp, cosr_cosp);

  // Pitch (y-axis rotation)
  const sinp = 2 * (w * y - z * x);
  let pitch;
  if (Math.abs(sinp) >= 1) {
    pitch = Math.sign(sinp) * Math.PI / 2;
  } else {
    pitch = Math.asin(sinp);
  }

  // Yaw (z-axis rotation)
  const siny_cosp = 2 * (w * z + x * y);
  const cosy_cosp = 1 - 2 * (y * y + z * z);
  const yaw = Math.atan2(siny_cosp, cosy_cosp);

  return [roll, pitch, yaw];
}

/**
 * Convert Euler angles (in radians) to quaternion
 * @param {Array<number>} euler - [roll, pitch, yaw] in radians
 * @returns {Array<number>} [x, y, z, w] quaternion
 */
function eulerToQuaternion(euler) {
  const [roll, pitch, yaw] = euler;
  
  const cr = Math.cos(roll * 0.5);
  const sr = Math.sin(roll * 0.5);
  const cp = Math.cos(pitch * 0.5);
  const sp = Math.sin(pitch * 0.5);
  const cy = Math.cos(yaw * 0.5);
  const sy = Math.sin(yaw * 0.5);

  return [
    sr * cp * cy - cr * sp * sy, // x
    cr * sp * cy + sr * cp * sy, // y
    cr * cp * sy - sr * sp * cy, // z
    cr * cp * cy + sr * sp * sy  // w
  ];
}

/**
 * Convert quaternion to 3x3 rotation matrix
 * @param {Array<number>} quaternion - [x, y, z, w] quaternion
 * @returns {Array<Array<number>>} 3x3 rotation matrix
 */
function quaternionToRotationMatrix(quaternion) {
  const [x, y, z, w] = quaternion;
  
  const xx = x * x;
  const yy = y * y;
  const zz = z * z;
  const xy = x * y;
  const xz = x * z;
  const yz = y * z;
  const wx = w * x;
  const wy = w * y;
  const wz = w * z;

  return [
    [1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy)],
    [2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx)],
    [2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy)]
  ];
}

/**
 * Transpose a 3x3 matrix
 * @param {Array<Array<number>>} matrix - 3x3 matrix
 * @returns {Array<Array<number>>} Transposed 3x3 matrix
 */
function transposeMatrix(matrix) {
  return [
    [matrix[0][0], matrix[1][0], matrix[2][0]],
    [matrix[0][1], matrix[1][1], matrix[2][1]],
    [matrix[0][2], matrix[1][2], matrix[2][2]]
  ];
}

/**
 * Multiply a 3x3 matrix with a 3D vector
 * @param {Array<Array<number>>} matrix - 3x3 matrix
 * @param {Array<number>} vector - 3D vector
 * @returns {Array<number>} Resulting 3D vector
 */
function multiplyMatrixVector(matrix, vector) {
  return [
    matrix[0][0] * vector[0] + matrix[0][1] * vector[1] + matrix[0][2] * vector[2],
    matrix[1][0] * vector[0] + matrix[1][1] * vector[1] + matrix[1][2] * vector[2],
    matrix[2][0] * vector[0] + matrix[2][1] * vector[1] + matrix[2][2] * vector[2]
  ];
}

/**
 * Linear interpolation for 3D vectors
 * @param {Array<number>} v1 - First vector
 * @param {Array<number>} v2 - Second vector
 * @param {number} t - Interpolation factor (0-1)
 * @returns {Array<number>} Interpolated vector
 */
function lerpVector(v1, v2, t) {
  return [
    v1[0] + (v2[0] - v1[0]) * t,
    v1[1] + (v2[1] - v1[1]) * t,
    v1[2] + (v2[2] - v1[2]) * t
  ];
}

/**
 * Linear interpolation for quaternions (normalized)
 * Note: For small time differences, linear interpolation is acceptable.
 * For larger differences, consider using SLERP (spherical linear interpolation)
 * @param {Array<number>} q1 - First quaternion [x, y, z, w]
 * @param {Array<number>} q2 - Second quaternion [x, y, z, w]
 * @param {number} t - Interpolation factor (0-1)
 * @returns {Array<number>} Interpolated and normalized quaternion
 */
function lerpQuaternion(q1, q2, t) {
  const result = [
    q1[0] + (q2[0] - q1[0]) * t,
    q1[1] + (q2[1] - q1[1]) * t,
    q1[2] + (q2[2] - q1[2]) * t,
    q1[3] + (q2[3] - q1[3]) * t
  ];
  
  // Normalize
  const mag = Math.sqrt(result[0]**2 + result[1]**2 + result[2]**2 + result[3]**2);
  return result.map(v => v / mag);
}

/**
 * Spherical linear interpolation for quaternions (more accurate than lerp)
 * @param {Array<number>} q1 - First quaternion [x, y, z, w]
 * @param {Array<number>} q2 - Second quaternion [x, y, z, w]
 * @param {number} t - Interpolation factor (0-1)
 * @returns {Array<number>} Interpolated quaternion
 */
function slerpQuaternion(q1, q2, t) {
  // Calculate dot product
  let dot = q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3];
  
  // If quaternions are close, use linear interpolation
  if (Math.abs(dot) > 0.9995) {
    return lerpQuaternion(q1, q2, t);
  }
  
  // Ensure shortest path
  if (dot < 0) {
    q2 = q2.map(v => -v);
    dot = -dot;
  }
  
  // Clamp dot product
  dot = Math.max(-1, Math.min(1, dot));
  
  // Calculate angle and sin values
  const theta = Math.acos(dot);
  const sinTheta = Math.sin(theta);
  
  // Calculate interpolation coefficients
  const a = Math.sin((1 - t) * theta) / sinTheta;
  const b = Math.sin(t * theta) / sinTheta;
  
  // Interpolate
  return [
    a * q1[0] + b * q2[0],
    a * q1[1] + b * q2[1],
    a * q1[2] + b * q2[2],
    a * q1[3] + b * q2[3]
  ];
}

/**
 * Multiply two quaternions
 * @param {Array<number>} q1 - First quaternion [x, y, z, w]
 * @param {Array<number>} q2 - Second quaternion [x, y, z, w]
 * @returns {Array<number>} Product quaternion
 */
function multiplyQuaternions(q1, q2) {
  const [x1, y1, z1, w1] = q1;
  const [x2, y2, z2, w2] = q2;
  
  return [
    w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
    w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
    w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
  ];
}

/**
 * Get the inverse (conjugate) of a quaternion
 * @param {Array<number>} quaternion - [x, y, z, w] quaternion
 * @returns {Array<number>} Inverse quaternion
 */
function inverseQuaternion(quaternion) {
  const [x, y, z, w] = quaternion;
  return [-x, -y, -z, w];
}

/**
 * Normalize a quaternion
 * @param {Array<number>} quaternion - [x, y, z, w] quaternion
 * @returns {Array<number>} Normalized quaternion
 */
function normalizeQuaternion(quaternion) {
  const mag = Math.sqrt(
    quaternion[0]**2 + 
    quaternion[1]**2 + 
    quaternion[2]**2 + 
    quaternion[3]**2
  );
  
  if (mag === 0) {
    return [0, 0, 0, 1]; // Return identity quaternion if magnitude is zero
  }
  
  return quaternion.map(v => v / mag);
}

/**
 * Rotate a vector by a quaternion
 * @param {Array<number>} vector - 3D vector to rotate
 * @param {Array<number>} quaternion - [x, y, z, w] quaternion
 * @returns {Array<number>} Rotated vector
 */
function rotateVectorByQuaternion(vector, quaternion) {
  // Convert vector to quaternion form [x, y, z, 0]
  const vectorQuat = [...vector, 0];
  
  // q * v * q^-1
  const qInv = inverseQuaternion(quaternion);
  const temp = multiplyQuaternions(quaternion, vectorQuat);
  const result = multiplyQuaternions(temp, qInv);
  
  // Return only the vector part
  return result.slice(0, 3);
}

/**
 * Calculate the angle between two quaternions in degrees
 * @param {Array<number>} q1 - First quaternion [x, y, z, w]
 * @param {Array<number>} q2 - Second quaternion [x, y, z, w]
 * @returns {number} Angle in degrees
 */
function quaternionAngle(q1, q2) {
  // Calculate dot product
  const dot = Math.abs(q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3]);
  
  // Clamp to avoid numerical errors
  const clampedDot = Math.min(1.0, dot);
  
  // Calculate angle
  const angleRad = 2 * Math.acos(clampedDot);
  
  // Convert to degrees
  return angleRad * 180 / Math.PI;
}

/**
 * Convert a 3x3 rotation matrix to quaternion
 * @param {Array<Array<number>>} m - 3x3 rotation matrix
 * @returns {Array<number>} [x, y, z, w] quaternion
 */
function rotationMatrixToQuaternion(m) {
  const trace = m[0][0] + m[1][1] + m[2][2];
  let x, y, z, w;
  
  if (trace > 0) {
    const S = Math.sqrt(trace + 1.0) * 2;
    w = 0.25 * S;
    x = (m[2][1] - m[1][2]) / S;
    y = (m[0][2] - m[2][0]) / S;
    z = (m[1][0] - m[0][1]) / S;
  } else if (m[0][0] > m[1][1] && m[0][0] > m[2][2]) {
    const S = Math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2;
    w = (m[2][1] - m[1][2]) / S;
    x = 0.25 * S;
    y = (m[0][1] + m[1][0]) / S;
    z = (m[0][2] + m[2][0]) / S;
  } else if (m[1][1] > m[2][2]) {
    const S = Math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2;
    w = (m[0][2] - m[2][0]) / S;
    x = (m[0][1] + m[1][0]) / S;
    y = 0.25 * S;
    z = (m[1][2] + m[2][1]) / S;
  } else {
    const S = Math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2;
    w = (m[1][0] - m[0][1]) / S;
    x = (m[0][2] + m[2][0]) / S;
    y = (m[1][2] + m[2][1]) / S;
    z = 0.25 * S;
  }
  
  return [x, y, z, w];
}

module.exports = {
  // Conversion functions
  quaternionToEuler,
  quaternionToEulerRadians,
  eulerToQuaternion,
  quaternionToRotationMatrix,
  rotationMatrixToQuaternion,
  
  // Matrix operations
  transposeMatrix,
  multiplyMatrixVector,
  
  // Interpolation
  lerpVector,
  lerpQuaternion,
  slerpQuaternion,
  
  // Quaternion operations
  multiplyQuaternions,
  inverseQuaternion,
  normalizeQuaternion,
  rotateVectorByQuaternion,
  quaternionAngle
};