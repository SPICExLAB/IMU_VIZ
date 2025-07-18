// Unity/AR Glasses Receiver
// Handles Rokid AR glasses data from Unity app

const { parseUnityMessage } = require('../parsers/unity-parser');
const UnityProcessor = require('../processors/unity-processor');

class UnityReceiver {
  constructor(useARAsHeadphone = true) {
    this.useARAsHeadphone = useARAsHeadphone;
    this.processor = new UnityProcessor(useARAsHeadphone);
    this.messageCount = 0;
  }

  /**
   * Process Unity/AR glasses message and return processed data
   * @param {string} messageStr - Raw message string
   * @param {string} clientIP - Client IP address
   * @returns {Object|null} Processed data or null
   */
  process(messageStr, clientIP) {
    try {
      // Parse the Unity message
      const parsedData = parseUnityMessage(messageStr);
      if (!parsedData) {
        return null;
      }

      // Process the parsed data (includes gravity removal)
      const processedData = this.processor.process(parsedData);
      if (!processedData) {
        return null;
      }

      // Track statistics
      this.messageCount++;
      if (this.messageCount % 1000 === 0) {
        console.log(`🥽 AR Glasses: ${this.messageCount} messages processed`);
      }

      return processedData;
    } catch (error) {
      console.error('Error processing Unity/AR data:', error);
      return null;
    }
  }

  getStatistics() {
    return {
      messageCount: this.messageCount,
      deviceMapping: this.useARAsHeadphone ? 'headphone (index 2)' : 'separate device',
      calibrationApplied: this.processor.hasCalibration()
    };
  }
}

module.exports = UnityReceiver;