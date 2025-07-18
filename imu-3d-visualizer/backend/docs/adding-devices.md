# Adding New Device Support

This guide explains how to add support for new devices (e.g., Android Watch, Android AR Glasses) to the IMU backend.

## Overview

The system is designed to be easily extensible. Adding a new device type requires creating three components:
1. **Parser**: Extracts data from raw messages
2. **Processor**: Applies device-specific transformations
3. **Receiver**: Orchestrates parsing and processing

## Step-by-Step Guide

### 1. Define Message Format

First, document your device's message format. For example, Android devices might send:
```
ANDROID:device_name:timestamp ax ay az qw qx qy qz [gx gy gz]
```

### 2. Create Parser (`parsers/android-parser.js`)

```javascript
// parsers/android-parser.js
function parseAndroidMessage(message) {
  try {
    // Check if message starts with Android identifier
    if (!message.startsWith('ANDROID:')) {
      return null;
    }

    const parts = message.split(':');
    if (parts.length < 3) return null;

    const deviceName = parts[1];
    const dataStr = parts[2];
    const values = dataStr.split(/\s+/).map(parseFloat);

    if (values.length < 8) return null;

    return {
      device_name: deviceName,
      timestamp: values[0],
      accelerometer: [values[1], values[2], values[3]],
      quaternion: [values[5], values[6], values[7], values[4]], // Note: reorder if needed
      gyroscope: values.length >= 11 ? [values[8], values[9], values[10]] : [0, 0, 0],
      has_gyro: values.length >= 11
    };
  } catch (error) {
    console.error('Error parsing Android message:', error);
    return null;
  }
}

module.exports = { parseAndroidMessage };
```

### 3. Create Processor (`processors/android-processor.js`)

```javascript
// processors/android-processor.js
const { quaternionToEuler } = require('../utils/rotation-utils');
const deviceMappings = require('../config/device-mappings.json');

class AndroidProcessor {
  constructor(useARAsHeadphone = true) {
    this.useARAsHeadphone = useARAsHeadphone;
  }

  process(rawData) {
    try {
      // Determine device index based on device name
      const deviceId = this.getDeviceIndex(rawData.device_name);
      
      // Apply any necessary transformations
      // Android might send acceleration in different units or coordinate system
      const processedAcc = this.transformAcceleration(rawData.accelerometer);
      
      // Calculate Euler angles
      const euler = quaternionToEuler(rawData.quaternion);

      return {
        device_id: deviceId,
        device_name: this.normalizeDeviceName(rawData.device_name),
        device_type: 'android',
        timestamp: rawData.timestamp,
        accelerometer: processedAcc,
        quaternion: rawData.quaternion,
        gyroscope: rawData.gyroscope,
        has_gyro: rawData.has_gyro,
        euler: euler
      };
    } catch (error) {
      console.error('Error processing Android data:', error);
      return null;
    }
  }

  getDeviceIndex(deviceName) {
    // Map Android devices to same indices as iOS equivalents
    if (deviceName.includes('watch')) return deviceMappings.indices.watch;
    if (deviceName.includes('glasses') && this.useARAsHeadphone) {
      return deviceMappings.indices.headphone;
    }
    // Add more mappings as needed
    return null;
  }

  transformAcceleration(acc) {
    // Apply any necessary transformations
    // Example: if Android sends in different units
    return acc;
  }

  normalizeDeviceName(name) {
    if (name.includes('watch')) return 'watch';
    if (name.includes('glasses')) return this.useARAsHeadphone ? 'headphone' : 'glasses';
    return name;
  }
}

module.exports = AndroidProcessor;
```

### 4. Create Receiver (`receivers/android-receiver.js`)

```javascript
// receivers/android-receiver.js
const { parseAndroidMessage } = require('../parsers/android-parser');
const AndroidProcessor = require('../processors/android-processor');

class AndroidReceiver {
  constructor(useARAsHeadphone = true) {
    this.processor = new AndroidProcessor(useARAsHeadphone);
    this.messageCount = 0;
  }

  process(messageStr, clientIP) {
    try {
      // Parse the message
      const parsedData = parseAndroidMessage(messageStr);
      if (!parsedData) {
        return null;
      }

      // Process the data
      const processedData = this.processor.process(parsedData);
      if (!processedData) {
        return null;
      }

      // Track statistics
      this.messageCount++;
      if (this.messageCount % 1000 === 0) {
        console.log(`🤖 Android: ${this.messageCount} messages processed`);
      }

      return processedData;
    } catch (error) {
      console.error('Error in Android receiver:', error);
      return null;
    }
  }
}

module.exports = AndroidReceiver;
```

### 5. Update Main UDP Receiver

In `receivers/udp-receiver.js`, add Android support:

```javascript
// Add import
const AndroidReceiver = require('./android-receiver');

// In constructor
this.androidReceiver = new AndroidReceiver(useARAsHeadphone);

// In handleIncomingMessage, add detection logic
if (messageStr.startsWith('ANDROID:')) {
  const result = this.androidReceiver.process(messageStr, clientIP);
  if (result) {
    this.emit('data', 'android', result, clientIP);
    return;
  }
}
```

### 6. Update Device Mappings

In `config/device-mappings.json`, add Android device names:

```json
{
  "deviceNames": {
    "android": {
      "watch": ["android watch", "wear os", "galaxy watch"],
      "glasses": ["android glasses", "android ar"]
    }
  }
}
```

### 7. Update Statistics

In `server.js`, add Android to statistics:

```javascript
this.stats = {
  ios: 0,
  ar_glasses: 0,
  android: 0,  // Add this
  unknown: 0,
  errors: 0,
  clients: 0
};
```

## Testing Your Implementation

1. Create a test script to send Android-formatted messages:
```javascript
const dgram = require('dgram');
const client = dgram.createSocket('udp4');

const testMessage = 'ANDROID:watch:1234567890 0.1 0.2 0.3 0 0 0 1';
client.send(testMessage, 8001, 'localhost', (err) => {
  if (err) console.error(err);
  else console.log('Test message sent');
  client.close();
});
```

2. Run the server and verify:
   - Message is received and parsed correctly
   - Device appears in statistics
   - Calibration works with new device
   - Data is sent to Python model

## Important Considerations

1. **Coordinate Systems**: Different platforms may use different coordinate systems. Document and handle these differences in your processor.

2. **Units**: Ensure acceleration is in m/s² and angular velocity in rad/s before sending to the model.

3. **Device Indices**: Maintain compatibility with MobilePoser's expected device order.

4. **Gravity Handling**: Determine if your device sends acceleration with or without gravity. Apply gravity removal if needed.

5. **Calibration**: The existing calibration system should work with new devices without modification.

## Example: Android Watch Implementation Summary

1. Message format: `ANDROID:watch:timestamp ax ay az qw qx qy qz`
2. Maps to index 1 (same as Apple Watch)
3. Acceleration might need unit conversion
4. No gravity removal needed (assuming linear acceleration)
5. Uses same calibration pipeline as iOS devices