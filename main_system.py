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
CREDENTIALS_FILE = "service_account.json"
STUDENTS_FILE = "students.json"
SHEET_NAME = "SmartAttendance_DB"
GSM_PORT = "/dev/serial0"
GSM_BAUD = 9600
NFC_SPI_DEVICE = 1  # CE1 (GPIO 7)
NFC_RST_PIN = 24    # Reset Pin (GPIO 24)

# Feedback Pins
PIN_LED_GREEN = 20
PIN_LED_RED = 21
PIN_BUZZER = 16

class SmartAttendance:
    def __init__(self):
        self.running = False
        self.students_cache = {}
        self.student_status = {}
        self.last_scan_times = {}
        self.gsm_serial = None
        self.reader = None
        self.log_callback = None # Function to call for GUI logs

        # Hardware Init
        self.init_gpio()
        self.init_gsm()
        self.init_nfc()
        
        # Load Data
        self.sync_students_from_sheet()

        # Start Sync Thread
        self.sync_thread = threading.Thread(target=self.auto_sync, daemon=True)
        self.sync_thread.start()

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        if self.log_callback:
            self.log_callback(formatted)

    # --------------------------------------------------------------------------
    # HARDWARE
    # --------------------------------------------------------------------------
    def init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PIN_LED_GREEN, GPIO.OUT)
        GPIO.setup(PIN_LED_RED, GPIO.OUT)
        GPIO.setup(PIN_BUZZER, GPIO.OUT)
        GPIO.output(PIN_LED_GREEN, GPIO.LOW)
        GPIO.output(PIN_LED_RED, GPIO.LOW)
        GPIO.output(PIN_BUZZER, GPIO.LOW)

    def init_gsm(self):
        try:
            self.gsm_serial = serial.Serial(GSM_PORT, baudrate=GSM_BAUD, timeout=1)
            self.gsm_serial.write(b"AT\r\n")
            time.sleep(0.5)
            self.log("[GSM] Initialized successfully.")
        except Exception as e:
            self.log(f"[GSM] Error initializing: {e}")

    def init_nfc(self):
        try:
            self.reader = MFRC522(device=NFC_SPI_DEVICE, pin_rst=NFC_RST_PIN)
            self.log(f"[NFC] Initialized on CE{NFC_SPI_DEVICE}")
        except Exception as e:
            self.log(f"[NFC] Error initializing: {e}")

    def trigger_success(self):
        def _run():
            GPIO.output(PIN_LED_GREEN, GPIO.HIGH)
            for _ in range(2):
                GPIO.output(PIN_BUZZER, GPIO.HIGH); time.sleep(0.1)
                GPIO.output(PIN_BUZZER, GPIO.LOW);  time.sleep(0.1)
            time.sleep(1.0)
            GPIO.output(PIN_LED_GREEN, GPIO.LOW)
        threading.Thread(target=_run).start()

    def trigger_fail(self):
        def _run():
            GPIO.output(PIN_LED_RED, GPIO.HIGH)
            GPIO.output(PIN_BUZZER, GPIO.HIGH); time.sleep(1.0)
            GPIO.output(PIN_BUZZER, GPIO.LOW)
            GPIO.output(PIN_LED_RED, GPIO.LOW)
        threading.Thread(target=_run).start()

    # --------------------------------------------------------------------------
    # CLOUD / DATA
    # --------------------------------------------------------------------------
    def get_google_client(self):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        return gspread.authorize(creds)

    def sync_students_from_sheet(self):
        self.log("[CLOUD] Syncing student list...")
        try:
            client = self.get_google_client()
            sheet = client.open(SHEET_NAME).worksheet("Students")
            records = sheet.get_all_records()
            
            new_cache = {}
            for row in records:
                uid = str(row['UID']).strip()
                new_cache[uid] = {
                    "Name": row['Name'],
                    "ParentPhone": str(row['ParentPhone']).strip(),
                    "Class": row.get('Class', '')
                }
            self.students_cache = new_cache
            
            with open(STUDENTS_FILE, 'w') as f:
                json.dump(self.students_cache, f)
            self.log(f"[CLOUD] Sync Complete. Loaded {len(self.students_cache)} students.")
        except Exception as e:
            self.log(f"[CLOUD] Sync Failed: {e}")
            if os.path.exists(STUDENTS_FILE):
                self.log("[CLOUD] Loading from local backup...")
                with open(STUDENTS_FILE, 'r') as f:
                    self.students_cache = json.load(f)

    def auto_sync(self):
        while True:
            time.sleep(600)
            if self.running: # Only sync if system is active? Or always?
                self.sync_students_from_sheet()

    def add_student(self, uid, name, phone, student_class):
        try:
            client = self.get_google_client()
            sheet = client.open(SHEET_NAME).worksheet("Students")
            # UID, Name, Class, ParentPhone
            sheet.append_row([uid, name, student_class, phone])
            self.log(f"[CLOUD] Added Student: {name}")
            # Refresh Cache
            self.sync_students_from_sheet()
            return True
        except Exception as e:
            self.log(f"[ERROR] Add Student Failed: {e}")
            return False

    def delete_student(self, uid):
        try:
            client = self.get_google_client()
            sheet = client.open(SHEET_NAME).worksheet("Students")
            cell = sheet.find(uid)
            sheet.delete_rows(cell.row)
            self.log(f"[CLOUD] Deleted Student UID: {uid}")
            self.sync_students_from_sheet()
            return True
        except Exception as e:
            self.log(f"[ERROR] Delete Student Failed: {e}")
            return False

    def upload_attendance_log(self, uid, name, log_type):
        try:
            client = self.get_google_client()
            sheet = client.open(SHEET_NAME).worksheet("Attendance")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, uid, name, "SCHOOL_GATE", log_type])
            self.log(f"[CLOUD] Logged: {name}")
        except Exception as e:
            self.log(f"[CLOUD] Log Upload Failed: {e}")

    # --------------------------------------------------------------------------
    # SMS
    # --------------------------------------------------------------------------
    def send_sms(self, phone, message):
        if not self.gsm_serial or not self.gsm_serial.is_open:
            self.log(f"[GSM] Port not open. Skipping SMS to {phone}")
            return

        self.log(f"[GSM] Sending SMS to {phone}")
        try:
            self.gsm_serial.write(b"AT+CMGF=1\r\n")
            time.sleep(0.2)
            cmd = f'AT+CMGS="{phone}"\r\n'
            self.gsm_serial.write(cmd.encode())
            time.sleep(0.2)
            self.gsm_serial.write(message.encode())
            self.gsm_serial.write(bytes([26])) # Ctrl+Z
            self.log("[GSM] Command sent.")
        except Exception as e:
            self.log(f"[GSM] Error sending SMS: {e}")

    # --------------------------------------------------------------------------
    # SCANNING LOGIC
    # --------------------------------------------------------------------------
    def scan_once(self):
        """Attempts to read a card ONCE. Returns UID or None."""
        if not self.reader: return None
        (status, TagType) = self.reader.MFRC522_Request(self.reader.PICC_REQIDL)
        if status == self.reader.MI_OK:
            (status, uid) = self.reader.MFRC522_Anticoll()
            if status == self.reader.MI_OK:
                # Construct UID format "19,127,222,53"
                return f"{uid[0]},{uid[1]},{uid[2]},{uid[3]}"
        return None

    def start_scanning(self):
        self.running = True
        self.log("--- SYSTEM STARTED ---")
        threading.Thread(target=self._scan_loop, daemon=True).start()

    def stop_scanning(self):
        self.running = False
        self.log("--- SYSTEM STOPPED ---")

    def _scan_loop(self):
        while self.running:
            uid_str = self.scan_once()
            
            if uid_str:
                self.log(f"[SCAN] Card Detected: {uid_str}")
                
                # Cool-down Check
                current_time = time.time()
                last_scan = self.last_scan_times.get(uid_str, 0)
                if current_time - last_scan < 60:
                    self.log("[IGNORED] Too fast.")
                    self.trigger_fail()
                    time.sleep(2)
                    continue

                # Lookup
                student = self.students_cache.get(uid_str)
                if not student:
                    # Try raw format backup logic if needed (omitted for brevity, can add back)
                    pass

                if student:
                    name = student['Name']
                    phone = student['ParentPhone']
                    
                    # Entry/Exit Logic
                    current_status = self.student_status.get(uid_str, "OUTSIDE")
                    if current_status == "OUTSIDE":
                        new_status = "INSIDE"
                        log_type = "SCHOOL_ENTRY"
                        sms_msg = f"Alert: {name} has ARRIVED at School at {datetime.datetime.now().strftime('%H:%M')}."
                        self.log(f"[LOGIC] {name} is ENTERING.")
                    else:
                        new_status = "OUTSIDE"
                        log_type = "SCHOOL_EXIT"
                        sms_msg = f"Alert: {name} has LEFT School at {datetime.datetime.now().strftime('%H:%M')}."
                        self.log(f"[LOGIC] {name} is LEAVING.")
                    
                    self.student_status[uid_str] = new_status
                    self.last_scan_times[uid_str] = current_time
                    
                    threading.Thread(target=self.send_sms, args=(phone, sms_msg)).start()
                    threading.Thread(target=self.upload_attendance_log, args=(uid_str, name, log_type)).start()
                    
                    self.trigger_success()
                else:
                    self.log(f"[ACCESS DENIED] Unknown Card: {uid_str}")
                    self.trigger_fail()
                
                time.sleep(2) # Prevent immediate re-read
            
            time.sleep(0.1)

    def close(self):
        self.running = False
        GPIO.cleanup()
        if self.gsm_serial:
            self.gsm_serial.close()

# --------------------------------------------------------------------------
# CLI ENTRY POINT (Backwards Compatibility)
# --------------------------------------------------------------------------
def main():
    app = SmartAttendance()
    app.start_scanning()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.close()

if __name__ == "__main__":
    main()
