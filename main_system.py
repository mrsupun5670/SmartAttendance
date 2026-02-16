import gspread
from oauth2client.service_account import ServiceAccountCredentials
import serial
import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time
import requests
import json
import threading
import datetime
import os

# --------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------
# File Paths
CREDENTIALS_FILE = "service_account.json"
STUDENTS_FILE = "students.json"
SHEET_NAME = "SmartAttendance_DB"

# Hardware Settings
GSM_PORT = "/dev/serial0"
GSM_BAUD = 9600
NFC_SPI_DEVICE = 1  # CE1 (GPIO 7)
NFC_RST_PIN = 24    # Reset Pin (GPIO 24)

# --------------------------------------------------------------------------
# GLOBAL STATE
# --------------------------------------------------------------------------
STUDENTS_CACHE = {}  # { "UID_STRING": { "Name": "...", "ParentPhone": "..." } }
STUDENT_STATUS = {}  # { "UID_STRING": "INSIDE" } - Tracks who is currently in school
LAST_SCAN_TIMES = {} # { "UID_STRING": timestamp } - For cool-down
LAST_SYNC_TIME = 0
GSM_SERIAL = None

# Feedback Pins
PIN_LED_GREEN = 20  # Pin 38
PIN_LED_RED = 21    # Pin 40
PIN_BUZZER = 16     # Pin 36

# --------------------------------------------------------------------------
# HARDWARE INITIALIZATION
# --------------------------------------------------------------------------
def init_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIN_LED_GREEN, GPIO.OUT)
    GPIO.setup(PIN_LED_RED, GPIO.OUT)
    GPIO.setup(PIN_BUZZER, GPIO.OUT)
    
    # Start OFF
    GPIO.output(PIN_LED_GREEN, GPIO.LOW)
    GPIO.output(PIN_LED_RED, GPIO.LOW)
    GPIO.output(PIN_BUZZER, GPIO.LOW)

def trigger_success():
    def _run():
        GPIO.output(PIN_LED_GREEN, GPIO.HIGH)
        # Beep Beep
        GPIO.output(PIN_BUZZER, GPIO.HIGH); time.sleep(0.1)
        GPIO.output(PIN_BUZZER, GPIO.LOW);  time.sleep(0.1)
        GPIO.output(PIN_BUZZER, GPIO.HIGH); time.sleep(0.1)
        GPIO.output(PIN_BUZZER, GPIO.LOW)
        
        time.sleep(1.0)
        GPIO.output(PIN_LED_GREEN, GPIO.LOW)
    
    threading.Thread(target=_run).start()

def trigger_fail():
    def _run():
        GPIO.output(PIN_LED_RED, GPIO.HIGH)
        # Long Beep
        GPIO.output(PIN_BUZZER, GPIO.HIGH); time.sleep(1.0)
        GPIO.output(PIN_BUZZER, GPIO.LOW)
        
        GPIO.output(PIN_LED_RED, GPIO.LOW)

    threading.Thread(target=_run).start()

def init_gsm():
    global GSM_SERIAL
    try:
        GSM_SERIAL = serial.Serial(GSM_PORT, baudrate=GSM_BAUD, timeout=1)
        # Auto-baud handshake
        GSM_SERIAL.write(b"AT\r\n")
        time.sleep(0.5)
        print("[GSM] Initialized successfully.")
    except Exception as e:
        print(f"[GSM] Error initializing: {e}")

def init_nfc():
    try:
        reader = MFRC522(device=NFC_SPI_DEVICE, pin_rst=NFC_RST_PIN)
        print(f"[NFC] Initialized on CE{NFC_SPI_DEVICE} with RST={NFC_RST_PIN}")
        return reader
    except Exception as e:
        print(f"[NFC] Error initializing: {e}")
        return None

# --------------------------------------------------------------------------
# CLOUD SYNC FUNCTIONS
# --------------------------------------------------------------------------
def sync_students_from_sheet():
    global STUDENTS_CACHE
    print("[CLOUD] Syncing student list...")
    try:
        # Auth with Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        
        # Open Sheet
        sheet = client.open(SHEET_NAME).worksheet("Students")
        records = sheet.get_all_records() # Returns list of dicts
        
        # Update Cache
        new_cache = {}
        for row in records:
            # Assume headers: UID, Name, ParentPhone, Class
            uid = str(row['UID']).strip()
            new_cache[uid] = {
                "Name": row['Name'],
                "ParentPhone": str(row['ParentPhone']).strip(),
                "Class": row.get('Class', '')
            }
            
        STUDENTS_CACHE = new_cache
        
        # Save to local file
        with open(STUDENTS_FILE, 'w') as f:
            json.dump(STUDENTS_CACHE, f)
            
        print(f"[CLOUD] Sync Complete. loaded {len(STUDENTS_CACHE)} students.")
        
    except Exception as e:
        print(f"[CLOUD] Sync Failed: {e}")
        # Try loading from local backup
        if os.path.exists(STUDENTS_FILE):
            print("[CLOUD] Loading from local backup...")
            with open(STUDENTS_FILE, 'r') as f:
                STUDENTS_CACHE = json.load(f)

def upload_attendance_log(uid, name, log_type="ENTRY"):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open(SHEET_NAME).worksheet("Attendance")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Columns: Timestamp, UID, Name, Device, Type
        row = [timestamp, uid, name, "SCHOOL_GATE", log_type]
        sheet.append_row(row)
        print(f"[CLOUD] Attendance Logged: {name}")
        
    except Exception as e:
        print(f"[CLOUD] Log Upload Failed: {e}")
        # In a real app, you would save this to 'offline_logs.json' to retry later

