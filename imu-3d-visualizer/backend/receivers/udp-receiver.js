// UDP Receiver - Main entry point for all IMU data
// Delegates to specific receivers based on data format

const dgram = require('dgram');
const EventEmitter = require('events');
const IOSReceiver = require('./ios-receiver');
const UnityReceiver = require('./unity-receiver');

class UDPReceiver extends EventEmitter {
  constructor(port = 8001, useARAsHeadphone = true, host = '0.0.0.0') {
    super();
    this.port = port;
    this.host = host;
    this.useARAsHeadphone = useARAsHeadphone;
    this.socket = null;
    this.isRunning = false;
    
    // Initialize device-specific receivers
    this.iosReceiver = new IOSReceiver();
    this.unityReceiver = new UnityReceiver(useARAsHeadphone);
    
    // Statistics
    this.packetCount = 0;
    this.lastStatsTime = Date.now();
    
    console.log(`📡 UDP Receiver configured for ${host}:${port}`);
    console.log(`📋 AR Glasses mapping: ${useARAsHeadphone ? 'as headphone (index 2)' : 'separate device'}`);
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

      // Try iOS format first (has semicolon and colon)
      if (messageStr.includes(';') && messageStr.includes(':')) {
        const result = this.iosReceiver.process(messageStr, clientIP);
        if (result) {
          this.emit('data', 'ios', result, clientIP);
          return;
        }
      }

      // Try Unity/AR glasses format (space-separated numbers)
      const result = this.unityReceiver.process(messageStr, clientIP);
      if (result) {
        this.emit('data', 'ar_glasses', result, clientIP);
        return;
      }

      // Unknown format
      if (this.packetCount % 100 === 0) {
        console.log(`❓ Unknown message format from ${clientIP}: "${messageStr.substring(0, 50)}..."`);
      }
      this.emit('data', 'unknown', { 
        raw: messageStr.substring(0, 100),
        from: clientIP 
      }, clientIP);

    } catch (error) {
      console.error('Error handling UDP message:', error);
      this.emit('data', 'error', { 
        error: error.message,
        from: rinfo.address 
      }, rinfo.address);
    }
  }

  getStatistics() {
    return {
      packetCount: this.packetCount,
      isRunning: this.isRunning,
      port: this.port,
      host: this.host,
      useARAsHeadphone: this.useARAsHeadphone
    };
  }
}

module.exports = UDPReceiver;