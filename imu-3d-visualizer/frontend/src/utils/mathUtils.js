// mathUtils.js - A utility file for quaternion and matrix operations
import * as math from 'mathjs';

/**
 * Converts a quaternion [x, y, z, w] to a 3x3 rotation matrix
 * @param {Array} q - Quaternion as [x, y, z, w]
 * @returns {Array} 3x3 rotation matrix
 */
export const quaternionToRotationMatrix = (q) => {
  const [x, y, z, w] = q;
  
  // Calculate components
  const xx = x * x;
  const xy = x * y;
  const xz = x * z;
  const xw = x * w;
  
  const yy = y * y;
  const yz = y * z;
  const yw = y * w;
  
  const zz = z * z;
  const zw = z * w;
  
  // Create rotation matrix
  return [
    [1 - 2 * (yy + zz), 2 * (xy - zw), 2 * (xz + yw)],
    [2 * (xy + zw), 1 - 2 * (xx + zz), 2 * (yz - xw)],
    [2 * (xz - yw), 2 * (yz + xw), 1 - 2 * (xx + yy)]
  ];
};

/**
 * Converts a 3x3 rotation matrix to a quaternion [x, y, z, w]
 * @param {Array} m - 3x3 rotation matrix
 * @returns {Array} Quaternion as [x, y, z, w]
 */
export const rotationMatrixToQuaternion = (m) => {
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
};

/**
 * Multiplies two matrices using math.js
 * @param {Array} a - First matrix
 * @param {Array} b - Second matrix
 * @returns {Array} Result matrix
 */
export const matrixMultiply = (a, b) => {
  return math.multiply(a, b);
};

/**
 * Multiplies a matrix by a vector
 * @param {Array} m - Matrix
 * @param {Array} v - Vector
 * @returns {Array} Result vector
 */
export const matrixVectorMultiply = (m, v) => {
  return math.multiply(m, v);
};

/**
 * Transposes a matrix (inverts a rotation matrix)
 * @param {Array} m - Matrix to transpose
 * @returns {Array} Transposed matrix
 */
export const transposeMatrix = (m) => {
  return math.transpose(m);
};

/**
 * Multiplies two quaternions: result = q1 * q2
 * Safely handles null/undefined values by returning default identity quaternion
 * @param {Array} q1 - First quaternion [x, y, z, w]
 * @param {Array} q2 - Second quaternion [x, y, z, w]
 * @returns {Array} Result quaternion [x, y, z, w]
 */
export const quaternionMultiply = (q1, q2) => {
  // Default identity quaternion if inputs are invalid
  if (!q1 || !q2 || !Array.isArray(q1) || !Array.isArray(q2) || q1.length !== 4 || q2.length !== 4) {
    console.warn('Invalid quaternion inputs for multiplication:', q1, q2);
    return [0, 0, 0, 1]; // Identity quaternion
  }
  
  const [x1, y1, z1, w1] = q1;
  const [x2, y2, z2, w2] = q2;
  
  return [
    w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
    w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
    w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
  ];
};

/**
 * Safely handles quaternion multiplication, with validation
 * Returns first quaternion if second is invalid (identity operation)
 * @param {Array} q1 - First quaternion [x, y, z, w]
 * @param {Array} q2 - Second quaternion [x, y, z, w]
 * @returns {Array} Destructurable array [x, y, z, w]
 */
export const multiplyQuaternions = (q1, q2) => {
  // If q2 is not valid, just return q1
  if (!q2 || !Array.isArray(q2) || q2.length !== 4) {
    return q1;
  }
  
  return quaternionMultiply(q1, q2);
};

/**
 * Normalizes a quaternion to unit length
 * @param {Array} q - Quaternion [x, y, z, w]
 * @returns {Array} Normalized quaternion
 */
export const normalizeQuaternion = (q) => {
  const magnitude = Math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]);
  
  if (magnitude === 0) {
    return [0, 0, 0, 1]; // Default quaternion representing no rotation
  }
  
  return [
    q[0] / magnitude,
    q[1] / magnitude,
    q[2] / magnitude,
    q[3] / magnitude
  ];
};

/**
 * Calculates the inverse of a quaternion
 * @param {Array} q - Quaternion [x, y, z, w]
 * @returns {Array} Inverse quaternion
 */
