// iOS Device Receiver
// Handles iPhone, Apple Watch, and AirPods data

const { parseIOSMessage } = require('../parsers/ios-parser');
const IOSProcessor = require('../processors/ios-processor');

class IOSReceiver {
  constructor() {
    this.processor = new IOSProcessor();
    this.deviceCount = {
      phone: 0,
      watch: 0,
      headphone: 0
    };
  }

  /**
   * Process iOS message and return processed data
   * @param {string} messageStr - Raw message string
   * @param {string} clientIP - Client IP address
   * @returns {Object|null} Processed data or null
   */
  process(messageStr, clientIP) {
    try {
      // Parse the iOS message
      const parsedData = parseIOSMessage(messageStr);
      if (!parsedData) {
        return null;
      }

      // Process the parsed data
      const processedData = this.processor.process(parsedData);
      if (!processedData) {
        return null;
      }

      // Track device statistics
      this.updateStats(processedData.device_name);

      return processedData;
    } catch (error) {
      console.error('Error processing iOS data:', error);
      return null;
    }
  }

  updateStats(deviceName) {
    if (this.deviceCount.hasOwnProperty(deviceName)) {
      this.deviceCount[deviceName]++;
      
      // Log every 1000 messages per device type
      if (this.deviceCount[deviceName] % 1000 === 0) {
        console.log(`📱 iOS ${deviceName}: ${this.deviceCount[deviceName]} messages processed`);
      }
    }
  }

  getStatistics() {
    return {
      devices: { ...this.deviceCount },
      total: Object.values(this.deviceCount).reduce((sum, count) => sum + count, 0)
    };
  }
}

module.exports = IOSReceiver;