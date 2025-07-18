import { useState, useCallback } from 'react';
import { notifications } from '@mantine/notifications';

export function useCalibration(sendMessage) {
  const [calibrationParams, setCalibrationParams] = useState({
    isCalibrated: false,
    isTPoseCalibrated: false,
    referenceDeviceId: null
  });

  // Handle world frame calibration
  const handleCalibrationComplete = useCallback((calibrationData) => {
    console.log('Calibration complete, sending to server:', calibrationData);
    
    // Send to server
    const success = sendMessage({
      type: 'calibration',
      data: calibrationData
    });
    
    if (success) {
      // Update local state
      setCalibrationParams({
        isCalibrated: true,
        referenceDeviceId: calibrationData.referenceDeviceId,
        referenceWorldQuat: calibrationData.referenceWorldQuat
      });
      
      notifications.show({
        title: 'World Frame Calibrated',
        message: 'Reference frame established successfully',
        color: 'blue',
      });
    } else {
      notifications.show({
        title: 'Calibration Failed',
        message: 'Could not send calibration data to server',
        color: 'red',
      });
    }
  }, [sendMessage]);

  // Handle T-pose calibration
  const handleTPoseCalibrationComplete = useCallback((tposeData) => {
    console.log('T-pose calibration complete, sending to server:', tposeData);
    
    // Log offset information
    if (tposeData.accOffsets) {
      console.log('Acceleration offsets:', tposeData.accOffsets);
    }
    if (tposeData.linearAccOffsets) {
      console.log('Linear acceleration offsets (AR glasses):', tposeData.linearAccOffsets);
    }
    
    // Send to server
    const success = sendMessage({
      type: 'tpose_calibration',
      data: tposeData
    });
    
    if (success) {
      // Update local state
      setCalibrationParams(prev => ({
        ...prev,
        isTPoseCalibrated: true,
        device2boneMatrices: tposeData.device2boneMatrices,
        accOffsets: tposeData.accOffsets,
        linearAccOffsets: tposeData.linearAccOffsets
      }));
      
      notifications.show({
        title: 'T-Pose Calibrated',
        message: 'All devices calibrated successfully',
        color: 'green',
      });
    } else {
      notifications.show({
        title: 'T-Pose Calibration Failed',
        message: 'Could not send calibration data to server',
        color: 'red',
      });
    }
  }, [sendMessage]);

  // Reset calibration
  const handleCalibrationReset = useCallback(() => {
    // Notify server
    const success = sendMessage({
      type: 'reset_calibration'
    });
    
    if (success) {
      // Reset local state
      setCalibrationParams({
        isCalibrated: false,
        isTPoseCalibrated: false,
        referenceDeviceId: null
      });
      
      notifications.show({
        title: 'Calibration Reset',
        message: 'All calibration data cleared',
        color: 'yellow',
      });
      
      console.log('Calibration reset');
    }
  }, [sendMessage]);

  return {
    calibrationParams,
    handleCalibrationComplete,
    handleTPoseCalibrationComplete,
    handleCalibrationReset
  };
}