// backend/calibration-manager.js
const math = require('mathjs');

class CalibrationManager {
  constructor() {
    // Store calibration data per client/session
    this.calibrations = new Map();
  }

  /**
   * Store calibration data for a client
   * @param {string} clientId - Unique client identifier
   * @param {Object} calibrationData - Calibration parameters
   */
  setCalibration(clientId, calibrationData) {
    console.log(`📐 Storing calibration for client ${clientId}`);
    this.calibrations.set(clientId, {
      smpl2imu: calibrationData.smpl2imu,
      referenceDeviceId: calibrationData.referenceDeviceId,
      referenceWorldQuat: calibrationData.referenceWorldQuat,
      device2boneMatrices: {},
      accOffsets: {},
      linearAccOffsets: {},
      timestamp: Date.now()
    });
  }

  /**
   * Store T-pose calibration data for a client
   * @param {string} clientId - Unique client identifier
   * @param {Object} tposeData - T-pose calibration data
   */
  setTPoseCalibration(clientId, tposeData) {
    console.log(`🙆 Storing T-pose calibration for client ${clientId}`);
    const calibration = this.calibrations.get(clientId);
    
    if (calibration) {
      calibration.device2boneMatrices = tposeData.device2boneMatrices;
      calibration.accOffsets = tposeData.accOffsets || {};
      calibration.linearAccOffsets = tposeData.linearAccOffsets || {};
      calibration.isTPoseCalibrated = true;
      
      // Log offset information
      console.log(`📊 Acceleration offsets stored for ${Object.keys(tposeData.accOffsets || {}).length} devices`);
      if (tposeData.linearAccOffsets && Object.keys(tposeData.linearAccOffsets).length > 0) {
        console.log(`📊 Linear acceleration offsets stored for ${Object.keys(tposeData.linearAccOffsets).length} AR glasses`);
      }
    }
  }

  /**
   * Remove calibration for a client
   * @param {string} clientId 
   */
  clearCalibration(clientId) {
    console.log(`🗑️ Clearing calibration for client ${clientId}`);
    this.calibrations.delete(clientId);
  }

  /**
   * Apply calibration to device data if available
   * @param {string} clientId 
   * @param {Object} deviceData - Raw device data
   * @returns {Object} Device data with world frame additions
   */
  applyCalibration(clientId, deviceData) {
    const calibration = this.calibrations.get(clientId);
    
    if (!calibration || !calibration.smpl2imu) {
      return deviceData; // Return unchanged if no calibration
    }

    try {
      // Get device2bone matrix if T-pose calibrated
      const deviceKey = `${deviceData.device_name}_${deviceData.device_id}`;
      const device2bone = calibration.device2boneMatrices?.[deviceKey];
      
      // Calculate world frame quaternion
      const rotMatrix = this.quaternionToRotationMatrix(deviceData.quaternion);
      let worldRotMatrix = math.multiply(calibration.smpl2imu, rotMatrix);
      
      // Apply device2bone transformation if available (T-pose calibrated)
      if (device2bone) {
        worldRotMatrix = math.multiply(worldRotMatrix, device2bone);
      }
      
      const worldQuaternion = this.rotationMatrixToQuaternion(worldRotMatrix);
      
      // Calculate world frame accelerometer
      // For acceleration, we only use smpl2imu * rotMatrix (not device2bone)
      const accTransformMatrix = math.multiply(calibration.smpl2imu, rotMatrix);
      let worldAccelerometer = math.multiply(accTransformMatrix, deviceData.accelerometer);
      
      // Apply acceleration offset if available
      if (calibration.accOffsets && calibration.accOffsets[deviceKey]) {
        worldAccelerometer = [
          worldAccelerometer[0] - calibration.accOffsets[deviceKey][0],
          worldAccelerometer[1] - calibration.accOffsets[deviceKey][1],
          worldAccelerometer[2] - calibration.accOffsets[deviceKey][2]
        ];
      }
      
      // Calculate world frame linear acceleration if available (AR glasses)
      let worldLinearAcceleration;
      if (deviceData.linear_acceleration) {
        worldLinearAcceleration = math.multiply(accTransformMatrix, deviceData.linear_acceleration);
        
        // Apply linear acceleration offset if available
        if (calibration.linearAccOffsets && calibration.linearAccOffsets[deviceKey]) {
          worldLinearAcceleration = [
            worldLinearAcceleration[0] - calibration.linearAccOffsets[deviceKey][0],
            worldLinearAcceleration[1] - calibration.linearAccOffsets[deviceKey][1],
            worldLinearAcceleration[2] - calibration.linearAccOffsets[deviceKey][2]
          ];
        }
      }
      
      // Calculate world frame Euler angles
      const worldEuler = this.quaternionToEuler(worldQuaternion);
      
      // Calculate visualization quaternion based on device type
      const worldFrameQuatForViz = this.getVisualizationQuaternion(
        worldQuaternion, 
        deviceData.device_name,
        calibration.referenceWorldQuat
      );
      
      // Add world frame data to device data
      return {
        ...deviceData,
        worldFrameQuaternion: worldQuaternion,
        worldFrameQuatForViz: worldFrameQuatForViz,
        worldFrameAccelerometer: worldAccelerometer,
        worldFrameLinearAcceleration: worldLinearAcceleration,
        worldFrameEuler: worldEuler,
        isCalibrated: true,
        hasAccOffset: !!(calibration.accOffsets && calibration.accOffsets[deviceKey]),
        hasLinearAccOffset: !!(calibration.linearAccOffsets && calibration.linearAccOffsets[deviceKey])
      };
      
    } catch (error) {
      console.error(`Error applying calibration for client ${clientId}:`, error);
      return deviceData;
    }
  }

