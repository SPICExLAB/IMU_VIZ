const dgram = require('dgram');
const EventEmitter = require('events');
const { parseIOSMessage, parseARGlassesMessage } = require('./data-parser');

class UDPReceiver extends EventEmitter {
  constructor(port = 8001, host = '0.0.0.0') {
    super();
    this.port = port;
    this.host = host;
    this.socket = null;
    this.isRunning = false;
    
    // Statistics
    this.packetCount = 0;
    this.lastStatsTime = Date.now();
    
    console.log(`📡 UDP Receiver configured for ${host}:${port}`);
  }

  start() {
    try {
      // Create UDP socket
      this.socket = dgram.createSocket('udp4');
      
      // Handle incoming messages
      this.socket.on('message', (buffer, rinfo) => {
        this.handleIncomingMessage(buffer, rinfo);
      });

      // Handle socket events
      this.socket.on('listening', () => {
        const address = this.socket.address();
        console.log(`📡 UDP receiver listening on ${address.address}:${address.port}`);
        this.isRunning = true;
      });

      this.socket.on('error', (error) => {
        console.error('📡 UDP socket error:', error);
        this.isRunning = false;
      });

      this.socket.on('close', () => {
        console.log('📡 UDP socket closed');
        this.isRunning = false;
      });

      // Bind to port
      this.socket.bind(this.port, this.host);
      
      return true;
    } catch (error) {
      console.error('Failed to start UDP receiver:', error);
      return false;
    }
  }

  stop() {
    if (this.socket) {
      this.isRunning = false;
      this.socket.close();
      this.socket = null;
      console.log('📡 UDP receiver stopped');
    }
  }

  handleIncomingMessage(buffer, rinfo) {
    try {
      this.packetCount++;
      
      // Convert buffer to string
      const messageStr = buffer.toString('utf8').trim();
      const clientIP = rinfo.address;
      
      // Skip empty messages
      if (!messageStr) {
        return;
      }

      // Classify and parse the message
      const { deviceType, parsedData } = this.classifyAndParseMessage(messageStr, clientIP);
      
      if (deviceType && parsedData) {
        // Emit parsed data
        this.emit('data', deviceType, parsedData, clientIP);
        
        // Debug log occasionally
        if (this.packetCount % 500 === 0) {
          console.log(`📊 Processed ${this.packetCount} UDP packets`);
        }
      } else {
        // Log unknown format for debugging
        this.emit('data', 'unknown', { 
          raw: messageStr.substring(0, 100),
          from: clientIP 
        }, clientIP);
      }

    } catch (error) {
      console.error('Error handling UDP message:', error);
      this.emit('data', 'error', { 
        error: error.message,
        from: rinfo.address 
      }, rinfo.address);
    }
  }

  classifyAndParseMessage(messageStr, clientIP) {
    try {
      // Method 1: Try iOS format first (has semicolon and colon)
      // Format: "device_id;device_type:timestamp1 timestamp2 ax ay az qx qy qz qw [gx gy gz]"
      if (messageStr.includes(';') && messageStr.includes(':')) {
        const parsedData = parseIOSMessage(messageStr);
        if (parsedData) {
          return { deviceType: 'ios', parsedData };
        }
      }

      // Method 2: Try AR glasses format (space-separated numeric values)
      // Format: "timestamp device_timestamp qx qy qz qw ax ay az [gx gy gz]"
      const parts = messageStr.split(/\s+/);
      if (parts.length >= 9) {
        // Check if all required parts are numeric
        const numericParts = parts.slice(0, 9);
        const allNumeric = numericParts.every(part => {
          const num = parseFloat(part);
          return !isNaN(num) && isFinite(num);
        });

        if (allNumeric) {
          const parsedData = parseARGlassesMessage(messageStr);
          if (parsedData) {
            return { deviceType: 'ar_glasses', parsedData };
          }
        }
      }

      // Method 3: Check for Unity-style indicators
      if (messageStr.toLowerCase().includes('unity') || 
          (parts.length >= 9 && parts.every(p => !isNaN(parseFloat(p))))) {
        const parsedData = parseARGlassesMessage(messageStr);
        if (parsedData) {
          return { deviceType: 'ar_glasses', parsedData };
        }
      }

      // Unknown format
      console.log(`❓ Unknown message format from ${clientIP}: "${messageStr.substring(0, 50)}..."`);
      return { deviceType: null, parsedData: null };

    } catch (error) {
      console.error(`Error classifying message from ${clientIP}:`, error);
      return { deviceType: null, parsedData: null };
    }
  }

  getStatistics() {
    return {
      packetCount: this.packetCount,
      isRunning: this.isRunning,
      port: this.port,
      host: this.host
    };
  }
}

module.exports = UDPReceiver;