#!/usr/bin/env python3
import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time

# --------------------------------------------------------------------------
# WIRING DIAGRAM (RC522 -> Raspberry Pi with 5" HDMI Display)
# --------------------------------------------------------------------------
# The Display uses CE0 (GPIO 8), so we MUST use CE1 (GPIO 7) for RFID.
#
# SDA (SS)  -> Pin 26 (GPIO 7)   <-- UPDATED: Use CE1
# SCK       -> Pin 23 (GPIO 11)  <-- Shared with Display
# MOSI      -> Pin 19 (GPIO 10)  <-- Shared with Display
# MISO      -> Pin 21 (GPIO 9)   <-- Shared with Display
# IRQ       -> (Not Connected)
# GND       -> Pin 6, 9, 20...   <-- Common Ground
# RST       -> Pin 18 (GPIO 24)  <-- UPDATED: Any free GPIO
# 3.3V      -> Pin 1 or 17       <-- IMPORTANT: DO NOT CONNECT TO 5V
# --------------------------------------------------------------------------

print("-----------------------------------------")
print("NFC Hardware Test Script (Custom Pins)")
print("-----------------------------------------")
print("Using SPI Device 1 (CE1) and RST=GPIO24")
print("Please place your RFID card/tag near the reader...")
print("Press Ctrl+C to stop.")

# Create an object of the class MFRC522
# device=1 means we use CE1 (GPIO 7)
# pin_rst=24 means we use GPIO 24 for Reset
try:
    reader = MFRC522(device=1, pin_rst=24)
except Exception as e:
    print(f"Error initializing MFRC522: {e}")
    print("Ensure SPI is enabled 'sudo raspi-config' -> Interface Options -> SPI")
    exit(1)

try:
    while True:
        # Scan for cards    
        (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)

        # If a card is found
        if status == reader.MI_OK:
            print("Card detected!")
            
            # Get the UID of the card
            (status, uid) = reader.MFRC522_Anticoll()

            # If we have the UID, continue
            if status == reader.MI_OK:
                # UID is a list of 4 bytes [x, x, x, x]
                # Keep first 4 bytes for standard UID check
                card_id_str = f"{uid[0]},{uid[1]},{uid[2]},{uid[3]}"
                
                print(f"!!! SUCCESS !!!")
                print(f"Card UID (List): {uid}")
                print(f"Card UID (String): {card_id_str}")
                
                # Select the scanned tag
                reader.MFRC522_SelectTag(uid)
                
                # Check authentication (optional, demonstrating functionality)
                # default_key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
                # status = reader.MFRC522_Auth(reader.PICC_AUTHENT1A, 8, default_key, uid)
                # if status == reader.MI_OK:
                #     data = reader.MFRC522_Read(8)
                #     reader.MFRC522_StopCrypto1()
                #     print(f"Block 8 Data: {data}")
                
                print("-----------------------------------------")
                print("Ready for next scan (wait 1s)...")
                time.sleep(1)
        
        # Small delay to reduce CPU usage
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nTest stopped by user.")
    GPIO.cleanup()
