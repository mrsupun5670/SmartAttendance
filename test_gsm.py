import serial
import time
import sys

# --------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------
PHONE_NUMBER = "+94772010915"
MESSAGE = "Hello! This is a test message from your Raspberry Pi Smart Attendance System."
SERIAL_PORT = '/dev/serial0'  # Default for Pi 3/4
# --------------------------------------------------------------------------

def send_command(ser, command, wait_time=1, expected_response=None):
    print(f"[PC -> GSM] {command}")
    ser.write((command + "\r\n").encode())
    time.sleep(wait_time)
    
    response = ""
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"[GSM -> PC] {response.strip()}")
    else:
        print("[GSM -> PC] ... (No Response)")
    
    if expected_response and expected_response not in response:
        return False, response
    return True, response

def send_sms(ser, number, text):
    print("\n--- INITIATING SMS SENDING ---")
    
    # 1. Set SMS to Text Mode
    success, _ = send_command(ser, "AT+CMGF=1", 1, "OK")
    if not success:
        print("Error: Could not set Text Mode (AT+CMGF=1).")
        return

    # 2. Trigger Send Command
    print(f"[PC -> GSM] AT+CMGS=\"{number}\"")
    ser.write(f'AT+CMGS="{number}"\r\n'.encode())
    time.sleep(1)
    
    # 3. Check for Prompt (>)
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"[GSM -> PC] {response.strip()}")
        if ">" not in response:
            print("Error: Did not receive '>' prompt.")
            return
    else:
         print("Error: No response from module (expected '>').")
         return

    # 4. Send Message Body + Ctrl+Z (ASCII 26)
    print(f"[PC -> GSM] {text} + <Ctrl+Z>")
    ser.write(text.encode())
    ser.write(bytes([26])) # ASCII 26 is Ctrl+Z (Substitute)
    
    # 5. Wait for network to send (can take 5-10 seconds)
    print("Sending... (waiting 10s)")
    time.sleep(10)
    
    if ser.in_waiting > 0:
        final_response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"[GSM -> PC] {final_response.strip()}")
        if "OK" in final_response:
             print("\n*** SMS SENT SUCCESSFULLY ***")
        else:
             print("\n*** SMS FAILURE ***")
    else:
        print("\n*** NO CONFIRMATION RECEIVED ***")


def main():
    # Try common baud rates since "No response" might mean wrong speed
    baud_rates = [9600, 115200]
    ser = None
    
    for baud in baud_rates:
        print(f"\nTesting connection at {baud} baud/s...")
        try:
            ser = serial.Serial(SERIAL_PORT, baudrate=baud, timeout=2)
            
            # Simple handshake
            # We send AT twice to let it auto-baud if needed
            ser.write(b"AT\r\n")
            time.sleep(1)
            ser.reset_input_buffer()
            
            success, response = send_command(ser, "AT", 1, "OK")
            
            if success:
                print(f"--> SUCCESS! Module found at {baud} baud.")
                break
            else:
                ser.close()
                ser = None
                
        except Exception as e:
            print(f"Error accessing port: {e}")
            return

    if ser is None:
        print("\n\nCRITICAL ERROR: GSM Module not responding at 9600 or 115200.")
        print("TROUBLESHOOTING:")
        print("1. CHECK WIRING: TX(Pi) -> RX(GSM) and RX(Pi) -> TX(GSM). Try swapping them!")
        print("2. CHECK POWER: Is the red LED blinking? Does it flash quickly (searching) or slowly (3s = connected)?")
        print("3. COMMON GROUND: Do you have a wire from GSM GND to Raspberry Pi GND?")
        return

    try:
        # Diagnostic Info
        send_command(ser, "AT+CSQ")    # Signal quality
        send_command(ser, "AT+CREG?")  # Network registration
        
        # Send the SMS
        send_sms(ser, PHONE_NUMBER, MESSAGE)
        
    except KeyboardInterrupt:
        print("\nTest stopped.")
    finally:
        ser.close()
        print("Serial closed.")

if __name__ == "__main__":
    main()
