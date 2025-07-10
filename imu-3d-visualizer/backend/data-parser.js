/**
 * Data parsing utilities for IMU sensor data
 * Converted from Python sensor_utils.py parsing functions
 */

/**
 * Parse iOS sensor message format
 * Expected format: "device_id;device_type:timestamp1 timestamp2 ax ay az qx qy qz qw [gx gy gz]"
 * 
 * @param {string} message - Raw iOS message string
 * @returns {Object|null} Parsed data object or null if parsing fails
 */
function parseIOSMessage(message) {
  try {
    message = message.trim();
    
    // Check basic format requirements
    if (!message || !message.includes(';') || !message.includes(':')) {
      return null;
    }

    // Split device info and data
    const parts = message.split(';', 2);
    if (parts.length !== 2) {
      return null;
    }

    const deviceIdStr = parts[0];
    const rawDataStr = parts[1];

    // Split device type and numeric data
    const dataParts = rawDataStr.split(':', 2);
    if (dataParts.length !== 2) {
      return null;
    }

    const deviceType = dataParts[0].toLowerCase();
    const dataStr = dataParts[1];

    // Parse numeric values
    const dataValues = [];
    const valueStrings = dataStr.trim().split(/\s+/);
    
    for (const valueStr of valueStrings) {
      const value = parseFloat(valueStr);
      if (!isNaN(value) && isFinite(value)) {
        dataValues.push(value);
      }
    }

    // Need at least 2 timestamps + 3 accel + 4 quat = 9 values
    if (dataValues.length < 9) {
      console.warn(`Insufficient iOS data values: got ${dataValues.length}, need at least 9`);
      return null;
    }

    // Extract data components
    const timestamps = dataValues.slice(0, 2);
    const accelerometer = dataValues.slice(2, 5);
    const quaternion = dataValues.slice(5, 9);
    
    // Extract gyroscope if available
    const gyroscope = dataValues.length >= 12 ? 
      dataValues.slice(9, 12) : [0.0, 0.0, 0.0];

    return {
      device_id: deviceIdStr,
      device_name: deviceType,
      timestamps: timestamps,
      accelerometer: accelerometer,
      quaternion: quaternion,
      gyroscope: gyroscope,
      raw_message: message
    };

  } catch (error) {
    console.error('Error parsing iOS message:', error);
    return null;
  }
}

/**
 * Parse AR glasses message format from Unity
 * Expected format: "timestamp device_timestamp qx qy qz qw ax ay az [gx gy gz]"
 * 
 * @param {string} message - Raw AR glasses message string
 * @returns {Object|null} Parsed data object or null if parsing fails
 */
function parseARGlassesMessage(message) {
  try {
    const parts = message.trim().split(/\s+/);
    
    // Need at least timestamp + device_timestamp + 4 quat + 3 accel = 9 values
    if (parts.length < 9) {
      console.warn(`AR glasses data format error: expected at least 9 values, got ${parts.length}`);
      return null;
    }

    // Parse components
    const timestamp = parseFloat(parts[0]);
    const deviceTimestamp = parseFloat(parts[1]);

    // Validate timestamps
    if (isNaN(timestamp) || isNaN(deviceTimestamp)) {
      console.warn('Invalid timestamps in AR glasses data');
      return null;
    }

    // Quaternion (x, y, z, w format from Unity)
    const quaternion = [];
    for (let i = 2; i < 6; i++) {
      const value = parseFloat(parts[i]);
      if (isNaN(value)) {
        console.warn(`Invalid quaternion value at index ${i}`);
        return null;
      }
      quaternion.push(value);
    }

    // Acceleration
    const accelerometer = [];
    for (let i = 6; i < 9; i++) {
      const value = parseFloat(parts[i]);
      if (isNaN(value)) {
        console.warn(`Invalid accelerometer value at index ${i}`);
        return null;
      }
      accelerometer.push(value);
    }

    // Gyroscope if available
    const gyroscope = [0.0, 0.0, 0.0];
    if (parts.length >= 12) {
      for (let i = 9; i < 12; i++) {
        const value = parseFloat(parts[i]);
        if (!isNaN(value)) {
          gyroscope[i - 9] = value;
        }
      }
    }

    return {
      device_name: 'glasses',
      timestamps: [timestamp, deviceTimestamp],
      accelerometer: accelerometer,
      quaternion: quaternion,
      gyroscope: gyroscope,
      raw_message: message
    };

  } catch (error) {
    console.error('Error parsing AR glasses message:', error);
    return null;
  }
}

/**
 * Validate parsed sensor data
 * @param {Object} data - Parsed sensor data
 * @returns {boolean} True if data is valid
 */
function validateSensorData(data) {
  if (!data) return false;

  // Check required fields
  if (!data.accelerometer || !data.quaternion || !data.timestamps) {
    return false;
  }

  // Check array lengths
  if (data.accelerometer.length !== 3) {
    console.warn('Invalid accelerometer data length');
    return false;
  }

  if (data.quaternion.length !== 4) {
    console.warn('Invalid quaternion data length');
    return false;
  }

  // Check for NaN or infinite values
  const allValues = [
    ...data.accelerometer,
    ...data.quaternion,
    ...(data.gyroscope || [])
  ];

  for (const value of allValues) {
    if (isNaN(value) || !isFinite(value)) {
      console.warn('Invalid sensor value detected');
      return false;
    }
  }

  return true;
}

/**
 * Get device index mapping for compatibility with Python code
 * @param {string} deviceName - Device name
 * @returns {number|null} Device index or null if unknown
 */
function getDeviceIndex(deviceName) {
  const deviceIndices = {
    'phone': 0,
    'iphone': 0,
    'watch': 1,
    'applewatch': 1,
    'headphone': 2,
    'airpods': 2,
    'glasses': 2,
    'arglasses': 2
  };

  const normalized = deviceName.toLowerCase();
  return deviceIndices[normalized] || null;
}

/**
 * Create standardized sensor data object
 * @param {string} deviceType - Device type ('ios' or 'ar_glasses')
 * @param {Object} rawData - Raw parsed data
 * @returns {Object} Standardized sensor data
 */
function createStandardizedData(deviceType, rawData) {
  const deviceIndex = getDeviceIndex(rawData.device_name);
  
  return {
    device_id: deviceIndex,
    device_name: rawData.device_name,
    device_type: deviceType,
    timestamp: Array.isArray(rawData.timestamps) ? rawData.timestamps[0] : rawData.timestamps,
    accelerometer: rawData.accelerometer,
    gyroscope: rawData.gyroscope || [0, 0, 0],
    quaternion: rawData.quaternion,
    raw_quaternion: rawData.quaternion.slice(), // Copy
    timestamps: rawData.timestamps,
    raw_message: rawData.raw_message
  };
}

module.exports = {
  parseIOSMessage,
  parseARGlassesMessage,
  validateSensorData,
  getDeviceIndex,
  createStandardizedData
};