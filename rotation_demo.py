"""
Clean Rotation Comparison Demo - Socket-based API
File: rotation_demo.py

Usage:
1. First run: python IMU_receiver.py
2. Then run: python rotation_demo.py
"""

import time
import numpy as np
from scipy.spatial.transform import Rotation as R

# Import the clean socket-based API
from imu_data_api import get_imu_api

def compare_rotations():
    """Compare rotation data between glasses and phone"""
    print("=== Rotation Comparison Demo (Socket API) ===")
    
    try:
        # Get API (automatically connects to running receiver via socket)
        api = get_imu_api()
    except RuntimeError as e:
        print(f"❌ {e}")
        print("Please start IMU_receiver.py first")
        return
    
    print("Move both devices together to compare their rotation vectors")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            # Get glasses and phone data via socket API
            glasses_data = api.get_device_data('glasses')
            phone_data = api.get_device_data('phone')
            
            if glasses_data and phone_data:
                if glasses_data.is_calibrated and phone_data.is_calibrated:
                    # Get rotation matrices
                    glasses_rot = glasses_data.rotation_matrix
                    phone_rot = phone_data.rotation_matrix
                    
                    # Convert to Euler angles for easier comparison
                    glasses_euler = R.from_matrix(glasses_rot).as_euler('xyz', degrees=True)
                    phone_euler = R.from_matrix(phone_rot).as_euler('xyz', degrees=True)
                    
                    # Clear screen and print comparison
                    print("\033[2J\033[H")  # Clear screen
                    print("=== ROTATION COMPARISON (Socket API) ===")
                    print(f"Timestamp: {time.strftime('%H:%M:%S')}")
                    print()
                    
                    print("EULER ANGLES (degrees):")
                    print(f"Glasses:  X={glasses_euler[0]:+7.2f}°  Y={glasses_euler[1]:+7.2f}°  Z={glasses_euler[2]:+7.2f}°")
                    print(f"Phone:    X={phone_euler[0]:+7.2f}°  Y={phone_euler[1]:+7.2f}°  Z={phone_euler[2]:+7.2f}°")
                    print(f"Diff:     X={glasses_euler[0]-phone_euler[0]:+7.2f}°  Y={glasses_euler[1]-phone_euler[1]:+7.2f}°  Z={glasses_euler[2]-phone_euler[2]:+7.2f}°")
                    print()
                    
                    print("ACCELERATION COMPARISON:")
                    glasses_acc = glasses_data.acceleration
                    phone_acc = phone_data.acceleration
                    print(f"Glasses:  X={glasses_acc[0]:+7.3f}  Y={glasses_acc[1]:+7.3f}  Z={glasses_acc[2]:+7.3f}  |mag|={np.linalg.norm(glasses_acc):.3f}")
                    print(f"Phone:    X={phone_acc[0]:+7.3f}  Y={phone_acc[1]:+7.3f}  Z={phone_acc[2]:+7.3f}  |mag|={np.linalg.norm(phone_acc):.3f}")
                    print(f"Diff:     X={glasses_acc[0]-phone_acc[0]:+7.3f}  Y={glasses_acc[1]-phone_acc[1]:+7.3f}  Z={glasses_acc[2]-phone_acc[2]:+7.3f}")
                    print()
                    
                    print("FREQUENCIES:")
                    print(f"Glasses: {glasses_data.frequency:.1f} Hz")
                    print(f"Phone:   {phone_data.frequency:.1f} Hz")
                    print()
                    
                    # Gyroscope comparison if available
                    if glasses_data.gyroscope is not None:
                        print("GYROSCOPE COMPARISON:")
                        glasses_gyro = glasses_data.gyroscope
                        phone_gyro = phone_data.gyroscope if phone_data.gyroscope is not None else np.array([0, 0, 0])
                        print(f"Glasses:  X={glasses_gyro[0]:+7.3f}  Y={glasses_gyro[1]:+7.3f}  Z={glasses_gyro[2]:+7.3f}  |mag|={np.linalg.norm(glasses_gyro):.3f}")
                        print(f"Phone:    X={phone_gyro[0]:+7.3f}  Y={phone_gyro[1]:+7.3f}  Z={phone_gyro[2]:+7.3f}  |mag|={np.linalg.norm(phone_gyro):.3f}")
                        print()
                    
                    # Check axis alignment
                    axis_analysis = []
                    for i, axis in enumerate(['X', 'Y', 'Z']):
                        diff = abs(glasses_euler[i] - phone_euler[i])
                        sum_abs = abs(glasses_euler[i] + phone_euler[i])
                        
                        if diff < 5:  # Very close values
                            axis_analysis.append(f"✅ {axis}: ALIGNED (diff={diff:.1f}°)")
                        elif sum_abs < diff:  # Values are opposite
                            axis_analysis.append(f"🔄 {axis}: FLIPPED (anti-corr={sum_abs:.1f}°)")
                        else:
                            axis_analysis.append(f"⚠️  {axis}: OFFSET (diff={diff:.1f}°)")
                    
                    print("AXIS ANALYSIS:")
                    for analysis in axis_analysis:
                        print(analysis)
                    print()
                    
                    print("CONNECTION STATUS:")
                    print(f"📡 API server: Connected (port 9001)")
                    print(f"⏱️  Data timestamps - Glasses: {glasses_data.timestamp:.3f}, Phone: {phone_data.timestamp:.3f}")
                    print()
                    
                    print("INSTRUCTIONS:")
                    print("1. Hold both devices together and rotate them as one unit")
                    print("2. Watch the Euler angles - they should change together")
                    print("3. Look for FLIPPED axes (values go opposite directions)")
                    print("4. Press Ctrl+C to exit")
                    
                else:
                    print("⏳ Waiting for both devices to be calibrated...")
                    print(f"Glasses calibrated: {glasses_data.is_calibrated if glasses_data else False}")
                    print(f"Phone calibrated: {phone_data.is_calibrated if phone_data else False}")
                    print("👆 Press the CALIBRATE button in the IMU receiver window!")
            else:
                print("⏳ Waiting for both glasses and phone to be active...")
                active_devices = api.get_active_devices()
                print(f"Active devices: {active_devices}")
                if len(active_devices) == 0:
                    print("🔌 Make sure IMU_receiver.py is running and devices are connected!")
            
            time.sleep(0.1)  # Update 10 times per second
            
    except KeyboardInterrupt:
        print("\n\n✨ Demo finished!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Connection to IMU receiver lost. Make sure IMU_receiver.py is still running.")
    finally:
        # Close API connection
        try:
            api.close()
        except:
            pass



if __name__ == "__main__":

    
    compare_rotations()