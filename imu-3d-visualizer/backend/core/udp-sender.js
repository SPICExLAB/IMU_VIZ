// backend/udp-sender.js
const dgram = require('dgram');
const EventEmitter = require('events');
const { 
  quaternionToRotationMatrix,
  lerpVector,
  lerpQuaternion
} = require('../utils/rotation-utils');

class UDPSender extends EventEmitter {
  constructor(port = 9001, host = '127.0.0.1', targetFPS = 30) {
    super();
    this.port = port;
    this.host = host;
    this.targetFPS = targetFPS;
    this.socket = null;
    this.isRunning = false;
    
    // Device buffers for resampling
    this.deviceBuffers = new Map();
    this.lastSendTime = Date.now();
    this.sendInterval = null;
    
    // Statistics
    this.stats = {
      packetsSent: 0,
      lastPacketTime: Date.now()
    };
    
    console.log(`📤 UDP Sender configured for ${host}:${port} at ${targetFPS}Hz`);
  }

  start() {
    try {
      // Create UDP socket
      this.socket = dgram.createSocket('udp4');
      
      this.socket.on('error', (error) => {
        console.error('📤 UDP sender socket error:', error);
        this.isRunning = false;
      });

      this.socket.on('close', () => {
        console.log('📤 UDP sender socket closed');
        this.isRunning = false;
      });

      // Start sending loop
      this.isRunning = true;
      const intervalMs = 1000 / this.targetFPS;
      
      this.sendInterval = setInterval(() => {
        this.sendCalibratedData();
      }, intervalMs);
      
      console.log(`📤 UDP sender started, sending at ${this.targetFPS}Hz`);
      return true;
      
    } catch (error) {
      console.error('Failed to start UDP sender:', error);
      return false;
    }
  }

  stop() {
    if (this.sendInterval) {
      clearInterval(this.sendInterval);
      this.sendInterval = null;
    }
    
    if (this.socket) {
      this.isRunning = false;
      this.socket.close();
      this.socket = null;
      console.log('📤 UDP sender stopped');
    }
  }

  updateDeviceData(deviceKey, deviceData, calibrationData) {
    if (!this.isRunning || !deviceData.isCalibrated) {
      return;
    }

    // Create timestamped entry
    const timestamp = Date.now();
    const entry = {
      timestamp,
      deviceKey,
      device_id: deviceData.device_id,
      device_name: deviceData.device_name,
      worldFrameQuaternion: deviceData.worldFrameQuaternion,
      worldFrameAccelerometer: deviceData.device_type === 'ar_glasses' && deviceData.worldFrameLinearAcceleration
        ? deviceData.worldFrameLinearAcceleration
        : deviceData.worldFrameAccelerometer,
      worldFrameLinearAcceleration: deviceData.worldFrameLinearAcceleration
    };

    // Initialize buffer if needed
    if (!this.deviceBuffers.has(deviceKey)) {
      this.deviceBuffers.set(deviceKey, []);
    }

    // Add to buffer and keep last 100ms of data
    const buffer = this.deviceBuffers.get(deviceKey);
    buffer.push(entry);
    
    // Clean old entries
    const cutoffTime = timestamp - 100;
    const cleanedBuffer = buffer.filter(e => e.timestamp > cutoffTime);
    this.deviceBuffers.set(deviceKey, cleanedBuffer);
  }

