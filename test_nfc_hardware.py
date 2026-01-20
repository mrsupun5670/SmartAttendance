#!/usr/bin/env python3
import RPi.GPIO as GPIO
# --------------------------------------------------------------------------
# WIRING DIAGRAM (RC522 -> Raspberry Pi)
# --------------------------------------------------------------------------
# SDA (SS)  -> Pin 24 (GPIO 8)
# SCK       -> Pin 23 (GPIO 11)
# MOSI      -> Pin 19 (GPIO 10)
# MISO      -> Pin 21 (GPIO 9)
# IRQ       -> (Not Connected)
# GND       -> Pin 6  (Ground)
# RST       -> Pin 22 (GPIO 25)
# 3.3V      -> Pin 1  (3.3V)  <-- IMPORTANT: DO NOT CONNECT TO 5V
# --------------------------------------------------------------------------

from mfrc522 import SimpleMFRC522
import time

# Create an object of the class SimpleMFRC522
reader = SimpleMFRC522()

print("-----------------------------------------")
print("NFC Hardware Test Script")
print("-----------------------------------------")
print("Please place your RFID card/tag near the reader...")
print("Press Ctrl+C to stop.")

try:
    while True:
        try:
            # reader.read() blocks until a card is read
            # It returns id (the card's unique ID) and text (data stored on card)
            id, text = reader.read()
            print("\n!!! SUCCESS - CARD DETECTED !!!")
            print(f"Card ID: {id}")
            print(f"Text on Card: {text}")
            print("-----------------------------------------")
            print("Ready for next scan...")
            
            # Small delay to prevent double reading the same tap instantly
            time.sleep(1)
            
        except Exception as e:
             print(f"Error reading card: {e}")
             time.sleep(1)

except KeyboardInterrupt:
    print("\nTest stopped by user.")
    GPIO.cleanup()
