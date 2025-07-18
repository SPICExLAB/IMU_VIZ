# IMU 3D Visualizer

Real-time 3D visualization system for IMU sensor data from iOS devices and AR glasses.

## Prerequisites

- Node.js (v14.0.0 or higher)
- npm (comes with Node.js)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/SPICExLAB/INRTL.git
   cd INRTL/imu-3d-visualizer
   ```

2. **Install all dependencies**
   ```bash
   npm run install:all
   ```

## Running the Application

Start both backend and frontend:

```bash
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend WebSocket: ws://localhost:3001
- UDP Receiver: Port 8001

For more detailed information, see [backend/README.md](backend/README.md).