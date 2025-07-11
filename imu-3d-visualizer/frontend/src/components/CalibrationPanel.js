import React, { useState, useRef, useEffect } from 'react';
import './CalibrationPanel.css';

// Matrix/Quaternion utility functions
const quaternionToRotationMatrix = (q) => {
  const [x, y, z, w] = q;
  
  // Calculate components
  const xx = x * x;
  const xy = x * y;
  const xz = x * z;
  const xw = x * w;
  
  const yy = y * y;
  const yz = y * z;
  const yw = y * w;
  
  const zz = z * z;
  const zw = z * w;
  
  // Create rotation matrix
  return [
    [1 - 2 * (yy + zz), 2 * (xy - zw), 2 * (xz + yw)],
    [2 * (xy + zw), 1 - 2 * (xx + zz), 2 * (yz - xw)],
    [2 * (xz - yw), 2 * (yz + xw), 1 - 2 * (xx + yy)]
  ];
};

const rotationMatrixToQuaternion = (m) => {
  // Extract rotation matrix components
  const [
    [m00, m01, m02],
    [m10, m11, m12],
    [m20, m21, m22]
  ] = m;
  
  // Calculate trace
  const trace = m00 + m11 + m22;
  
  let x, y, z, w;
  
  if (trace > 0) { 
    const S = Math.sqrt(trace + 1.0) * 2;
    w = 0.25 * S;
    x = (m21 - m12) / S;
    y = (m02 - m20) / S; 
    z = (m10 - m01) / S; 
  } else if ((m00 > m11) && (m00 > m22)) { 
    const S = Math.sqrt(1.0 + m00 - m11 - m22) * 2;
    w = (m21 - m12) / S;
    x = 0.25 * S;
    y = (m01 + m10) / S; 
    z = (m02 + m20) / S;
  } else if (m11 > m22) { 
    const S = Math.sqrt(1.0 + m11 - m00 - m22) * 2;
    w = (m02 - m20) / S;
    x = (m01 + m10) / S; 
    y = 0.25 * S;
    z = (m12 + m21) / S;
  } else { 
    const S = Math.sqrt(1.0 + m22 - m00 - m11) * 2;
    w = (m10 - m01) / S;
    x = (m02 + m20) / S;
    y = (m12 + m21) / S;
    z = 0.25 * S;
  }
  
  return [x, y, z, w];
};

const transposeMatrix = (m) => {
  return [
    [m[0][0], m[1][0], m[2][0]],
    [m[0][1], m[1][1], m[2][1]],
    [m[0][2], m[1][2], m[2][2]]
  ];
};

const calculateAverageQuaternion = (quaternions) => {
  if (quaternions.length === 0) return [0, 0, 0, 1];
  
  // Simple averaging for quaternions - for more accuracy, 
  // you might want to use a more sophisticated approach
  let sum = [0, 0, 0, 0];
  
  for (const q of quaternions) {
    sum[0] += q[0];
    sum[1] += q[1];
    sum[2] += q[2];
    sum[3] += q[3];
  }
  
  const magnitude = Math.sqrt(
    sum[0] * sum[0] + 
    sum[1] * sum[1] + 
    sum[2] * sum[2] + 
    sum[3] * sum[3]
  );
  
  return [
    sum[0] / magnitude,
    sum[1] / magnitude,
    sum[2] / magnitude,
    sum[3] / magnitude
  ];
};

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
    
    const sampleInterval = setInterval(() => {
      if (sampleCount >= samplesToCollect) {
        clearInterval(sampleInterval);
        processWorldFrameSamples();
        return;
      }
      
      // Add current device data to samples
      if (devices[selectedDevice]) {
        samplesRef.current.push({
          quaternion: [...devices[selectedDevice].quaternion],
          accelerometer: [...devices[selectedDevice].accelerometer]
        });
      }
      
      sampleCount++;
      setProgress(sampleCount / samplesToCollect * 100);
    }, 1000 / samplingRate);
  };
  
  // Process collected world frame samples
  const processWorldFrameSamples = () => {
    // Calculate average quaternion and acceleration
    const samples = samplesRef.current;
    
    if (samples.length === 0) {
      setCalibrationStep('idle');
      return;
    }
    
    // Average quaternions from samples
    const avgQuaternion = calculateAverageQuaternion(samples.map(s => s.quaternion));
    
    // Convert to rotation matrix
    const rotationMatrix = quaternionToRotationMatrix(avgQuaternion);
    
    // Calculate smpl2imu as the transpose (inverse for rotation matrices)
    const calculatedSmpl2imu = transposeMatrix(rotationMatrix);
    
    setSmpl2imu(calculatedSmpl2imu);
    setCalibrationStep('complete');
    
    // Pass calibration results back to parent
    onCalibrationComplete({
      smpl2imu: calculatedSmpl2imu,
      referenceDeviceId: selectedDevice,
      isCalibrated: true
    });
  };
  
  // Reset calibration
  const resetCalibration = () => {
    setCalibrationStep('idle');
    setSmpl2imu(null);
    samplesRef.current = [];
    
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
  
  // No matrix display needed
  
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