  /**
   * Convert quaternion to rotation matrix
   */
  quaternionToRotationMatrix(q) {
    const [x, y, z, w] = q;
    
    const xx = x * x;
    const xy = x * y;
    const xz = x * z;
    const xw = x * w;
    
    const yy = y * y;
    const yz = y * z;
    const yw = y * w;
    
    const zz = z * z;
    const zw = z * w;
    
    return [
      [1 - 2 * (yy + zz), 2 * (xy - zw), 2 * (xz + yw)],
      [2 * (xy + zw), 1 - 2 * (xx + zz), 2 * (yz - xw)],
      [2 * (xz - yw), 2 * (yz + xw), 1 - 2 * (xx + yy)]
    ];
  }

  /**
   * Convert rotation matrix to quaternion
   */
  rotationMatrixToQuaternion(m) {
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

  /**
   * Convert quaternion to Euler angles in degrees
   */
  quaternionToEuler(quaternion) {
    const [x, y, z, w] = quaternion;
    
    // Roll (x-axis rotation)
    const sinr_cosp = 2 * (w * x + y * z);
    const cosr_cosp = 1 - 2 * (x * x + y * y);
    const roll = Math.atan2(sinr_cosp, cosr_cosp) * 180 / Math.PI;

    // Pitch (y-axis rotation)
    const sinp = 2 * (w * y - z * x);
    let pitch;
    if (Math.abs(sinp) >= 1) {
      pitch = Math.sign(sinp) * 90;
    } else {
      pitch = Math.asin(sinp) * 180 / Math.PI;
    }

    // Yaw (z-axis rotation)
    const siny_cosp = 2 * (w * z + x * y);
    const cosy_cosp = 1 - 2 * (y * y + z * z);
    const yaw = Math.atan2(siny_cosp, cosy_cosp) * 180 / Math.PI;

    return [roll, pitch, yaw];
  }

  /**
   * Get calibration status for a client
   */
  getCalibrationStatus(clientId) {
    const calibration = this.calibrations.get(clientId);
    if (!calibration) return { isCalibrated: false };
    
    return {
      isCalibrated: true,
      isTPoseCalibrated: !!calibration.isTPoseCalibrated,
      hasAccOffsets: Object.keys(calibration.accOffsets || {}).length > 0,
      hasLinearAccOffsets: Object.keys(calibration.linearAccOffsets || {}).length > 0
    };
  }

  /**
   * Get calibration data for a client
   */
  getCalibrationData(clientId) {
    return this.calibrations.get(clientId);
  }

  /**
   * Calculate visualization quaternion with device-specific transforms
   * @param {Array} worldQuaternion - World frame quaternion [x, y, z, w]
   * @param {string} deviceName - Device name for specific transforms
   * @param {Array} referenceQuat - Reference quaternion from calibration
   * @returns {Array} Visualization quaternion [x, y, z, w]
   */
  getVisualizationQuaternion(worldQuaternion, deviceName, referenceQuat) {
    // First, calculate the inverse of the reference quaternion
    const refQuatInverse = this.inverseQuaternion(referenceQuat);
    
    // Multiply worldQuaternion by inverse of reference quaternion
    // This gives us the relative rotation from the calibration moment
    const relativeQuat = this.quaternionMultiply(refQuatInverse, worldQuaternion);
    
    // After calibration (especially T-pose), the coordinate systems are aligned
    // No need for device-specific transforms - just return the relative quaternion
    return relativeQuat;
  }

  /**
   * Calculate inverse of a quaternion (conjugate for unit quaternions)
   * @param {Array} q - Quaternion [x, y, z, w]
   * @returns {Array} Inverse quaternion
   */
  inverseQuaternion(q) {
    // For unit quaternions, inverse is the conjugate
    return [-q[0], -q[1], -q[2], q[3]];
  }

  /**
   * Multiply two quaternions: q1 * q2
   * @param {Array} q1 - First quaternion [x, y, z, w]
   * @param {Array} q2 - Second quaternion [x, y, z, w]
   * @returns {Array} Result quaternion
   */
  quaternionMultiply(q1, q2) {
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
   * Clean up old calibrations (older than 1 hour)
   */
  cleanup() {
    const oneHourAgo = Date.now() - (60 * 60 * 1000);
    
    for (const [clientId, calibration] of this.calibrations.entries()) {
      if (calibration.timestamp < oneHourAgo) {
        console.log(`🧹 Removing old calibration for client ${clientId}`);
        this.calibrations.delete(clientId);
      }
    }
  }
}

module.exports = CalibrationManager;