export const inverseQuaternion = (q) => {
  // For unit quaternions, the inverse is the conjugate
  return [
    -q[0],
    -q[1],
    -q[2],
    q[3]
  ];
};

/**
 * Converts quaternion to Euler angles in degrees (roll, pitch, yaw)
 * @param {Array} quaternion - Quaternion [x, y, z, w]
 * @returns {Array} Euler angles in degrees [roll, pitch, yaw]
 */
export const quaternionToEuler = (quaternion) => {
  const [x, y, z, w] = quaternion;
  
  // Roll (x-axis rotation)
  const sinr_cosp = 2 * (w * x + y * z);
  const cosr_cosp = 1 - 2 * (x * x + y * y);
  const roll = Math.atan2(sinr_cosp, cosr_cosp) * 180 / Math.PI;

  // Pitch (y-axis rotation)
  const sinp = 2 * (w * y - z * x);
  let pitch;
  if (Math.abs(sinp) >= 1) {
    pitch = Math.sign(sinp) * 90; // Use 90 degrees if out of range
  } else {
    pitch = Math.asin(sinp) * 180 / Math.PI;
  }

  // Yaw (z-axis rotation)
  const siny_cosp = 2 * (w * z + x * y);
  const cosy_cosp = 1 - 2 * (y * y + z * z);
  const yaw = Math.atan2(siny_cosp, cosy_cosp) * 180 / Math.PI;

  return [roll, pitch, yaw];
};

/**
 * Calculates the average of an array of quaternions
 * @param {Array} quaternions - Array of quaternions
 * @returns {Array} Average quaternion, normalized
 */
export const calculateAverageQuaternion = (quaternions) => {
  if (quaternions.length === 0) return [0, 0, 0, 1];
  
  // Simple averaging for quaternions
  const sum = [0, 0, 0, 0];
  
  for (const q of quaternions) {
    // Ensure quaternion is in the same hemisphere for better averaging
    const signCorrection = q[3] < 0 ? -1 : 1;
    
    sum[0] += q[0] * signCorrection;
    sum[1] += q[1] * signCorrection;
    sum[2] += q[2] * signCorrection;
    sum[3] += q[3] * signCorrection;
  }
  
  return normalizeQuaternion(sum);
};

/**
 * Creates an identity quaternion
 * @returns {Array} Identity quaternion [0, 0, 0, 1]
 */
export const identityQuaternion = () => {
  return [0, 0, 0, 1];
};

/**
 * Applies calibration to device quaternion and acceleration data
 * @param {Array} quaternion - Raw device quaternion [x, y, z, w]
 * @param {Array} acceleration - Raw device acceleration [x, y, z]
 * @param {Array} smpl2imu - Calibration matrix (3x3)
 * @returns {Object} Calibrated quaternion and acceleration
 */
export const applyCalibrationToDevice = (quaternion, acceleration, smpl2imu) => {
  try {
    if (!quaternion || !acceleration || !smpl2imu) {
      console.warn('Invalid inputs for calibration:', { 
        quaternion: quaternion ? 'valid' : 'invalid', 
        acceleration: acceleration ? 'valid' : 'invalid', 
        smpl2imu: smpl2imu ? 'valid' : 'invalid' 
      });
      return null;
    }
    
    // Debugging
    console.log('Applying calibration with inputs:', { 
      quaternion, 
      acceleration, 
      smpl2imu 
    });
    
    // Convert quaternion to rotation matrix
    const rotMatrix = quaternionToRotationMatrix(quaternion);
    
    // Apply smpl2imu transformation
    const worldRotMatrix = matrixMultiply(smpl2imu, rotMatrix);
    
    // Convert back to quaternion
    const worldQuaternion = rotationMatrixToQuaternion(worldRotMatrix);
    
    // Apply transformation to acceleration
    const worldAcceleration = matrixVectorMultiply(smpl2imu, acceleration);
    
    // Debugging 
    console.log('Calibration output:', {
      worldQuaternion,
      worldAcceleration
    });
    
    return {
      quaternion: worldQuaternion,
      acceleration: worldAcceleration
    };
  } catch (error) {
    console.error('Error applying calibration:', error);
    return null;
  }
};