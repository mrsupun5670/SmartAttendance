# Configuration file for SmartAttendance project
# This file will store settings like GPIO pin numbers, database path, etc.

# Database settings
DATABASE_NAME = "attendance.db"

# NFC Reader settings (example, actual pins will depend on wiring)
NFC_SPI_PORT = 0
NFC_SPI_DEVICE = 0

# GSM Module settings (example, actual serial port will depend on connection)
GSM_SERIAL_PORT = "/dev/ttyS0" # Common for Raspberry Pi, might be /dev/ttyAMA0 or /dev/ttyUSB0
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
