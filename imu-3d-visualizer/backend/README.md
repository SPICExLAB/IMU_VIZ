# IMU Backend Server

Real-time IMU data processing server for iOS devices (iPhone, Apple Watch, AirPods) and Rokid AR glasses. Handles sensor data reception, calibration, and unified coordinate frame transformation.

## Quick Start

```bash
# Install dependencies
npm install

# Start the server
npm start

# Server will start on:
# - WebSocket: port 3001
# - UDP Receiver: port 8001
# - UDP Sender: port 9001 (sends to Python model)
```

## Features

- **Multi-device Support**: iOS devices (iPhone, Watch, AirPods) and Rokid AR glasses
- **Real-time Processing**: 30Hz data streaming to Python model
- **Calibration System**: World frame alignment and T-pose calibration
- **Gravity Removal**: Built-in bias correction for AR glasses
- **Device Mapping**: Consistent device indexing (phone:0, watch:1, headphone/glasses:2)

## Configuration

### Device Mapping

Set `useARAsHeadphone` flag in `server.js`:
```javascript
// Map AR glasses as headphone (index 2) for MobilePoser compatibility
const USE_AR_AS_HEADPHONE = true; // Set to false to use separate index
```

### Ports Configuration

Default ports in `config/default.json`:
```json
{
  "server": {
    "websocketPort": 3001,
    "udpReceiverPort": 8001,
    "udpSenderPort": 9001,
    "targetFPS": 30
  }
}
```

## Data Flow

1. **iOS Devices** → UDP (port 8001) → Data Parser → Processor → Calibration
2. **AR Glasses** → UDP (port 8001) → Data Parser → Processor (gravity removal) → Calibration
3. **Calibrated Data** → UDP Sender (port 9001) → Python Model

## Calibration Process

1. **World Frame Calibration**: Aligns all devices to unified coordinate system
2. **T-pose Calibration**: Device-to-bone transformation matrices
3. **Acceleration Offset**: Removes sensor bias in rest position

## Adding New Device Support

See [docs/adding-devices.md](docs/adding-devices.md) for detailed guide on adding Android or other device support.

## Architecture

- `server.js` - Main entry point and WebSocket server
- `receivers/` - Device-specific UDP receivers
- `processors/` - Data processing for each device type
- `core/` - Core functionality (calibration, sending)
- `utils/` - Shared utilities and math operations

For detailed architecture, see [ARCHITECTURE.md](ARCHITECTURE.md)