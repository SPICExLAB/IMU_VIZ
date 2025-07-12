// CalibrationPanel.js - With T-pose calibration support
import { useState, useRef } from 'react';
import { 
  calculateAverageQuaternion, 
  quaternionToRotationMatrix,
  transposeMatrix,
  matrixMultiply
} from '../utils/mathUtils';
import './CalibrationPanel.css';

const CalibrationPanel = ({ 
  selectedDevice, 
  devices, 
  onCalibrationComplete,
  onCalibrationReset,
  onTPoseCalibrationComplete,
  showOverlay = false,
  calibrationParams = {}
}) => {
  // Calibration states
  const [calibrationStep, setCalibrationStep] = useState('idle');
  const [countdown, setCountdown] = useState(3);
  const [progress, setProgress] = useState(0);
  
  // Collected samples
  const samplesRef = useRef([]);
  const tposeSamplesRef = useRef({});
  const calibrationDuration = 3; // seconds
  const samplingRate = 30; // Hz
  const samplesToCollect = calibrationDuration * samplingRate;
  
  // Handle world frame alignment
  const startWorldFrameCalibration = () => {
    if (!selectedDevice) return;
    
    console.log('Starting world frame calibration for device:', selectedDevice);
    
    setCalibrationStep('worldFrame');
    setCountdown(3);
    samplesRef.current = [];
    
    // Start countdown
    const countdownInterval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(countdownInterval);
          collectWorldFrameSamples();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };
  
  // Handle T-pose calibration
  const startTPoseCalibration = () => {
    console.log('Starting T-pose calibration for all devices');
    
    setCalibrationStep('tposeCountdown');
    setCountdown(3);
    tposeSamplesRef.current = {};
    
    // Start countdown
    const countdownInterval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(countdownInterval);
          collectTPoseSamples();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };
  
  // Collect samples for world frame alignment
  const collectWorldFrameSamples = () => {
    setCalibrationStep('inProgress');
    setProgress(0);
    let sampleCount = 0;
    
    console.log('Starting world frame sample collection');
    
    const sampleInterval = setInterval(() => {
      if (sampleCount >= samplesToCollect) {
        clearInterval(sampleInterval);
        processWorldFrameSamples();
        return;
      }
      
      // Add current device data to samples
      if (devices[selectedDevice]) {
        const deviceData = devices[selectedDevice];
        
        if (deviceData.quaternion && deviceData.accelerometer) {
          samplesRef.current.push({
            quaternion: [...deviceData.quaternion],
            accelerometer: [...deviceData.accelerometer]
          });
          
          sampleCount++;
          setProgress((sampleCount / samplesToCollect) * 100);
        }
      }
    }, 1000 / samplingRate);
  };
  
  // Collect T-pose samples for all active devices
  const collectTPoseSamples = () => {
    setCalibrationStep('tposeInProgress');
    setProgress(0);
    let sampleCount = 0;
    
    console.log('Starting T-pose sample collection');
    
    const sampleInterval = setInterval(() => {
      if (sampleCount >= samplesToCollect) {
        clearInterval(sampleInterval);
        processTPoseSamples();
        return;
      }
      
      // Collect samples from all active devices
      Object.entries(devices).forEach(([deviceKey, deviceData]) => {
        if (deviceData.isActive && deviceData.worldFrameQuaternion) {
          if (!tposeSamplesRef.current[deviceKey]) {
            tposeSamplesRef.current[deviceKey] = [];
          }
          
          tposeSamplesRef.current[deviceKey].push({
            quaternion: [...deviceData.quaternion],
            worldFrameQuaternion: [...deviceData.worldFrameQuaternion]
          });
        }
      });
      
      sampleCount++;
      setProgress((sampleCount / samplesToCollect) * 100);
    }, 1000 / samplingRate);
  };
  
  // Process collected world frame samples
  const processWorldFrameSamples = () => {
    const samples = samplesRef.current;
    
    console.log(`Processing ${samples.length} samples for world frame calibration`);
    
    if (samples.length === 0) {
      console.error('No samples collected for calibration!');
      setCalibrationStep('idle');
      return;
    }
    
    try {
      // Calculate average quaternion from samples
      const avgQuaternion = calculateAverageQuaternion(
        samples.map(s => s.quaternion)
      );
      
      // Convert to rotation matrix
      const rotationMatrix = quaternionToRotationMatrix(avgQuaternion);
      
      // Calculate smpl2imu as the transpose (inverse for rotation matrices)
      const smpl2imu = transposeMatrix(rotationMatrix);
      
      // Prepare calibration data
      const calibrationData = {
        smpl2imu: smpl2imu,
        referenceDeviceId: selectedDevice,
        referenceWorldQuat: avgQuaternion,
        isCalibrated: true
      };
      
      console.log('World frame calibration data prepared:', calibrationData);
      
      // Send to parent component
      if (onCalibrationComplete) {
        onCalibrationComplete(calibrationData);
      }
      
      setCalibrationStep('worldFrameComplete');
      
    } catch (error) {
      console.error('Error processing calibration samples:', error);
      setCalibrationStep('idle');
    }
  };
  
  // Process T-pose samples
  const processTPoseSamples = () => {
    console.log('Processing T-pose samples for all devices');
    
    try {
      const device2boneMatrices = {};
      
      // Calculate device2bone for each device
      Object.entries(tposeSamplesRef.current).forEach(([deviceKey, samples]) => {
        if (samples.length > 0) {
          // Average the world frame quaternions
          const avgWorldQuat = calculateAverageQuaternion(
            samples.map(s => s.worldFrameQuaternion)
          );
          
          // Convert to rotation matrix
          const tposeWorldRotMatrix = quaternionToRotationMatrix(avgWorldQuat);
          
          // Calculate device2bone matrix
          // In T-pose, the device should align with the bone's local frame
          // device2bone = inverse(tposeWorldRotMatrix) * identity
          // This simplifies to: device2bone = transpose(tposeWorldRotMatrix)
          const device2bone = transposeMatrix(tposeWorldRotMatrix);
          
          device2boneMatrices[deviceKey] = device2bone;
          
          console.log(`Device2bone calculated for ${deviceKey}:`, device2bone);
        }
      });
      
      // Send T-pose calibration data
      if (onTPoseCalibrationComplete) {
        onTPoseCalibrationComplete({
          device2boneMatrices,
          isTPoseCalibrated: true
        });
      }
      
      setCalibrationStep('complete');
      
    } catch (error) {
      console.error('Error processing T-pose samples:', error);
      setCalibrationStep('worldFrameComplete');
    }
  };
  
  // Reset calibration
  const resetCalibration = () => {
    setCalibrationStep('idle');
    setProgress(0);
    samplesRef.current = [];
    tposeSamplesRef.current = {};
    
    if (onCalibrationReset) {
      onCalibrationReset();
    }
  };
  
  // Get instruction text based on calibration step
  const getInstructionText = () => {
    switch (calibrationStep) {
      case 'idle':
        return "Calibrate your device to establish a reference frame";
      case 'worldFrame':
        return `Place ${devices[selectedDevice]?.device_name} aligned with your body (X=Left, Y=Up, Z=Forward). Starting in ${countdown}...`;
      case 'inProgress':
        return "Hold still while we calibrate the reference frame...";
      case 'worldFrameComplete':
        return "World frame established! Now calibrate T-pose for all devices.";
      case 'tposeCountdown':
        return `Stand in T-pose with all devices worn correctly. Starting in ${countdown}...`;
      case 'tposeInProgress':
        return "Hold T-pose while we calibrate all devices...";
      case 'complete':
        return "Calibration complete! All devices are calibrated.";
      default:
        return "";
    }
  };
  
  // Get button states
  const getWorldFrameButtonState = () => {
    if (!selectedDevice) return 'disabled';
    if (calibrationStep === 'idle') return 'available';
    if (calibrationStep === 'worldFrameComplete' || calibrationStep === 'complete') return 'done';
    return 'disabled';
  };
  
  const getTPoseButtonState = () => {
    if (calibrationStep === 'worldFrameComplete') return 'available';
    if (calibrationStep === 'complete') return 'done';
    return 'disabled';
  };
  
  // Render progress bar
  const renderProgressBar = () => {
    if (calibrationStep === 'inProgress' || calibrationStep === 'tposeInProgress') {
      return (
        <div className="calibration-progress">
          <div 
            className="progress-bar" 
            style={{ width: `${progress}%` }}
          />
        </div>
      );
    }
    return null;
  };
  
  const worldFrameButtonState = getWorldFrameButtonState();
  const tposeButtonState = getTPoseButtonState();
  
  return (
    <div className={`calibration-panel-container ${showOverlay ? 'with-overlay' : 'full-width'}`}>
      <div className="calibration-panel">
        <div className="calibration-content">
          <div className="calibration-instruction">
            {getInstructionText()}
          </div>
          
          {renderProgressBar()}
          
          <div className="calibration-buttons">
            <button 
              className={`calibration-button ${worldFrameButtonState}`}
              onClick={startWorldFrameCalibration}
              disabled={worldFrameButtonState === 'disabled'}
            >
              {worldFrameButtonState === 'done' ? "World Frame ✓" : "Align World Frame"}
            </button>
            
            <button 
              className={`calibration-button ${tposeButtonState}`}
              onClick={startTPoseCalibration}
              disabled={tposeButtonState === 'disabled'}
            >
              {tposeButtonState === 'done' ? "T-Pose ✓" : "T-Pose Calibration"}
            </button>
            
            <button 
              className="calibration-button reset"
              onClick={resetCalibration}
              disabled={calibrationStep === 'worldFrame' || 
                       calibrationStep === 'inProgress' || 
                       calibrationStep === 'tposeCountdown' ||
                       calibrationStep === 'tposeInProgress'}
            >
              Reset
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalibrationPanel;