// iOS Message Parser
// Parses sensor data from iOS devices (iPhone, Apple Watch, AirPods)

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
    
    // Determine if device has gyroscope data
    // Apple Watch format: timestamp device_timestamp ax ay az qx qy qz qw gx gy gz
    // iPhone format: timestamp device_timestamp ax ay az qx qy qz qw roll pitch yaw
    // AirPods format: timestamp device_timestamp ax ay az qx qy qz qw
    let hasGyro = false;
    let gyroscope = [0.0, 0.0, 0.0];
    
    if (deviceType === 'watch' && dataValues.length >= 12) {
      // Apple Watch has real gyroscope data
      hasGyro = true;
      gyroscope = dataValues.slice(9, 12);
    }
    // iPhone and AirPods don't send real gyroscope data

    return {
      device_id: deviceIdStr,
      device_name: deviceType,
      timestamps: timestamps,
      accelerometer: accelerometer,
      quaternion: quaternion,
      gyroscope: gyroscope,
      has_gyro: hasGyro,
      raw_message: message
    };

  } catch (error) {
    console.error('Error parsing iOS message:', error);
    return null;
  }
}

/**
 * Validate iOS parsed data
 * @param {Object} data - Parsed data
 * @returns {boolean} True if valid
 */
function validateIOSData(data) {
  if (!data) return false;

  // Check required fields
  if (!data.accelerometer || !data.quaternion || !data.timestamps) {
    return false;
  }

  // Check array lengths
  if (data.accelerometer.length !== 3 || data.quaternion.length !== 4) {
    return false;
  }

  // Check for valid device name
  const validDevices = ['phone', 'iphone', 'watch', 'applewatch', 'headphone', 'airpods'];
  if (!validDevices.includes(data.device_name.toLowerCase())) {
    return false;
  }

  return true;
}

module.exports = {
  parseIOSMessage,
  validateIOSData
};