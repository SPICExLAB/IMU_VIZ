/**
 * Data processing utilities for IMU sensor data
 * Handles coordinate transformations and device-specific processing
 * Converted from Python sensor_utils.py SensorDataProcessor class
 */

const { validateSensorData } = require('./data-parser');

class DataProcessor {
  constructor(useARAsHeadphone = true) {
    this.useARAsHeadphone = useARAsHeadphone;
    
    // Device index mapping for compatibility
    this.deviceIndices = {
      'phone': 0,
      'watch': 1,
      'headphone': 2,
      'glasses': 2  // When useARAsHeadphone=true
    };

    console.log(`📊 DataProcessor initialized with useARAsHeadphone=${useARAsHeadphone}`);
  }

  /**
   * Process device data and return standardized format
   * @param {string} deviceType - 'ios' or 'ar_glasses'
   * @param {Object} rawData - Raw data from parser
   * @returns {Object|null} Processed sensor data or null if processing fails
   */
  processDeviceData(deviceType, rawData) {
    try {
      if (!validateSensorData(rawData)) {
        console.warn('Invalid sensor data received');
        return null;
      }

      if (deviceType === 'ios') {
        return this.processIOSData(rawData);
      } else if (deviceType === 'ar_glasses') {
        return this.processARGlassesData(rawData);
      } else {
        console.warn(`Unknown device type: ${deviceType}`);
        return null;
      }
    } catch (error) {
      console.error(`Error processing ${deviceType} data:`, error);
      return null;
    }
  }

  /**
   * Process iOS device data (iPhone, Apple Watch, AirPods)
   */
  processIOSData(rawData) {
    try {
      const deviceName = rawData.device_name.toLowerCase();
      const accelerometer = [...rawData.accelerometer]; // Copy array
      const quaternion = [...rawData.quaternion]; // Copy array
      const gyroscope = rawData.gyroscope || [0, 0, 0];

      // Get device index
      const deviceId = this.getDeviceIndex(deviceName);
      if (deviceId === null) {
        console.warn(`Unknown iOS device: ${deviceName}`);
        return null;
      }

      // Apply device-specific transformations
      const { processedAcc, processedQuat } = this.applyIOSTransformations(
        deviceName, accelerometer, quaternion
      );

      // Calculate Euler angles
      const eulerAngles = this.quaternionToEuler(processedQuat);

      return {
        device_id: deviceId,
        device_name: deviceName,
        device_type: 'ios',
        timestamp: Array.isArray(rawData.timestamps) ? rawData.timestamps[0] : rawData.timestamps,
        accelerometer: processedAcc,
        gyroscope: [...gyroscope],
        quaternion: processedQuat,
        raw_quaternion: [...quaternion],
        euler: eulerAngles,
        raw_message: rawData.raw_message
      };
    } catch (error) {
      console.error('Error processing iOS data:', error);
      return null;
    }
  }

  /**
   * Process AR glasses data from Unity app
   */
  processARGlassesData(rawData) {
    try {
      const accelerometer = [...rawData.accelerometer];
      const quaternion = [...rawData.quaternion];
      const gyroscope = rawData.gyroscope || [0, 0, 0];

      // Determine device index based on useARAsHeadphone flag
      let deviceId, deviceName;
      if (this.useARAsHeadphone) {
        deviceId = this.deviceIndices['glasses']; // Index 2 (same as headphone)
        deviceName = 'headphone'; // Map to headphone for compatibility
      } else {
        deviceId = 4; // Separate index for AR glasses
        deviceName = 'glasses';
      }

      // Apply AR glasses transformations
      const { processedAcc, processedQuat } = this.applyARGlassesTransformations(
        accelerometer, quaternion, true // removeGravity = true
      );

      // Calculate Euler angles
      const eulerAngles = this.quaternionToEuler(processedQuat);

      return {
        device_id: deviceId,
        device_name: deviceName,
        device_type: 'ar_glasses',
        timestamp: Array.isArray(rawData.timestamps) ? rawData.timestamps[0] : rawData.timestamps,
        accelerometer: processedAcc,
        gyroscope: [...gyroscope],
        quaternion: processedQuat,
        raw_quaternion: [...quaternion],
        euler: eulerAngles,
        raw_message: rawData.raw_message
      };
    } catch (error) {
      console.error('Error processing AR glasses data:', error);
      return null;
    }
  }

