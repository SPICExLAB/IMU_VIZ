import React from 'react';
import { Wifi, WifiOff, RotateCcw } from 'lucide-react';

export default function ConnectionStatus({ status, deviceCount, stats }) {
  const getStatusIcon = () => {
    switch (status) {
      case 'connected':
        return <Wifi className="status-icon connected" />;
      case 'reconnecting':
        return <RotateCcw className="status-icon reconnecting" />;
      default:
        return <WifiOff className="status-icon disconnected" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected':
        return 'Connected to WebSocket Server';
      case 'reconnecting':
        return 'Reconnecting...';
      case 'error':
        return 'Connection Error';
      default:
        return 'Disconnected from Server';
    }
  };

  const totalPackets = (stats.ios || 0) + (stats.ar_glasses || 0) + (stats.unknown || 0);

  return (
    <div className={`connection-status ${status}`}>
      <div className="status-left">
        {getStatusIcon()}
        <span className="status-text">{getStatusText()}</span>
        {status === 'connected' && (
          <span className="status-details">
            • {deviceCount} device{deviceCount !== 1 ? 's' : ''} active
            • {totalPackets.toLocaleString()} packets received
          </span>
        )}
      </div>
      
      <div className="status-right">
        <div className="status-indicator-group">
          <div className="indicator">
            <span className="indicator-label">WebSocket:</span>
            <span className={`indicator-value ${status}`}>
              {status === 'connected' ? 'ws://localhost:3001' : 'Offline'}
            </span>
          </div>
          
          {status === 'connected' && (
            <div className="indicator">
              <span className="indicator-label">UDP Listener:</span>
              <span className="indicator-value connected">Port 8001</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}