import serial
import time
import sys

# --------------------------------------------------------------------------
# WIRING INSTRUCTIONS
# --------------------------------------------------------------------------
# SIM800L VCC -> External Power (3.7V - 4.2V) or 5V if it has regulator
# SIM800L GND -> Raspberry Pi GND (Pin 6) AND Power Source GND
# SIM800L TX  -> Raspberry Pi RX  (Pin 10 / GPIO 15)
# SIM800L RX  -> Raspberry Pi TX  (Pin 8  / GPIO 14)
# --------------------------------------------------------------------------

def send_at(command, wait_time=1):
    print(f"Sending: {command}")
    ser.write((command + "\r\n").encode())
    time.sleep(wait_time)
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"Response:\n{response}")
        return response
    else:
        print("No response")
        return ""

try:
    # Open Serial Port (usually /dev/serial0 or /dev/ttyS0 on Pi)
    ser = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)
    if not ser.isOpen():
        print("Error: Serial port not open")
        sys.exit()
    print("Serial port opened successfully.")
except Exception as e:
    print(f"Failed to open serial port: {e}")
    print("Did you enable Serial in raspi-config?")
    sys.exit()

try:
    # 1. Basic handshake
    send_at("AT") 
    
    # 2. Check signal strength
    send_at("AT+CSQ")
    
    # 3. Check SIM card status
    send_at("AT+CPIN?")
    
    # 4. Check Network Registration
    # 0,1 = Registered Home Network
    # 0,5 = Registered Roaming
    send_at("AT+CREG?")
    
    # 5. Check Carrier
    send_at("AT+COPS?")

    ser.close()

except KeyboardInterrupt:
    print("Test stopped.")
    ser.close()
