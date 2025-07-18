# IMU Backend Setup Guide

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Network access for UDP ports 8001 and 9001
- WebSocket port 3001

## Installation

1. **Clone or download the repository**

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure AR glasses calibration**
   - Ensure `config/rokid_calibration.json` exists
   - If not, copy from your Python calibration script output

## Configuration

### 1. Device Mapping (Important!)

In `server.js`, set the device mapping flag:
```javascript
const USE_AR_AS_HEADPHONE = true;  // Set based on your needs
```

- `true`: AR glasses will use index 2 (headphone slot) - recommended for MobilePoser
- `false`: AR glasses will use index 4 (separate device)

### 2. Network Configuration

Edit `config/default.json` if you need to change ports:
```json
{
  "server": {
    "websocketPort": 3001,      // WebSocket for frontend
    "udpReceiverPort": 8001,    // UDP for IMU data
    "udpSenderPort": 9001,      // UDP to Python model
    "targetFPS": 30
  }
}
```

### 3. AR Glasses Calibration

The bias calibration file should be at `config/rokid_calibration.json`:
```json
{
  "version": "2.1",
  "device": "Rokid AR Glasses",
  "bias": [-0.144, -0.966, -0.290],
  "method": "multi-position"
}
```

## Running the Server

### Development Mode (with auto-restart)
```bash
npm run dev
```

### Production Mode
```bash
npm start
```

You should see:
```
🚀 IMU WebSocket Server initializing...
📋 Configuration: USE_AR_AS_HEADPHONE = true
🌐 WebSocket server listening on port 3001
📡 UDP receiver active on port 8001
📤 UDP sender active on port 9001 at 30Hz
📱 Ready for IMU connections!
```

## Verifying Setup

### 1. Check iOS Device Connection
- Run your iOS app with iPhone/Watch/AirPods
- Server should log: `📱 New device detected: phone from 192.168.x.x`

### 2. Check AR Glasses Connection
- Run Unity app on Rokid glasses
- Server should log: `🥽 New device detected: glasses from 192.168.x.x`

### 3. Check WebSocket Connection
- Frontend should connect to `ws://localhost:3001`
- Server should log: `📱 Client connected: 127.0.0.1:xxxxx`

### 4. Check Calibration
- Perform calibration from frontend
- Server should log: `📐 Received calibration from client`
- After T-pose: `🙆 Received T-pose calibration from client`

### 5. Check Python Model Connection
- Run your Python receiver on port 9001
- Should receive JSON packets at 30Hz with calibrated data

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :8001  # Mac/Linux
netstat -ano | findstr :8001  # Windows

# Kill the process or change port in config
```

### No Data Received
1. Check firewall settings for UDP ports
2. Verify device is on same network
3. Check device app is sending to correct IP/port

### Calibration Not Working
1. Ensure frontend sends calibration data correctly
2. Check console for calibration confirmation messages
3. Verify T-pose is performed correctly

### AR Glasses Linear Acceleration Issues
1. Check `rokid_calibration.json` exists and is valid
2. Look for: `✅ AR Glasses calibration loaded` in logs
3. If missing, acceleration won't be bias-corrected

## Directory Structure After Setup

```
imu-backend/
├── node_modules/
├── config/
│   ├── default.json
│   ├── device-mappings.json
│   └── rokid_calibration.json
├── core/
│   ├── calibration-manager.js
│   └── udp-sender.js
├── receivers/
│   ├── udp-receiver.js
│   ├── ios-receiver.js
│   └── unity-receiver.js
├── processors/
│   ├── ios-processor.js
│   └── unity-processor.js
├── parsers/
│   ├── ios-parser.js
│   └── unity-parser.js
├── utils/
│   └── rotation-utils.js
├── docs/
│   └── adding-devices.md
├── server.js
├── package.json
├── README.md
├── SETUP.md
└── ARCHITECTURE.md
```

## Next Steps

1. Start developing your frontend calibration UI
2. Set up Python model to receive data on port 9001
3. Test full pipeline: devices → backend → Python model
4. Add Android support following the guide in `docs/adding-devices.md`