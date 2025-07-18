// Unity/AR Glasses Message Parser
// Parses sensor data from Unity app running on Rokid AR glasses

/**
 * Parse AR glasses message format from Unity
 * Expected format: "timestamp device_timestamp qx qy qz qw ax ay az [gx gy gz]"
 * 
 * @param {string} message - Raw AR glasses message string
 * @returns {Object|null} Parsed data object or null if parsing fails
 */
function parseUnityMessage(message) {
  try {
    const parts = message.trim().split(/\s+/);
    
    // Need at least timestamp + device_timestamp + 4 quat + 3 accel = 9 values
    if (parts.length < 9) {
      return null;
    }

    // Check if all required parts are numeric
    for (let i = 0; i < 9; i++) {
      const value = parseFloat(parts[i]);
      if (isNaN(value) || !isFinite(value)) {
        return null;
      }
    }

    // Parse components
    const timestamp = parseFloat(parts[0]);
    const deviceTimestamp = parseFloat(parts[1]);

    // Quaternion (x, y, z, w format from Unity)
    const quaternion = [
      parseFloat(parts[2]),
      parseFloat(parts[3]),
      parseFloat(parts[4]),
      parseFloat(parts[5])
    ];

    // Acceleration
    const accelerometer = [
      parseFloat(parts[6]),
      parseFloat(parts[7]),
      parseFloat(parts[8])
    ];

    // Determine if AR glasses have gyroscope data (need 12+ values)
    const hasGyro = parts.length >= 12;
    
    // Gyroscope if available
    const gyroscope = [0.0, 0.0, 0.0];
    if (hasGyro) {
      for (let i = 9; i < 12; i++) {
        const value = parseFloat(parts[i]);
        if (!isNaN(value)) {
          gyroscope[i - 9] = value;
        }
      }
    }

    // Check if we have linear acceleration data (positions 12-14)
    let linearAcceleration = null;
    if (parts.length >= 15) {
      linearAcceleration = [];
      for (let i = 12; i < 15; i++) {
        const value = parseFloat(parts[i]);
        if (!isNaN(value)) {
          linearAcceleration.push(value);
        }
      }
      if (linearAcceleration.length !== 3) {
        linearAcceleration = null;
      }
    }

    return {
      device_name: 'glasses',
      timestamps: [timestamp, deviceTimestamp],
      accelerometer: accelerometer,
      quaternion: quaternion,
      gyroscope: gyroscope,
      has_gyro: hasGyro,
      linear_acceleration: linearAcceleration,
      raw_message: message
    };

  } catch (error) {
    console.error('Error parsing Unity message:', error);
    return null;
  }
}

/**
 * Validate Unity/AR glasses parsed data
 * @param {Object} data - Parsed data
 * @returns {boolean} True if valid
 */
function validateUnityData(data) {
  if (!data) return false;

  // Check required fields
  if (!data.accelerometer || !data.quaternion || !data.timestamps) {
    return false;
  }

  // Check array lengths
  if (data.accelerometer.length !== 3 || data.quaternion.length !== 4) {
    return false;
  }

  // Check timestamps
  if (data.timestamps.length !== 2) {
    return false;
  }

  // Check for NaN values
  const allValues = [
    ...data.accelerometer,
    ...data.quaternion,
    ...data.timestamps
  ];

  for (const value of allValues) {
    if (isNaN(value) || !isFinite(value)) {
      return false;
    }
  }

  return true;
}

module.exports = {
  parseUnityMessage,
  validateUnityData
};