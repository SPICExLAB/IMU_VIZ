import socket
import numpy as np
import time

class CleanIMUReceiver:
    def __init__(self, host='0.0.0.0', port=8001):
        """Receive clean, remapped IMU data from Unity"""
        self.host = host
        self.port = port
        
        # Socket setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        print(f"🎯 Listening for clean IMU data on {self.host}:{self.port}")
        
    def parse_clean_imu_data(self, data_str):
        """Parse the clean IMU data from Unity"""
        try:
            values = data_str.strip().split()
            if len(values) != 11:
                print(f"Expected 11 values, got {len(values)}")
                return None
                
            return {
                'timestamp': float(values[0]),
                'device_time': float(values[1]),
                'nod': float(values[2]),           # Up/down head movement (degrees)
                'tilt': float(values[3]),          # Left/right head tilt (degrees)
                'turn': float(values[4]),          # Left/right head rotation (degrees)
                'acc_x': float(values[5]),         # Right/left acceleration (right is +)
                'acc_y': float(values[6]),         # Up/down acceleration (up is +)
                'acc_z': float(values[7]),         # Forward/back acceleration (forward is +)
                'gyro_nod': float(values[8]),      # Nod angular velocity (rad/s)
                'gyro_turn': float(values[9]),     # Turn angular velocity (rad/s)
                'gyro_tilt': float(values[10])     # Tilt angular velocity (rad/s)
            }
        except (ValueError, IndexError) as e:
            print(f"Error parsing data: {e}")
            return None
    
    def display_clean_data(self, data):
        """Display the clean IMU data"""
        print("\n" + "="*60)
        print(f"⏰ Time: {data['timestamp']:.3f} | Device: {data['device_time']:.3f}")
        
        # Head orientation in intuitive terms
        print(f"\n🎯 HEAD ORIENTATION:")
        print(f"  NOD (up/down):     {data['nod']:8.1f}°")
        print(f"  TILT (left/right): {data['tilt']:8.1f}°") 
        print(f"  TURN (left/right): {data['turn']:8.1f}°")
        
        # Acceleration with corrected coordinate system
        acc_magnitude = np.sqrt(data['acc_x']**2 + data['acc_y']**2 + data['acc_z']**2)
        print(f"\n🚀 ACCELERATION (includes gravity):")
        print(f"  Right/Left:    {data['acc_x']:8.3f} m/s² (+ is RIGHT)")
        print(f"  Up/Down:       {data['acc_y']:8.3f} m/s² (+ is UP)")
        print(f"  Forward/Back:  {data['acc_z']:8.3f} m/s² (+ is FORWARD)")
        print(f"  Magnitude:     {acc_magnitude:.3f} m/s²")
        
        # Angular velocities
        print(f"\n🔄 ANGULAR VELOCITY:")
        print(f"  Nod rate:      {data['gyro_nod']:8.3f} rad/s")
        print(f"  Turn rate:     {data['gyro_turn']:8.3f} rad/s")
        print(f"  Tilt rate:     {data['gyro_tilt']:8.3f} rad/s")
        
        # Movement interpretation
        print(f"\n💡 INTERPRETATION:")
        movements = []
        
        if abs(data['nod']) > 10:
            direction = "UP" if data['nod'] > 0 else "DOWN"
            movements.append(f"Looking {direction} ({abs(data['nod']):.1f}°)")
        
        if abs(data['tilt']) > 10:
            direction = "RIGHT" if data['tilt'] > 0 else "LEFT"
            movements.append(f"Tilted {direction} ({abs(data['tilt']):.1f}°)")
            
        if abs(data['turn']) > 10:
            direction = "LEFT" if data['turn'] > 0 else "RIGHT" 
            movements.append(f"Turned {direction} ({abs(data['turn']):.1f}°)")
        
        if movements:
            for movement in movements:
                print(f"  📍 {movement}")
        else:
            print(f"  📍 Head position: LEVEL")
            
        # Gravity analysis
        if acc_magnitude > 9.5:  # Close to gravity
            primary_axis = max(['acc_x', 'acc_y', 'acc_z'], key=lambda k: abs(data[k]))
            direction_map = {
                'acc_x': f"{'RIGHT' if data['acc_x'] > 0 else 'LEFT'}",
                'acc_y': f"{'UP' if data['acc_y'] > 0 else 'DOWN'}",
                'acc_z': f"{'FORWARD' if data['acc_z'] > 0 else 'BACKWARD'}"
            }
            print(f"  🌍 Gravity primarily in {direction_map[primary_axis]} direction")
    
    def run(self, display_interval=1.0):
        """Main loop to receive and display clean IMU data"""
        print("\n🎮 Clean IMU Data Receiver")
        print("Unity is doing all the coordinate remapping!")
        print("Move your head to see clean, intuitive data")
        print("Press Ctrl+C to stop\n")
        
        last_display_time = time.time()
        
        try:
            while True:
                data, addr = self.sock.recvfrom(1024)
                data_str = data.decode('utf-8')
                
                imu_data = self.parse_clean_imu_data(data_str)
                if imu_data is None:
                    continue
                
                current_time = time.time()
                if current_time - last_display_time > display_interval:
                    self.display_clean_data(imu_data)
                    last_display_time = current_time
                    
        except KeyboardInterrupt:
            print("\n\nStopping clean IMU receiver...")
        finally:
            self.sock.close()

def main():
    """Main function"""
    print("🎯 Rokid AR Glasses - Clean IMU Data Receiver")
    print("=" * 50)
    print("Expected coordinate system:")
    print("  📍 NOD: + = looking up, - = looking down")
    print("  📍 TILT: + = tilting right, - = tilting left") 
    print("  📍 TURN: + = turning left, - = turning right")
    print("  📍 ACC_X: + = right, - = left")
    print("  📍 ACC_Y: + = up, - = down")
    print("  📍 ACC_Z: + = forward, - = backward")
    
    receiver = CleanIMUReceiver()
    
    try:
        rate = float(input("\nDisplay update rate in seconds (default 1.0): ") or "1.0")
    except ValueError:
        rate = 1.0
    
    try:
        receiver.run(display_interval=rate)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()