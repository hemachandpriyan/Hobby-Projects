import serial
import requests
import time
import re

# --- CONFIGURATION ---
SERIAL_PORT = "/dev/serial0"    # Default Pi serial interface
BAUD_RATE = 115200               # Make sure this matches the rate you used in your diagnostic code
TOPIC_NAME = "my_home_mmwave_sensor_99"

MAX_DISTANCE_CM = 200            # Alert threshold in cm
COOLDOWN_SECONDS = 60           # Avoid spamming notifications

def send_push_notification(distance_cm):
    url = f"https://ntfy.sh/human_detection_hcp"
    message = f"Alert: Human detected at {distance_cm} cm!"
    try:
        requests.post(url, data=message.encode('utf-8'), timeout=10)
        print(f"[{time.strftime('%H:%M:%S')}] Push notification sent successfully!")
    except Exception as e:
        print(f"Error sending notification: {e}")

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to mmWave sensor on {SERIAL_PORT} @ {BAUD_RATE} baud.")
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return

    last_send_time = 0
    current_distance = None
    human_present = False

    print(f"Monitoring distance... (Trigger set to <= {MAX_DISTANCE_CM} cm)")

    try:
        while True:
            # Read a full text line
            raw_line = ser.readline()
            if not raw_line:
                continue

            # Decode into clean text string
            line = raw_line.decode('utf-8', errors='ignore').strip()
            
            if not line:
                continue

            # 1. Parse 'ON' / 'OFF' detection state
            if line == "ON":
                human_present = True
            elif line == "OFF":
                human_present = False
                current_distance = None  # Reset distance when no human is present

            # 2. Extract distance integer from lines like 'Range 98'
            if "Range" in line:
                # Use regex to safely extract the digits following 'Range'
                match = re.search(r'Range\s*(\d+)', line, re.IGNORECASE)
                if match:
                    current_distance = int(match.group(1))

            # 3. Evaluate Alert Conditions
            if human_present and current_distance is not None:
                print(f"Human Present: {human_present} | Distance: {current_distance} cm")
                
                # Check if target is within <= 200cm
                if current_distance <= MAX_DISTANCE_CM:
                    current_time = time.time()
                    
                    if current_time - last_send_time > COOLDOWN_SECONDS:
                        print(f"--> ALERT: Human detected at {current_distance}cm (<= {MAX_DISTANCE_CM}cm)! Triggering push notification...")
                        send_push_notification(current_distance)
                        last_send_time = current_time

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping sensor monitor...")
        ser.close()

if __name__ == "__main__":
    main()
