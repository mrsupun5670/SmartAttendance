/*
 * SmartAttendanceESP32 (Bus Unit)
 * Purpose: Independent Bus Attendance System with WiFi Logging + GSM SMS
 */

#include <HTTPClient.h>
#include <HardwareSerial.h>
#include <MFRC522.h>
#include <Preferences.h>
#include <SPI.h>
#include <WiFi.h>

// ----------------------------------------------------------------------
// CONFIGURATION
// ----------------------------------------------------------------------
const char *ssid = "Suneth";
const char *password = "Suneth@512";

// GOOGLE SCRIPT URL
// GOOGLE SCRIPT URL
String GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/"
                           "AKfycby8QjOohMtw2NpOMpLytM2_LI-"
                           "lwb39g3Cc2Kaj7FTaRMUb6O744m2mm1uv3724IqY/exec";

// PARENT PHONE (Default - In a real system you'd fetch this from the cloud)
String DEFAULT_PHONE = "+94772010915";

// PINS - RFID (Standard VSPI)
#define SS_PIN 5
#define RST_PIN 22

// PINS - GSM (Serial2)
#define RX_PIN 16
#define TX_PIN 17

// ----------------------------------------------------------------------
// GLOBAL OBJECTS
// ----------------------------------------------------------------------
MFRC522 rfid(SS_PIN, RST_PIN);
HardwareSerial gsmSerial(2); // UART2
Preferences preferences;     // To save entry/exit state permanently

void setup() {
  Serial.begin(115200);

  // 1. Init status storage
  preferences.begin("attendance", false);

  // 2. Init RFID
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("RFID Ready");

  // 3. Init GSM
  gsmSerial.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  delay(1000);
  gsmSerial.println("AT");
  Serial.println("GSM Init Sent");

  // 4. Init WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  int timeout = 0;
  // Increase timeout to 60 half-seconds (30 seconds)
  while (WiFi.status() != WL_CONNECTED && timeout < 60) {
    delay(500);
    Serial.print(".");
    timeout++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n--- WiFi Connected! ---");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[ERROR] WiFi Failed to Connect.");
    Serial.println("Check: 1. Password correct? 2. Is it 2.4GHz? (ESP32 "
                   "doesn't support 5GHz)");
  }
}

void loop() {
  // Check for RFID
  if (!rfid.PICC_IsNewCardPresent())
    return;
  if (!rfid.PICC_ReadCardSerial())
    return;

  // 1. Get UID (Comma Separated Decimal to match Pi/Sheet)
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (i > 0)
      uid += ",";
    uid += String(rfid.uid.uidByte[i]);
  }

  Serial.println("\nCard Detected: " + uid);

  // 2. Handle Logic (Entry/Exit)
  handleStudentScan(uid);

  // Halt PICC
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  delay(2000); // 2 second delay to prevent immediate double-read
}

void handleStudentScan(String uid) {
  // Check last status
  // 0 = Outside (Default), 1 = Inside
  int currentStatus = preferences.getInt(uid.c_str(), 0);

  String action = (currentStatus == 0) ? "BUS_ENTRY" : "BUS_EXIT";
  String smsMsg = (currentStatus == 0) ? "Student has BOARDED the Bus."
                                       : "Student has GOT OFF the Bus.";

  // Toggle Status
  preferences.putInt(uid.c_str(), (currentStatus == 0) ? 1 : 0);

  Serial.println("Action: " + action);

  // 3. Send SMS (Directly from Bus Unit)
  sendSMS(DEFAULT_PHONE, smsMsg);

  // 4. Send Data to Cloud (WiFi)
  if (WiFi.status() == WL_CONNECTED) {
    sendDataToScript(uid, action);
  } else {
    Serial.println("WiFi Offline - Log NOT synced to Sheet.");
  }
}

void sendDataToScript(String uid, String type) {
  HTTPClient http;

  // Construct GET URL with Query Params
  // Ex: SCRIPT_URL?action=logAttendance&uid=...&name=BusPassenger&device=...
  String url = GOOGLE_SCRIPT_URL + "?action=logAttendance" + "&uid=" + uid +
               "&name=BusPassenger" + "&device=BUS-UNIT-01" + "&type=" + type;

  Serial.println("Sending Request: " + url);

  http.begin(url);
  http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);

  int httpResponseCode = http.GET();

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("Cloud Response: " + response);
  } else {
    Serial.print("Error on sending GET: ");
    Serial.println(httpResponseCode);
  }
  http.end();
}

void sendSMS(String number, String message) {
  gsmSerial.println("AT+CMGF=1");
  delay(200);
  gsmSerial.print("AT+CMGS=\"");
  gsmSerial.print(number);
  gsmSerial.println("\"");
  delay(200);
  gsmSerial.print(message);
  delay(100);
  gsmSerial.write(26); // Ctrl+Z
  delay(5000);         // Wait for network
  Serial.println("SMS Sent!");
}
