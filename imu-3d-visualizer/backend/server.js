// backend/server.js - Updated with calibration support
const WebSocket = require('ws');
const UDPReceiver = require('./udp-receiver');
const DataProcessor = require('./data-processor');
const CalibrationManager = require('./calibration-manager');

class IMUWebSocketServer {
  constructor() {
    this.port = 3001;
    this.udpPort = 8001;
    this.clients = new Map(); // Changed to Map for better client tracking
    this.dataProcessor = new DataProcessor();
    this.calibrationManager = new CalibrationManager();
    
    // Add device tracking for gyro capabilities
    this.deviceCapabilities = {};
    
    // Statistics
    this.stats = {
      ios: 0,
      ar_glasses: 0,
      unknown: 0,
      errors: 0,
      clients: 0
    };
    
    console.log('🚀 IMU WebSocket Server initializing...');
  }

  start() {
    // Initialize WebSocket Server
    this.wss = new WebSocket.Server({ 
      port: this.port,
      perMessageDeflate: false // Disable compression for lower latency
    });

    this.wss.on('connection', (ws, req) => {
      const clientIP = req.socket.remoteAddress;
      const clientId = `${clientIP}:${req.socket.remotePort}`;
      console.log(`📱 Client connected: ${clientId}`);
      
      // Store client with metadata
      this.clients.set(clientId, {
        ws: ws,
        ip: clientIP,
        connectedAt: Date.now()
      });
      this.stats.clients = this.clients.size;

      // Send welcome message with current stats
      ws.send(JSON.stringify({
        type: 'connection',
        message: 'Connected to IMU WebSocket Server',
        stats: this.stats,
        clientId: clientId
      }));

      // Handle client messages (including calibration)
      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data);
          this.handleClientMessage(clientId, message);
        } catch (error) {
          console.error(`Error parsing message from ${clientId}:`, error);
        }
      });

      ws.on('close', (code, reason) => {
        this.clients.delete(clientId);
        this.calibrationManager.clearCalibration(clientId);
        this.stats.clients = this.clients.size;
        console.log(`📱 Client disconnected: ${clientId} (code: ${code})`);
      });

      ws.on('error', (error) => {
        console.error(`WebSocket error from ${clientId}:`, error.message);
        this.clients.delete(clientId);
        this.calibrationManager.clearCalibration(clientId);
        this.stats.clients = this.clients.size;
      });
    });

    // Initialize UDP Receiver
    this.udpReceiver = new UDPReceiver(this.udpPort);
    this.udpReceiver.on('data', (deviceType, rawData, clientIP) => {
      this.handleIMUData(deviceType, rawData, clientIP);
    });

    // Start UDP listener
    if (this.udpReceiver.start()) {
      console.log(`🌐 WebSocket server listening on port ${this.port}`);
      console.log(`📡 UDP listener active on port ${this.udpPort}`);
      console.log('📱 Ready for IMU connections!');
      
      // Log stats periodically
      this.startStatsLogger();
      
      // Clean up old calibrations periodically
      setInterval(() => {
        this.calibrationManager.cleanup();
      }, 3600000); // Every hour
    } else {
      console.error('❌ Failed to start UDP receiver');
      process.exit(1);
    }
  }

  handleClientMessage(clientId, message) {
    switch (message.type) {
      case 'calibration':
        console.log(`📐 Received calibration from client ${clientId}`);
        this.calibrationManager.setCalibration(clientId, message.data);
        
        // Send confirmation
        const client = this.clients.get(clientId);
        if (client && client.ws.readyState === WebSocket.OPEN) {
          client.ws.send(JSON.stringify({
            type: 'calibration_confirmed',
            clientId: clientId,
            timestamp: Date.now()
          }));
        }
        break;
        
      case 'tpose_calibration':
        console.log(`🙆 Received T-pose calibration from client ${clientId}`);
        this.calibrationManager.setTPoseCalibration(clientId, message.data);
        
        // Send confirmation
        const tposeClient = this.clients.get(clientId);
        if (tposeClient && tposeClient.ws.readyState === WebSocket.OPEN) {
          tposeClient.ws.send(JSON.stringify({
            type: 'tpose_calibration_confirmed',
            clientId: clientId,
            timestamp: Date.now()
          }));
        }
        break;
        
      case 'reset_calibration':
        console.log(`🔄 Resetting calibration for client ${clientId}`);
        this.calibrationManager.clearCalibration(clientId);
        break;
        
      default:
        console.log(`Unknown message type from ${clientId}:`, message.type);
    }
  }

  handleIMUData(deviceType, rawData, clientIP) {
    try {
      // Process the raw data
      const processedData = this.dataProcessor.processDeviceData(deviceType, rawData);
      
      if (processedData) {
        // Update statistics
        this.stats[deviceType]++;
        
        // Track device capabilities for better reporting
        const deviceIdentifier = `${processedData.device_name}-${clientIP}`;
        
        // Update device capabilities tracking
        if (!this.deviceCapabilities[deviceIdentifier]) {
          this.deviceCapabilities[deviceIdentifier] = {
            device_name: processedData.device_name,
            device_type: deviceType,
            has_gyro: processedData.has_gyro,
            client_ip: clientIP,
            last_seen: new Date()
          };
          
          // Log when we detect a new device
          console.log(`📱 New device detected: ${processedData.device_name} from ${clientIP} (has_gyro: ${processedData.has_gyro ? 'YES' : 'NO'})`);
        } else {
          // Update last seen time
          this.deviceCapabilities[deviceIdentifier].last_seen = new Date();
        }
        
        // Apply calibration for each connected client
        this.clients.forEach((client, clientId) => {
          // Check if this client has calibration
          let dataToSend = processedData;
          
          if (this.calibrationManager.getCalibrationStatus(clientId)) {
            // Apply calibration for this specific client
            dataToSend = this.calibrationManager.applyCalibration(clientId, processedData);
          }
          
          // Send to this specific client
          if (client.ws.readyState === WebSocket.OPEN) {
            const message = JSON.stringify({
              type: 'imu_data',
              deviceType,
              data: dataToSend,
              timestamp: Date.now(),
              clientIP
            });
            
            try {
              client.ws.send(message);
            } catch (error) {
              console.error(`Error sending to client ${clientId}:`, error);
            }
          }
        });

        // Log occasionally
        const totalCount = this.stats[deviceType];
        if (totalCount % 100 === 0) {
          console.log(`📊 ${deviceType}: ${totalCount} packets from ${clientIP}`);
        }
      } else {
        this.stats.errors++;
      }
    } catch (error) {
      console.error('Error processing IMU data:', error);
      this.stats.errors++;
    }
  }

  startStatsLogger() {
    setInterval(() => {
      const total = this.stats.ios + this.stats.ar_glasses + this.stats.unknown + this.stats.errors;
      
      if (total > 0) {
        console.log('\n📈 === IMU Server Statistics ===');
        console.log(`📱 iOS devices: ${this.stats.ios} packets`);
        console.log(`🥽 AR glasses: ${this.stats.ar_glasses} packets`);
        console.log(`❓ Unknown: ${this.stats.unknown} packets`);
        console.log(`❌ Errors: ${this.stats.errors} packets`);
        console.log(`🌐 Connected clients: ${this.stats.clients}`);
        
        // Log calibration status
        let calibratedClients = 0;
        this.clients.forEach((client, clientId) => {
          if (this.calibrationManager.getCalibrationStatus(clientId)) {
            calibratedClients++;
          }
        });
        console.log(`📐 Calibrated clients: ${calibratedClients}`);
        
        // Log device capabilities
        if (Object.keys(this.deviceCapabilities).length > 0) {
          console.log('\n📱 Device Capabilities:');
          Object.values(this.deviceCapabilities).forEach(device => {
            const lastSeenTime = new Date(device.last_seen).toLocaleTimeString();
            console.log(`  - ${device.device_name} (${device.client_ip}): Gyroscope: ${device.has_gyro ? 'YES' : 'NO'} (Last seen: ${lastSeenTime})`);
          });
        }
        
        console.log(`📊 Total packets: ${total}`);
        console.log('===============================\n');
      } else if (this.stats.clients > 0) {
        // Only log this every 30 seconds when no data
        if (Date.now() % 30000 < 10000) {
          console.log(`⏳ Ready for IMU data (${this.stats.clients} clients connected)`);
        }
      }
    }, 30000); // Every 30 seconds
  }

  stop() {
    console.log('🛑 Shutting down IMU WebSocket Server...');
    
    if (this.udpReceiver) {
      this.udpReceiver.stop();
    }
    
    if (this.wss) {
      this.wss.close();
    }
    
    console.log('✅ Server stopped');
  }
}

// Start the server
const server = new IMUWebSocketServer();

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Received SIGINT, shutting down gracefully...');
  server.stop();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Received SIGTERM, shutting down gracefully...');
  server.stop();
  process.exit(0);
});

// Start the server
server.start();