# --------------------------------------------------------------------------
# SMS FUNCTION
# --------------------------------------------------------------------------
def send_sms(phone, message):
    if not GSM_SERIAL or not GSM_SERIAL.is_open:
        print(f"[GSM] Port not open. Skipping SMS to {phone}")
        return

    print(f"[GSM] Sending SMS to {phone}: '{message}'")
    try:
        # Set text mode
        GSM_SERIAL.write(b"AT+CMGF=1\r\n")
        time.sleep(0.2)
        
        # Number command
        cmd = f'AT+CMGS="{phone}"\r\n'
        GSM_SERIAL.write(cmd.encode())
        time.sleep(0.2)
        
        # Message body + Ctrl-Z
        GSM_SERIAL.write(message.encode())
        GSM_SERIAL.write(bytes([26])) # Ctrl+Z
        
        # Don't block too long, let it send in background
        print("[GSM] Command sent.")
        
    except Exception as e:
        print(f"[GSM] Error sending SMS: {e}")

# --------------------------------------------------------------------------
# MAIN LOGIC
# --------------------------------------------------------------------------
def main():
    print("--- SMART ATTENDANCE SYSTEM STARTING ---")
    
    # 1. Hardware Init
    init_gpio()
    init_gsm()
    reader = init_nfc()
    if not reader:
        print("CRITICAL: NFC Reader failed. Exiting.")
        return

    # 2. Initial Data Sync
    sync_students_from_sheet()
    
    # 3. Background Sync Thread (Every 10 mins)
    def auto_sync():
        while True:
            time.sleep(600) # 600s = 10 mins
            sync_students_from_sheet()
            
    sync_thread = threading.Thread(target=auto_sync, daemon=True)
    sync_thread.start()
    
    print("--- SYSTEM READY TO SCAN ---")
    
    # 4. Main Event Loop
    try:
        while True:
            # Scan for cards    
            (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)

            if status == reader.MI_OK:
                (status, uid) = reader.MFRC522_Anticoll()
                if status == reader.MI_OK:
                    
                    # Construct UID String (matches sheet format)
                    # UID comes as list of ints: [19, 127, 222, 53]
                    
                    # Format 1: Standard Comma-Separated (Preferred) -> "19,127,222,53"
                    uid_str_commas = f"{uid[0]},{uid[1]},{uid[2]},{uid[3]}"
                    
                    # Format 2: Raw Numbers (Backup) -> "1912722253"
                    uid_str_raw = f"{uid[0]}{uid[1]}{uid[2]}{uid[3]}"
                    
                    print(f"\n[SCAN] Card Detected: '{uid_str_commas}' (Raw: '{uid_str_raw}')")
                    
                    # --- SAFETY CHECK: COOL-DOWN TIMER ---
                    # Prevent accidental double-taps (Entry -> Exit -> Entry) within 60 seconds
                    current_time = time.time()
                    last_scan = LAST_SCAN_TIMES.get(uid_str_commas, 0)
                    
                    if current_time - last_scan < 60:
                        remaining = int(60 - (current_time - last_scan))
                        print(f"[IGNORED] Too fast! Please wait {remaining}s before scanning again.")
                        trigger_fail() # Feedback for "too fast" (optional, makes it red)
                        time.sleep(2)
                        continue # Skip the rest of the loop
                    
                    # 1. Look up student (Try both formats)
                    student = STUDENTS_CACHE.get(uid_str_commas)
                    
                    if not student:
                         # Try looking up by the raw number format (if specific Sheet cells were auto-formatted to numbers)
                         student = STUDENTS_CACHE.get(uid_str_raw)

                    # If still not found, try stripping spaces just in case
                    if not student:
                         uid_cleaned = uid_str_commas.replace(" ", "")
                         student = STUDENTS_CACHE.get(uid_cleaned)

                    if student:
                        name = student['Name']
                        phone = student['ParentPhone']
                        
                        # LOGIC: Check Status (Entry vs Exit)
                        current_status = STUDENT_STATUS.get(uid_str_commas, "OUTSIDE")
                        
                        if current_status == "OUTSIDE":
                            # ACTION: ENTER
                            new_status = "INSIDE"
                            log_type = "SCHOOL_ENTRY"
                            sms_msg = f"Alert: {name} has ARRIVED at School at {datetime.datetime.now().strftime('%H:%M')}."
                            print(f"[LOGIC] {name} is ENTERING.")
                        else:
                            # ACTION: EXIT
                            new_status = "OUTSIDE"
                            log_type = "SCHOOL_EXIT"
                            sms_msg = f"Alert: {name} has LEFT School at {datetime.datetime.now().strftime('%H:%M')}."
                            print(f"[LOGIC] {name} is LEAVING.")
                        
                        # Update status AND time in memory
                        STUDENT_STATUS[uid_str_commas] = new_status
                        LAST_SCAN_TIMES[uid_str_commas] = current_time
                        
                        # Use the standardized ID for logging
                        log_uid = uid_str_commas
                        
                        # 2. Send SMS
                        threading.Thread(target=send_sms, args=(phone, sms_msg)).start()
                        
                        # 3. Log to Cloud
                        threading.Thread(target=upload_attendance_log, args=(log_uid, name, log_type)).start()
                        
                        # 4. Visual Feedback
                        print(">>> ACCESS GRANTED <<<")
                        trigger_success()
                        
                    else:
                        print(f"[LOGIC] Unknown Card. Scanned: '{uid_str_commas}'")
                        print(f"[DEBUG] Known IDs in Database: {list(STUDENTS_CACHE.keys())}")
                        print(">>> ACCESS DENIED <<<")
                        trigger_fail()
                    
                    # Wait a bit to prevent double-scanning
                    time.sleep(2)
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nSystem stopping...")
        GPIO.cleanup()
        if GSM_SERIAL:
            GSM_SERIAL.close()

if __name__ == "__main__":
    main()
