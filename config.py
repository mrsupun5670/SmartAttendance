# Configuration file for SmartAttendance project
# This file will store settings like GPIO pin numbers, database path, etc.

# Database settings
DATABASE_NAME = "attendance.db"

# NFC Reader settings
# Note: SPI Device 0 (CE0) is used by the XPT2046 Display.
# We must use Device 1 (CE1) for the RFID reader.
NFC_SPI_PORT = 0
NFC_SPI_DEVICE = 1      # CE1 (GPIO 7)
NFC_RST_PIN = 24        # Reset pin for RFID (GPIO 24)

# GSM Module settings
# Raspberry Pi 3/4 typically uses /dev/serial0 which maps to the correct UART
GSM_SERIAL_PORT = "/dev/serial0" 
GSM_BAUDRATE = 9600

# Parent phone numbers (example)
PARENT_PHONE_NUMBERS = {
    "NFC_CARD_ID_1": "+1234567890",
    "NFC_CARD_ID_2": "+1987654321",
}

# Mode and Action definitions (will be expanded later)
MODE_BUS = "BUS_MODE"
MODE_SCHOOL = "SCHOOL_MODE"

ACTION_BUS_BOARDING = "BUS_BOARDING"
ACTION_BUS_ALIGHTING = "BUS_ALIGHTING"
ACTION_SCHOOL_ENTRY = "SCHOOL_ENTRY"
ACTION_SCHOOL_EXIT = "SCHOOL_EXIT"
