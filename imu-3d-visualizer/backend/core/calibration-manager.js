// backend/calibration-manager.js
const math = require('mathjs');
const {
  quaternionToRotationMatrix,
  rotationMatrixToQuaternion,
  quaternionToEuler,
  inverseQuaternion,
  multiplyQuaternions
} = require('../utils/rotation-utils');

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
      const rotMatrix = quaternionToRotationMatrix(deviceData.quaternion);
      let worldRotMatrix = math.multiply(calibration.smpl2imu, rotMatrix);
      
      // Apply device2bone transformation if available (T-pose calibrated)
      if (device2bone) {
        worldRotMatrix = math.multiply(worldRotMatrix, device2bone);
      }
      
      const worldQuaternion = rotationMatrixToQuaternion(worldRotMatrix);
      
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
      const worldEuler = quaternionToEuler(worldQuaternion);
      
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
    const refQuatInverse = inverseQuaternion(referenceQuat);
    
    // Multiply worldQuaternion by inverse of reference quaternion
    // This gives us the relative rotation from the calibration moment
    const relativeQuat = multiplyQuaternions(refQuatInverse, worldQuaternion);
    
    // After calibration (especially T-pose), the coordinate systems are aligned
    // No need for device-specific transforms - just return the relative quaternion
    return relativeQuat;
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