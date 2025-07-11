// Fix for CalibrationPanel.js to ensure the calibration is fully completed and applied

import React, { useState, useRef, useEffect } from 'react';
import { 
  calculateAverageQuaternion, 
  quaternionToRotationMatrix,
  transposeMatrix,
  identityQuaternion,
  quaternionToEuler,
  matrixMultiply,
  matrixVectorMultiply,
  rotationMatrixToQuaternion
} from '../utils/mathUtils';
import './CalibrationPanel.css';

// Main CalibrationPanel Component
const CalibrationPanel = ({ 
  selectedDevice, 
  devices, 
  onCalibrationComplete,
  onCalibrationReset
}) => {
  // Calibration states
  const [calibrationStep, setCalibrationStep] = useState('idle'); // 'idle', 'worldFrame', 'inProgress', 'complete'
  const [countdown, setCountdown] = useState(3);
  const [progress, setProgress] = useState(0);
  
  // Button states
  const [worldFrameButtonState, setWorldFrameButtonState] = useState('available'); // 'disabled', 'available', 'done'
  
  // Calibration data
  const [smpl2imu, setSmpl2imu] = useState(null);
  const [refQuaternion, setRefQuaternion] = useState(null);
  
  // Collected samples
  const samplesRef = useRef([]);
  const calibrationDuration = 3; // seconds
  const samplingRate = 30; // Hz
  const samplesToCollect = calibrationDuration * samplingRate;
  
  // Update button states based on calibration step
  useEffect(() => {
    switch (calibrationStep) {
      case 'idle':
        setWorldFrameButtonState(selectedDevice ? 'available' : 'disabled');
        break;
      case 'worldFrame':
      case 'inProgress':
        setWorldFrameButtonState('disabled');
        break;
      case 'complete':
        setWorldFrameButtonState('done');
        break;
      default:
        break;
    }
  }, [calibrationStep, selectedDevice]);
  
  // Handle world frame alignment
  const startWorldFrameCalibration = () => {
    if (!selectedDevice || worldFrameButtonState !== 'available') return;
    
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
  
  // Collect samples for world frame alignment
  const collectWorldFrameSamples = () => {
    setCalibrationStep('inProgress');
    let sampleCount = 0;
    
    console.log('Starting sample collection');
    
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
          setProgress(sampleCount / samplesToCollect * 100);
        } else {
          console.warn('Missing quaternion or accelerometer data for sample', sampleCount);
        }
      } else {
        console.warn('Selected device not found in devices list');
      }
    }, 1000 / samplingRate);
  };
  
  // Process collected world frame samples
  const processWorldFrameSamples = () => {
    // Calculate average quaternion and acceleration
    const samples = samplesRef.current;
    
    console.log(`Processing ${samples.length} samples for calibration`);
    
    if (samples.length === 0) {
      console.error('No samples collected for calibration!');
      setCalibrationStep('idle');
      return;
    }
    
    try {
      // Average quaternions from samples
      const avgQuaternion = calculateAverageQuaternion(samples.map(s => s.quaternion));
      console.log('Average quaternion:', avgQuaternion);
      
      // Store this reference quaternion
      setRefQuaternion(avgQuaternion);
      
      // Convert to rotation matrix
      const rotationMatrix = quaternionToRotationMatrix(avgQuaternion);
      console.log('Rotation matrix:', rotationMatrix);
      
      // Calculate smpl2imu as the transpose (inverse for rotation matrices)
      const calculatedSmpl2imu = transposeMatrix(rotationMatrix);
      console.log('smpl2imu matrix:', calculatedSmpl2imu);
      
      setSmpl2imu(calculatedSmpl2imu);
      setCalibrationStep('complete');
      
      // Create the reference world quaternion
      const referenceWorldQuat = identityQuaternion();
      
      // Debug: Test the calibration matrix with a sample
      const testSample = samples[0];
      if (testSample) {
        const { quaternion, accelerometer } = testSample;
        console.log('Testing calibration with sample:', { quaternion, accelerometer });
        
        // Convert quaternion to rotation matrix
        const rotMatrix = quaternionToRotationMatrix(quaternion);
        
        // Apply smpl2imu transformation
        const worldRotMatrix = matrixMultiply(calculatedSmpl2imu, rotMatrix);
        
        // Convert back to quaternion
        const worldQuaternion = rotationMatrixToQuaternion(worldRotMatrix);
        
        // Apply transformation to acceleration
        const worldAcceleration = matrixVectorMultiply(calculatedSmpl2imu, accelerometer);
        
        console.log('Test results:', {
          worldQuaternion,
          worldAcceleration,
          worldEuler: quaternionToEuler(worldQuaternion)
        });
      }
      
      // Pass calibration results back to parent
      const calibrationData = {
        smpl2imu: calculatedSmpl2imu,
        referenceDeviceId: selectedDevice,
        referencedWorldQuat: referenceWorldQuat,
        isCalibrated: true
      };
      
      console.log('Calibration complete. Data:', calibrationData);
      
      if (onCalibrationComplete) {
        onCalibrationComplete(calibrationData);
      }
      
      // Immediate verification of calibration
      setTimeout(() => {
        if (devices[selectedDevice]) {
          const device = devices[selectedDevice];
          console.log('Verification check - device after calibration:', {
            hasWorldFrame: !!device.worldFrameQuaternion,
            worldFrameQuaternion: device.worldFrameQuaternion,
            worldFrameAccelerometer: device.worldFrameAccelerometer
          });
        }
      }, 500); // Short delay to allow state to update
      
    } catch (error) {
      console.error('Error processing calibration samples:', error);
      setCalibrationStep('idle');
    }
  };
  
  // Reset calibration
  const resetCalibration = () => {
    setCalibrationStep('idle');
    setSmpl2imu(null);
    setRefQuaternion(null);
    samplesRef.current = [];
    
    console.log('Calibration reset');
    
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
      case 'complete':
        return "Reference frame established! You can reset to calibrate again.";
      default:
        return "";
    }
  };
  
  // Render button with state-based styles
  const renderAlignButton = () => {
    const buttonClass = `calibration-button ${worldFrameButtonState}`;
    return (
      <button 
        className={buttonClass} 
        onClick={startWorldFrameCalibration}
        disabled={worldFrameButtonState === 'disabled'}
      >
        {worldFrameButtonState === 'done' ? "Align World Frame ✓" : "Align World Frame"}
      </button>
    );
  };
  
  // Render reset button
  const renderResetButton = () => {
    return (
      <button 
        className="calibration-button reset" 
        onClick={resetCalibration}
        disabled={calibrationStep === 'worldFrame' || calibrationStep === 'inProgress'}
      >
        Reset
      </button>
    );
  };
  
  // Render progress bar if active calibration
  const renderProgressBar = () => {
    if (calibrationStep === 'inProgress') {
      return (
        <div className="calibration-progress">
          <div 
            className="progress-bar" 
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      );
    }
    return null;
  };
  
  return (
    <div className="calibration-panel">
      <div className="calibration-content">
        <div className="calibration-instruction">
          {getInstructionText()}
        </div>
        
        {renderProgressBar()}
        
        <div className="calibration-buttons">
          {renderAlignButton()}
          {renderResetButton()}
        </div>
      </div>
    </div>
  );
};

export default CalibrationPanel;