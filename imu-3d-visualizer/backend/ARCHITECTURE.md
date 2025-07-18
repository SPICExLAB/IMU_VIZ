# IMU Backend Architecture

## Overview

The IMU backend is a modular system designed to receive, process, calibrate, and forward IMU sensor data from multiple device types. It maintains a unified coordinate frame across all devices and sends processed data to a Python model for pose estimation.

## Data Flow

```
iOS Devices (iPhone/Watch/AirPods) ─┐
                                    ├─→ UDP Port 8001 → Receiver → Parser → Processor ─┐
Unity/AR Glasses (Rokid) ───────────┘                                                   │
                                                                                        ├─→ Calibration Manager → UDP Sender → Python Model (Port 9001)
WebSocket Clients ─────────────────────→ Port 3001 → Calibration Commands ─────────────┘
```

## Component Architecture

### 1. Main Server (`server.js`)
- WebSocket server for client connections and calibration
- Orchestrates all components
- Manages statistics and monitoring
- Configuration flag: `USE_AR_AS_HEADPHONE`

### 2. Receivers (`receivers/`)
- **udp-receiver.js**: Main UDP listener, delegates to specific receivers
- **ios-receiver.js**: Handles iOS device data
- **unity-receiver.js**: Handles Unity/AR glasses data
- Base pattern for easy extension (e.g., android-receiver.js)

### 3. Parsers (`parsers/`)
- **ios-parser.js**: Parses iOS message format
- **unity-parser.js**: Parses Unity message format
- Validates data structure and extracts sensor values

### 4. Processors (`processors/`)
- **ios-processor.js**: 
  - Converts iOS acceleration from G to m/s²
  - Applies coordinate system corrections
  - Maps devices to indices
- **unity-processor.js**:
  - Removes gravity from acceleration
  - Applies bias correction
  - Handles device mapping based on `useARAsHeadphone` flag

### 5. Core Components (`core/`)
- **calibration-manager.js**: 
  - Stores per-client calibration data
  - Applies world frame transformations
  - Handles T-pose calibration
- **udp-sender.js**:
  - Sends calibrated data at 30Hz
  - Interpolates between samples
  - Formats data for MobilePoser model

### 6. Utilities (`utils/`)
- **rotation-utils.js**: Quaternion and matrix operations
- Mathematical functions for coordinate transformations

## Device Mapping

MobilePoser expects 5 devices in specific order:
- Index 0: Phone (iPhone)
- Index 1: Watch (Apple Watch)
- Index 2: Headphone (AirPods) OR AR Glasses (when `USE_AR_AS_HEADPHONE=true`)
- Index 3: Unused
- Index 4: AR Glasses (when `USE_AR_AS_HEADPHONE=false`)

## Calibration System

### World Frame Calibration
1. Client sends reference device quaternion
2. System calculates `smpl2imu` transformation matrix
3. All device data transformed to unified world frame

### T-pose Calibration
1. Client performs T-pose
2. System calculates device-to-bone matrices
3. Acceleration offsets computed for bias correction

## Message Formats

### iOS Format
```
device_id;device_type:timestamp1 timestamp2 ax ay az qx qy qz qw [gx gy gz]
```

### Unity/AR Format
```
timestamp device_timestamp qx qy qz qw ax ay az [gx gy gz] [lax lay laz]
```

### Output Format (to Python)
```json
{
  "type": "imu_data",
  "timestamp": 1234567890,
  "n_imus": 5,
  "glb_acc": [[ax,ay,az], ...],
  "glb_ori": [[[r11,r12,r13],[r21,r22,r23],[r31,r32,r33]], ...],
  "device_states": [true, true, true, false, false],
  "fps": 30
}
```

## Configuration

All configuration in `config/` directory:
- `default.json`: Server settings
- `device-mappings.json`: Device name to index mappings
- `rokid_calibration.json`: AR glasses bias calibration

## Extension Points

To add new device support (e.g., Android):
1. Create new receiver in `receivers/android-receiver.js`
2. Create new parser in `parsers/android-parser.js`
3. Create new processor in `processors/android-processor.js`
4. Update `device-mappings.json` with new device names
5. No changes needed to core calibration or sending logic