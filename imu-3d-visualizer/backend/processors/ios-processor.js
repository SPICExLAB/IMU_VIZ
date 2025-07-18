// iOS Data Processor
// Handles coordinate transformations for iPhone, Apple Watch, and AirPods

const { quaternionToEuler } = require('../utils/rotation-utils');
const { validateIOSData } = require('../parsers/ios-parser');
const deviceMappings = require('../config/device-mappings.json');

class IOSProcessor {
  constructor() {
    // Device index mapping
    this.deviceIndices = deviceMappings.indices;
  }

  /**
   * Process iOS device data
   * @param {Object} rawData - Parsed iOS data
   * @returns {Object|null} Processed data or null
   */
  process(rawData) {
    try {
      // Validate data first
      if (!validateIOSData(rawData)) {
        return null;
      }

      const deviceName = rawData.device_name.toLowerCase();
      const accelerometer = [...rawData.accelerometer];
      const quaternion = [...rawData.quaternion];
      const gyroscope = rawData.gyroscope || [0, 0, 0];
      const hasGyro = !!rawData.has_gyro;

      // Get device index
      const deviceId = this.getDeviceIndex(deviceName);
      if (deviceId === null) {
        console.warn(`Unknown iOS device: ${deviceName}`);
        return null;
      }

      // Convert iOS acceleration from G's to m/s² with coordinate flip
      // iOS sends userAcceleration in G's, need to convert to m/s²
      // Also apply coordinate system correction
      const processedAcc = [
        accelerometer[0] * (-9.8),
        accelerometer[1] * (-9.8),
        accelerometer[2] * (-9.8)
      ];

      // Calculate Euler angles for debugging
      const eulerAngles = quaternionToEuler(quaternion);

      // Normalize device name for consistency
      const normalizedName = this.normalizeDeviceName(deviceName);

      return {
        device_id: deviceId,
        device_name: normalizedName,
        device_type: 'ios',
        timestamp: Array.isArray(rawData.timestamps) ? rawData.timestamps[0] : rawData.timestamps,
        accelerometer: processedAcc,
        gyroscope: [...gyroscope],
        has_gyro: hasGyro,
        quaternion: [...quaternion],
        raw_quaternion: [...quaternion],
        euler: eulerAngles,
        raw_accelerometer_g: [...accelerometer],  // Keep original G values for debugging
        device_timestamp: rawData.timestamps[1] || null
      };
    } catch (error) {
      console.error('Error processing iOS data:', error);
      return null;
    }
  }

  /**
   * Get device index based on device name
   */
  getDeviceIndex(deviceName) {
    const normalized = deviceName.toLowerCase();
    
    // Check against device name mappings
    if (deviceMappings.deviceNames.ios.phone.some(name => normalized.includes(name))) {
      return this.deviceIndices.phone;
    }
    if (deviceMappings.deviceNames.ios.watch.some(name => normalized.includes(name))) {
      return this.deviceIndices.watch;
    }
    if (deviceMappings.deviceNames.ios.headphone.some(name => normalized.includes(name))) {
      return this.deviceIndices.headphone;
    }
    
    return null;
  }

  /**
   * Normalize device name for consistency
   */
  normalizeDeviceName(deviceName) {
    const normalized = deviceName.toLowerCase();
    
    if (normalized.includes('phone')) return 'phone';
    if (normalized.includes('watch')) return 'watch';
    if (normalized.includes('airpod') || normalized.includes('headphone')) return 'headphone';
    
    return deviceName;
  }
}

module.exports = IOSProcessor;