  /**
   * Get device index for compatibility
   */
  getDeviceIndex(deviceName) {
    const nameMapping = {
      'phone': 'phone',
      'iphone': 'phone',
      'watch': 'watch',
      'applewatch': 'watch',
      'headphone': 'headphone',
      'airpods': 'headphone',
      'glasses': 'glasses',
      'arglasses': 'glasses'
    };

    const normalizedName = nameMapping[deviceName.toLowerCase()];
    if (normalizedName) {
      return this.deviceIndices[normalizedName];
    }
    return null;
  }

  /**
   * Apply device-specific coordinate transformations for iOS devices
   */
  applyIOSTransformations(deviceName, accelerometer, quaternion) {
    // Copy arrays to avoid modifying originals
    let acc = [...accelerometer];
    let quat = [...quaternion];

    // Apply device-specific transformations
    if (deviceName === 'headphone') {
      // AirPods coordinate frame adjustments
      // Convert quaternion to Euler for transformation
      const euler = this.quaternionToEulerRadians(quat);
      const fixedEuler = [euler[0] * -1, euler[2], euler[1]];
      quat = this.eulerToQuaternion(fixedEuler);
      acc = [acc[0] * -1, acc[2], acc[1]];
    }

    return { processedAcc: acc, processedQuat: quat };
  }


/**
   * Apply coordinate transformations for AR glasses
   * AR Glasses frame: X:right, Y:forward, Z:up

   */
  applyARGlassesTransformations(accelerometer, quaternion, removeGravity = true) {
    // Copy arrays
    let acc = [...accelerometer];
    const quat = [...quaternion];

    let transformedAcc = [acc[0], acc[1], acc[2]];

    // Remove gravity if requested
    if (removeGravity) {
      try {
        const gravityWorld = [0, 0, 9.81];
        
        // Create rotation matrix from quaternion to transform gravity to device frame
        const rotationMatrix = this.quaternionToRotationMatrix(quat);
        const rotationMatrixInv = this.transposeMatrix(rotationMatrix);
        const gravityDevice = this.multiplyMatrixVector(rotationMatrixInv, gravityWorld);
        
        // Remove gravity from acceleration
        transformedAcc[0] -= gravityDevice[0];
        transformedAcc[1] -= gravityDevice[1];
        transformedAcc[2] -= gravityDevice[2];
      } catch (error) {
        console.warn('Failed to remove gravity:', error);
      }
    }

    transformedAcc = [-transformedAcc[0], transformedAcc[2], -transformedAcc[1]]

    // Quaternion transformations can be added here if needed
    const transformedQuat = quat;

    return { processedAcc: transformedAcc, processedQuat: transformedQuat };
  }

  /**
   * Convert quaternion to Euler angles (roll, pitch, yaw) in degrees
   */
  quaternionToEuler(quaternion) {
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
        pitch = Math.sign(sinp) * Math.PI / 2; // Use 90 degrees if out of range
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
   */
  quaternionToEulerRadians(quaternion) {
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
   * Convert Euler angles to quaternion
   */
  eulerToQuaternion(euler) {
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
   * Convert quaternion to rotation matrix
   */
  quaternionToRotationMatrix(quaternion) {
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
   */
  transposeMatrix(matrix) {
    return [
      [matrix[0][0], matrix[1][0], matrix[2][0]],
      [matrix[0][1], matrix[1][1], matrix[2][1]],
      [matrix[0][2], matrix[1][2], matrix[2][2]]
    ];
  }

  /**
   * Multiply a 3x3 matrix with a 3D vector
   */
  multiplyMatrixVector(matrix, vector) {
    return [
      matrix[0][0] * vector[0] + matrix[0][1] * vector[1] + matrix[0][2] * vector[2],
      matrix[1][0] * vector[0] + matrix[1][1] * vector[1] + matrix[1][2] * vector[2],
      matrix[2][0] * vector[0] + matrix[2][1] * vector[1] + matrix[2][2] * vector[2]
    ];
  }

  /**
   * Normalize a quaternion
   */
  normalizeQuaternion(quaternion) {
    const [x, y, z, w] = quaternion;
    const magnitude = Math.sqrt(x * x + y * y + z * z + w * w);
    
    if (magnitude === 0) {
      return [0, 0, 0, 1]; // Return identity quaternion
    }
    
    return [x / magnitude, y / magnitude, z / magnitude, w / magnitude];
  }

  /**
   * Get processing statistics
   */
  getStatistics() {
    return {
      useARAsHeadphone: this.useARAsHeadphone,
      deviceIndices: { ...this.deviceIndices }
    };
  }
}

module.exports = DataProcessor;