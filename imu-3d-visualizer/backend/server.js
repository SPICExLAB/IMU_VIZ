const WebSocket = require('ws');
const UDPReceiver = require('./udp-receiver');
const DataProcessor = require('./data-processor');

class IMUWebSocketServer {
  constructor() {
    this.port = 3001;
    this.udpPort = 8001;
    this.clients = new Set();
    this.dataProcessor = new DataProcessor();
    
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
      
      this.clients.add(ws);
      this.stats.clients = this.clients.size;

      // Send welcome message with current stats
      ws.send(JSON.stringify({
        type: 'connection',
        message: 'Connected to IMU WebSocket Server',
        stats: this.stats,
        clientId: clientId
      }));

      ws.on('close', (code, reason) => {
        this.clients.delete(ws);
        this.stats.clients = this.clients.size;
        console.log(`📱 Client disconnected: ${clientId} (code: ${code})`);
      });

      ws.on('error', (error) => {
        console.error(`WebSocket error from ${clientId}:`, error.message);
        this.clients.delete(ws);
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
    } else {
      console.error('❌ Failed to start UDP receiver');
      process.exit(1);
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
        
        // Broadcast to all connected clients
        const message = JSON.stringify({
          type: 'imu_data',
          deviceType,
          data: processedData,
          timestamp: Date.now(),
          clientIP
        });

        this.broadcastToClients(message);

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

  broadcastToClients(message) {
    if (this.clients.size === 0) return;

    // Remove disconnected clients and send to active ones
    const deadClients = [];
    
    this.clients.forEach(ws => {
      if (ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(message);
        } catch (error) {
          console.error('Error sending to client:', error);
          deadClients.push(ws);
        }
      } else {
        deadClients.push(ws);
      }
    });

    // Clean up dead connections
    deadClients.forEach(ws => {
      this.clients.delete(ws);
    });
    
    this.stats.clients = this.clients.size;
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
    }, 30000); // Every 30 seconds instead of 10
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