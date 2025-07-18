// Main IMU WebSocket Server
// Handles iOS devices (iPhone, Watch, AirPods) and AR glasses data

const WebSocket = require('ws');
const UDPReceiver = require('./receivers/udp-receiver');
const UDPSender = require('./core/udp-sender');
const CalibrationManager = require('./core/calibration-manager');
const config = require('./config/default.json');

// CONFIGURATION FLAG
// Set to true to map AR glasses as headphone (index 2) for MobilePoser compatibility
// Set to false to use separate device index for AR glasses
const USE_AR_AS_HEADPHONE = true;

class IMUWebSocketServer {
  constructor() {
    // Load configuration
    this.config = config.server;
    this.port = this.config.websocketPort || 3001;
    this.udpPort = this.config.udpReceiverPort || 8001;
    this.udpSendPort = this.config.udpSenderPort || 9001;
    this.targetFPS = this.config.targetFPS || 30;
    
    // Initialize components
    this.clients = new Map();
    this.calibrationManager = new CalibrationManager();
    this.udpSender = new UDPSender(this.udpSendPort, '127.0.0.1', this.targetFPS);
    
    // Device tracking
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
    console.log(`📋 Configuration: USE_AR_AS_HEADPHONE = ${USE_AR_AS_HEADPHONE}`);
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

      // Send welcome message
      ws.send(JSON.stringify({
        type: 'connection',
        message: 'Connected to IMU WebSocket Server',
        stats: this.stats,
        clientId: clientId,
        config: {
          useARAsHeadphone: USE_AR_AS_HEADPHONE
        }
      }));

      // Handle client messages
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

    // Initialize UDP Receiver with device mapping flag
    this.udpReceiver = new UDPReceiver(this.udpPort, USE_AR_AS_HEADPHONE);
    this.udpReceiver.on('data', (deviceType, processedData, clientIP) => {
      this.handleIMUData(deviceType, processedData, clientIP);
    });

    // Start UDP receiver
    if (this.udpReceiver.start()) {
      // Start UDP sender
      if (this.udpSender.start()) {
        console.log(`🌐 WebSocket server listening on port ${this.port}`);
        console.log(`📡 UDP receiver active on port ${this.udpPort}`);
        console.log(`📤 UDP sender active on port ${this.udpSendPort} at ${this.targetFPS}Hz`);
        console.log('📱 Ready for IMU connections!');
        
        // Log stats periodically
        this.startStatsLogger();
        
        // Clean up old calibrations periodically
        setInterval(() => {
          this.calibrationManager.cleanup();
        }, 3600000); // Every hour
      } else {
        console.error('❌ Failed to start UDP sender');
        process.exit(1);
      }
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

  handleIMUData(deviceType, processedData, clientIP) {
    try {
      if (processedData) {
        // Update statistics
        this.stats[deviceType] = (this.stats[deviceType] || 0) + 1;
        
        // Track device capabilities
        const deviceIdentifier = `${processedData.device_name}-${clientIP}`;
        
        if (!this.deviceCapabilities[deviceIdentifier]) {
          this.deviceCapabilities[deviceIdentifier] = {
            device_name: processedData.device_name,
            device_type: deviceType,
            has_gyro: processedData.has_gyro,
            client_ip: clientIP,
            last_seen: new Date()
          };
          
          console.log(`📱 New device detected: ${processedData.device_name} from ${clientIP} (has_gyro: ${processedData.has_gyro ? 'YES' : 'NO'})`);
        } else {
          this.deviceCapabilities[deviceIdentifier].last_seen = new Date();
        }
        
        // Apply calibration for each connected client
        this.clients.forEach((client, clientId) => {
          let dataToSend = processedData;
          const calibrationData = this.calibrationManager.getCalibrationData(clientId);
          
          if (this.calibrationManager.getCalibrationStatus(clientId).isCalibrated) {
            // Apply calibration for this specific client
            dataToSend = this.calibrationManager.applyCalibration(clientId, processedData);
            
            // If fully calibrated, send to UDP sender
            if (calibrationData && calibrationData.isTPoseCalibrated && dataToSend.isCalibrated) {
              const deviceKey = `${dataToSend.device_name}_${dataToSend.device_id}`;
              this.udpSender.updateDeviceData(deviceKey, dataToSend, calibrationData);
            }
          }
          
          // Send to WebSocket client
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
      const total = this.stats.ios + this.stats.ar_glasses + (this.stats.unknown || 0) + this.stats.errors;
      
      if (total > 0) {
        console.log('\n📈 === IMU Server Statistics ===');
        console.log(`📱 iOS devices: ${this.stats.ios} packets`);
        console.log(`🥽 AR glasses: ${this.stats.ar_glasses} packets`);
        if (this.stats.unknown > 0) {
          console.log(`❓ Unknown: ${this.stats.unknown} packets`);
        }
        console.log(`❌ Errors: ${this.stats.errors} packets`);
        console.log(`🌐 Connected clients: ${this.stats.clients}`);
        
        // Log calibration status
        let calibratedClients = 0;
        let tposeCalibratedClients = 0;
        this.clients.forEach((client, clientId) => {
          const status = this.calibrationManager.getCalibrationStatus(clientId);
          if (status.isCalibrated) {
            calibratedClients++;
            if (status.isTPoseCalibrated) {
              tposeCalibratedClients++;
            }
          }
        });
        console.log(`📐 Calibrated clients: ${calibratedClients} (T-pose: ${tposeCalibratedClients})`);
        
        // Log UDP sender stats
        const senderStats = this.udpSender.getStatistics();
        if (senderStats.isRunning) {
          console.log(`📤 UDP Sender: ${senderStats.packetsSent} packets sent to port ${this.udpSendPort}`);
          console.log(`📤 Active devices in sender: ${senderStats.activeDevices}`);
        }
        
        // Log device capabilities
        if (Object.keys(this.deviceCapabilities).length > 0) {
          console.log('\n📱 Device Capabilities:');
          Object.values(this.deviceCapabilities).forEach(device => {
            const lastSeenTime = new Date(device.last_seen).toLocaleTimeString();
            console.log(`  - ${device.device_name} (${device.client_ip}): Gyroscope: ${device.has_gyro ? 'YES' : 'NO'} (Last seen: ${lastSeenTime})`);
          });
        }
        
        console.log(`📊 Total packets: ${total}`);
        console.log(`🔧 Device mapping: AR glasses as ${USE_AR_AS_HEADPHONE ? 'headphone (index 2)' : 'separate device'}`);
        console.log('===============================\n');
      }
    }, 30000); // Every 30 seconds
  }

  stop() {
    console.log('🛑 Shutting down IMU WebSocket Server...');
    
    if (this.udpReceiver) {
      this.udpReceiver.stop();
    }
    
    if (this.udpSender) {
      this.udpSender.stop();
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