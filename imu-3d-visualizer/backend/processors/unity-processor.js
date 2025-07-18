// Unity/AR Glasses Data Processor
// Handles Rokid AR glasses data with gravity removal

const { 
  quaternionToEuler,
  quaternionToRotationMatrix,
  transposeMatrix,
  multiplyMatrixVector
} = require('../utils/rotation-utils');
const { validateUnityData } = require('../parsers/unity-parser');
const deviceMappings = require('../config/device-mappings.json');
const fs = require('fs');
const path = require('path');

class UnityProcessor {
  constructor(useARAsHeadphone = true) {
    this.useARAsHeadphone = useARAsHeadphone;
    
    // Device index based on mapping flag
    this.deviceIndex = useARAsHeadphone ? 
      deviceMappings.indices.glasses_as_headphone : 
      deviceMappings.indices.glasses_separate;
    
    // Device name based on mapping flag
    this.deviceName = useARAsHeadphone ? 'headphone' : 'glasses';
    
    // Load AR glasses calibration
    this.calibration = null;
    this.loadCalibration();

    console.log(`📊 UnityProcessor initialized: AR glasses mapped as ${this.deviceName} (index ${this.deviceIndex})`);
  }

  /**
   * Load AR glasses calibration from JSON file
   */
  loadCalibration() {
    try {
      const calibrationPath = path.join(__dirname, '../config/rokid_calibration.json');
      if (fs.existsSync(calibrationPath)) {
        const calibrationData = JSON.parse(fs.readFileSync(calibrationPath, 'utf8'));
        this.calibration = {
          bias: calibrationData.bias,
          version: calibrationData.version,
          method: calibrationData.method
        };
        console.log(`✅ AR Glasses calibration loaded: bias=[${calibrationData.bias.map(b => b.toFixed(3)).join(', ')}]`);
      } else {
        console.log(`⚠️ AR Glasses calibration file not found at ${calibrationPath}`);
        console.log(`⚠️ Linear acceleration will not be bias-corrected`);
      }
    } catch (error) {
      console.error('❌ Error loading AR glasses calibration:', error);
    }
  }

  /**
   * Process Unity/AR glasses data
   * @param {Object} rawData - Parsed Unity data
   * @returns {Object|null} Processed data or null
   */
  process(rawData) {
    try {
      // Validate data first
      if (!validateUnityData(rawData)) {
        return null;
      }

      const accelerometer = [...rawData.accelerometer];
      const quaternion = [...rawData.quaternion];
      const gyroscope = rawData.gyroscope || [0, 0, 0];
      const hasGyro = !!rawData.has_gyro;

      // AR glasses already send acceleration in m/s², NO conversion needed
      // Apply gravity removal
      const linearAcc = this.removeGravity(accelerometer, quaternion);

      // Calculate Euler angles for debugging
      const eulerAngles = quaternionToEuler(quaternion);

      return {
        device_id: this.deviceIndex,
        device_name: this.deviceName,
        device_type: 'ar_glasses',
        timestamp: Array.isArray(rawData.timestamps) ? rawData.timestamps[0] : rawData.timestamps,
        accelerometer: accelerometer, // Raw acceleration with gravity
        linear_acceleration: linearAcc, // Gravity-removed and bias-corrected
        gyroscope: [...gyroscope],
        has_gyro: hasGyro,
        quaternion: quaternion,
        raw_quaternion: [...quaternion],
        euler: eulerAngles,
        calibration_applied: !!this.calibration,
        device_timestamp: rawData.timestamps[1] || null
      };
    } catch (error) {
      console.error('Error processing Unity/AR data:', error);
      return null;
    }
  }

  /**
   * Remove gravity from acceleration
   * @param {Array} acceleration - Raw acceleration [x, y, z]
   * @param {Array} quaternion - Device orientation [x, y, z, w]
   * @returns {Array} Linear acceleration without gravity
   */
  removeGravity(acceleration, quaternion) {
    try {
      // Gravity in world frame (determined by calibration)
      const gravityWorld = [0, 0, 9.81];
      
      // Transform gravity to device frame
      const rotationMatrix = quaternionToRotationMatrix(quaternion);
      const rotationMatrixInv = transposeMatrix(rotationMatrix);
      const gravityDevice = multiplyMatrixVector(rotationMatrixInv, gravityWorld);
      
      // Remove gravity from acceleration
      let linearAcc = [
        acceleration[0] - gravityDevice[0],
        acceleration[1] - gravityDevice[1],
        acceleration[2] - gravityDevice[2]
      ];
      
      // Apply bias correction if calibration is loaded
      if (this.calibration && this.calibration.bias) {
        linearAcc = [
          linearAcc[0] - this.calibration.bias[0],
          linearAcc[1] - this.calibration.bias[1],
          linearAcc[2] - this.calibration.bias[2]
        ];
      }
      
      return linearAcc;
    } catch (error) {
      console.warn('Failed to calculate linear acceleration:', error);
      return [0, 0, 0];
    }
  }

  /**
   * Check if calibration is loaded
   */
  hasCalibration() {
    return !!this.calibration;
  }

  /**
   * Reload calibration (useful if calibration file is updated)
   */
  reloadCalibration() {
    console.log('🔄 Reloading AR glasses calibration...');
    this.loadCalibration();
  }
}

module.exports = UnityProcessor;