  sendCalibratedData() {
    const now = Date.now();
    
    // Get latest data for each device
    const latestData = this.getLatestDeviceData(now);
    
    // Only send if we have data for at least one device
    if (latestData.size === 0) {
      return;
    }

    // Create MobilePoser-compatible data structure with 5 devices
    // Original order: [phone, watch, headphone, xx, xx]
    const n_imus = 5;
    const glb_acc = Array(n_imus).fill(null).map(() => [0, 0, 0]);
    const glb_ori = Array(n_imus).fill(null).map(() => [[0,0,0],[0,0,0],[0,0,0]]); // Zero matrices
    const deviceStates = Array(n_imus).fill(false);
    
    // Map device data to original MobilePoser indices
    // phone -> 0, watch -> 1, headphone/glasses -> 2
    latestData.forEach((data, deviceKey) => {
      let deviceIndex = null;
      const deviceName = data.device_name.toLowerCase();
      
      // Check for headphone/glasses first to avoid matching "phone" in "headphone"
      if (deviceName.includes('headphone') || deviceName.includes('airpods') || 
          deviceName.includes('glasses') || deviceName.includes('arglasses') ||
          deviceName.includes('ar') || deviceName.includes('head')) {
        deviceIndex = 2;
      } else if (deviceName.includes('watch') || deviceName.includes('apple watch')) {
        deviceIndex = 1;
      } else if (deviceName.includes('phone') || deviceName.includes('iphone')) {
        deviceIndex = 0;
      }
      
      if (deviceIndex !== null && deviceIndex < n_imus) {
        // Set acceleration
        glb_acc[deviceIndex] = data.worldFrameAccelerometer;
        
        // Convert quaternion to rotation matrix
        glb_ori[deviceIndex] = quaternionToRotationMatrix(data.worldFrameQuaternion);
        
        deviceStates[deviceIndex] = true;
      }
    });

    // Create packet
    const packet = {
      type: 'imu_data',
      timestamp: now,
      n_imus: n_imus,
      glb_acc: glb_acc,
      glb_ori: glb_ori,
      device_states: deviceStates,
      fps: this.targetFPS
    };

    // Send packet
    const message = JSON.stringify(packet);
    const buffer = Buffer.from(message);
    
    this.socket.send(buffer, this.port, this.host, (error) => {
      if (error) {
        console.error('Error sending UDP packet:', error);
      } else {
        this.stats.packetsSent++;
        this.stats.lastPacketTime = now;
        
        // Log occasionally
        if (this.stats.packetsSent % 100 === 0) {
          console.log(`📤 Sent ${this.stats.packetsSent} packets to port ${this.port}`);
        }
      }
    });
  }

  getLatestDeviceData(targetTime) {
    const latestData = new Map();
    
    this.deviceBuffers.forEach((buffer, deviceKey) => {
      if (buffer.length === 0) return;
      
      // Get the most recent entry
      const latest = buffer[buffer.length - 1];
      
      // Check if data is recent enough (within 100ms)
      if (targetTime - latest.timestamp < 100) {
        // If we have at least 2 samples, we can interpolate
        if (buffer.length >= 2) {
          const interpolated = this.interpolateDeviceData(buffer, targetTime);
          if (interpolated) {
            latestData.set(deviceKey, interpolated);
          }
        } else {
          // Use latest as-is
          latestData.set(deviceKey, latest);
        }
      }
    });
    
    return latestData;
  }

  interpolateDeviceData(buffer, targetTime) {
    // Find two samples to interpolate between
    let before = null;
    let after = null;
    
    for (let i = 0; i < buffer.length; i++) {
      if (buffer[i].timestamp <= targetTime) {
        before = buffer[i];
      } else {
        after = buffer[i];
        break;
      }
    }
    
    // If we only have samples before or after, use the closest one
    if (!before) return after;
    if (!after) return before;
    
    // Linear interpolation
    const t = (targetTime - before.timestamp) / (after.timestamp - before.timestamp);
    
    return {
      ...before,
      timestamp: targetTime,
      // Interpolate acceleration
      worldFrameAccelerometer: lerpVector(
        before.worldFrameAccelerometer,
        after.worldFrameAccelerometer,
        t
      ),
      // Interpolate quaternion
      worldFrameQuaternion: lerpQuaternion(
        before.worldFrameQuaternion,
        after.worldFrameQuaternion,
        t
      )
    };
  }

  getStatistics() {
    return {
      packetsSent: this.stats.packetsSent,
      isRunning: this.isRunning,
      targetFPS: this.targetFPS,
      activeDevices: this.deviceBuffers.size,
      lastPacketTime: this.stats.lastPacketTime
    };
  }
}

module.exports = UDPSender;