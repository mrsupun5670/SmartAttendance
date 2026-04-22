# Smart Attendance System - Production Implementation Plan

## 1. Architecture Overview

This "Production Ready" system integrates multiple hardware nodes (Raspberry Pi, ESP32) with a centralized cloud database (Google Sheets) and a web-based Admin Panel hosted on GitHub Pages.

### Components:
1.  **Central Database (Google Sheets)**:
    *   Stores `Student Data` (Name, ID, Parent Phone).
    *   Stores `Attendance Logs` (Time, Device, Status).
2.  **The Brain (Middleware API - Google Apps Script)**:
    *   Since GitHub Pages is static, we use a Google Apps Script (deployed as a Web App) to act as a secure API gateway.
    *   It handles requests from the Web Admin and ESP32.
3.  **Web Admin Panel (GitHub Pages)**:
    *   A clean UI for you to add/remove students and view live attendance.
    *   Communicates with the Google Sheet via the Apps Script API.
4.  **Raspberry Pi Node (The "Master" Gateway)**:
    *   **Hardware**: 5" Touch Screen, RFID, GSM, Pi 4.
    *   **Function**:
        *   Scans ID -> Checks Local Cache (for speed) -> Sends SMS (via GSM) -> Uploads Log to Cloud.
        *   Syncs with Google Sheet every 10 minutes to get new students.
5.  **ESP32 Node (The "Satellite" Scanner)**:
    *   **Hardware**: ESP32, RFID.
    *   **Function**:
        *   Scans ID -> Uploads Log to Google Sheet (via WiFi/API).

---

## 2. Step-by-Step Setup Guide

### Phase 1: Google Cloud & Sheets Setup (CRITICAL)
*You must do this manually to get the credentials.*

1.  **Create a Google Sheet**:
    *   Name: `SmartAttendance_DB`
    *   Tab 1 Name: `Students` (Headers: `UID`, `Name`, `ParentPhone`, `Class`)
    *   Tab 2 Name: `Attendance` (Headers: `Timestamp`, `UID`, `Name`, `Device`, `Type`)
2.  **Enable Google Sheets API (for Raspberry Pi)**:
    *   Go to **Google Cloud Console**.
    *   Create a Project -> Enable "Google Sheets API" and "Google Drive API".
    *   **Create Credentials**: Select "Service Account".
    *   Download the keys as a JSON file. Rename it to `service_account.json`.
    *   **Share your Google Sheet** with the `client_email` found inside that JSON file (give "Editor" access).

### Phase 2: Google Apps Script API (For Web & ESP32)
*This creates the link between your Website/ESP32 and the Sheet.*

1.  Open your Google Sheet.
2.  Go to `Extensions` -> `Apps Script`.
3.  Paste the "Backend Script" (I will provide this).
4.  **Deploy**: Click `Deploy` -> `New Deployment` -> `Web App`.
    *   Execute as: `Me`.
    *   Who has access: `Anyone` (Important for ESP32/GitHub Pages to work without login prompts).
5.  Copy the **Web App URL**. You will need this for the Website and ESP32 code.

### Phase 3: Raspberry Pi Setup (The Physical "Gate")

#### 1. Hardware PIN Configuration (CRITICAL)
Since the 5" Display uses SPI0 (CE0), we MUST move the RFID reader to **CE1**.

| Component | Pin Name | Pi GPIO | Description |
| :--- | :--- | :--- | :--- |
| **RFID** | SDA (SS) | **GPIO 7** | **Use CE1 (Pin 26)** |
| RFID | SCK | GPIO 11 | Shared with Screen (Pin 23) |
| RFID | MOSI | GPIO 10 | Shared with Screen (Pin 19) |
| RFID | MISO | GPIO 9 | Shared with Screen (Pin 21) |
| **RFID** | RST | **GPIO 24** | **Custom Reset (Pin 18)** |
| RFID | 3.3V | 3.3V | **Pin 1 or 17** (Do NOT use 5V) |
| | | | |
| **GSM** | TX | GPIO 15 | Connect to Pi RX (Pin 10) |
| GSM | RX | GPIO 14 | Connect to Pi TX (Pin 8) |
| GSM | GND | GND | Common Ground (Pin 6) |

#### 2. OS Configuration
Run `sudo raspi-config`:
*   **Interface Options -> SPI**: **YES** (Enables RFID)
*   **Interface Options -> Serial Port**:
    *   Login Shell? **NO**
    *   Hardware Enabled? **YES**

#### 3. Software Installation
Run these commands on the Pi:
```bash
# 1. Update System
sudo apt update

# 2. Install Libraries (Use --break-system-packages if on Bookworm)
pip3 install gspread oauth2client requests pyserial spidev mfrc522 --break-system-packages

# 3. Create Project Folder
mkdir -p ~/SmartAttendance
cd ~/SmartAttendance
# (Copy main_system.py and service_account.json here)
```

#### 4. The Logic (How it works)
The script `main_system.py` implements intelligent logic:
*   **Offline First**: It downloads the student list to `students.json` so it works even if WiFi drops.
*   **Entry/Exit Toggle**:
    *   **Tap 1**: Marks student "INSIDE" -> Logs **SCHOOL_ENTRY** -> SMS "Arrived".
    *   **Tap 2**: Marks student "OUTSIDE" -> Logs **SCHOOL_EXIT** -> SMS "Left".
*   **Safety Cool-down**: Ignores scans from the same card for **60 seconds** to prevent accidental double-taps.
*   **Formatting Fix**: Automatically handles UID formats with or without commas (e.g., `19,127...` vs `19127...`).

#### 5. Auto-Start (Make it a Appliance)
To run automatically when the Pi turns on:
1.  Type `crontab -e`
2.  Add this line to the bottom:
    ```bash
    @reboot /usr/bin/python3 /home/school/SmartAttendance/main_system.py >> /home/school/attendance.log 2>&1
    ```

---

## 4. Next Steps for Me (The Agent)
1.  I will write the **Google Apps Script** code for you to paste.
2.  I will create the **Python "Production" Codebase** for the Pi (integrating your working GSM/RFID drivers).
3.  I will generate the **Web Admin Panel** code.
