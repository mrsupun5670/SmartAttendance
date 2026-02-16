// -------------------------------------------------------------------------------------------------
// CONFIGURATION
// -------------------------------------------------------------------------------------------------
// TODO: PASTE YOUR SPREADSHEET ID HERE (From the URL of your Sheet)
var SHEET_ID = "18wXo-JHq9PVw2YbpClJlwT5XOtW2dju47mdV2VIrHuI";

function doGet(e) {
    return handleRequest(e);
}

function doPost(e) {
    return handleRequest(e);
}

function handleRequest(e) {
    var action = e.parameter.action;

    // OPEN SHEET BY ID (Fixes the "Null" error)
    var ss;
    try {
        ss = SpreadsheetApp.openById(SHEET_ID);
    } catch (err) {
        return response({ status: "error", message: "Invalid Sheet ID. Please update code." });
    }

    // --- DASHBOARD: GET LOGS ---
    if (action == "getAttendance") {
        var sheet = ss.getSheetByName("Attendance");
        var lastRow = sheet.getLastRow();
        var startRow = Math.max(2, lastRow - 50);
        if (lastRow < 2) return response([]);

        var data = sheet.getRange(startRow, 1, lastRow - startRow + 1, 5).getValues();
        data.reverse();
        return response(data);
    }

    // --- ESP32 / PI: SMART SCAN (Validate + Log + Return Phone) ---
    // Handles BOTH 'logAttendance' (direct) and 'handleScan' (smart)
    if (action == "logAttendance" || action == "handleScan") {
        var uid = e.parameter.uid;       // e.g. "19,127,222,53"
        var device = e.parameter.device; // e.g. "BUS-UNIT"
        var type = e.parameter.type;     // e.g. "BUS_ENTRY"

        // 1. Validate Student & Get Phone
        var student = findStudent(ss, uid);

        if (!student) {
            return response({
                status: "denied",
                message: "Unknown Card"
            });
        }

        // 2. Log Attendance
        var sheet = ss.getSheetByName("Attendance");
        var timestamp = new Date();
        sheet.appendRow([timestamp, uid, student.name, device, type]);

        // 3. Return Data to ESP32 (So it can send SMS)
        // Ensure Phone is a String and has '+' prefix for GSM
        var phoneStr = String(student.phone).trim();
        if (!phoneStr.startsWith("+")) {
            phoneStr = "+" + phoneStr;
        }

        return response({
            status: "allowed",
            message: "Logged Successfully",
            name: String(student.name),
            phone: phoneStr
        });
    }

    // --- ADD STUDENT (Dashboard) ---
    // Check if it's a JSON POST or URL Params
    if (action == "addStudent" || (e.postData && JSON.parse(e.postData.contents).action == "addStudent")) {
        var data = e.parameter;
        if (e.postData) data = JSON.parse(e.postData.contents);

        var sheet = ss.getSheetByName("Students");
        sheet.appendRow([data.uid, data.name, data.phone, data.class]);
        return response({ status: "success", message: "Student Added" });
    }
}

// Helper: Find student by UID in "Students" tab
function findStudent(ss, targetUID) {
    var sheet = ss.getSheetByName("Students");
    var data = sheet.getDataRange().getValues(); // Read all data

    // Clean target UID (remove spaces)
    var cleanTarget = String(targetUID).replace(/\s/g, '').trim();

    for (var i = 1; i < data.length; i++) {
        // Check Column A (Index 0) for UID
        var rowUID = String(data[i][0]).replace(/\s/g, '').trim();

        // Check exact match OR raw match
        if (rowUID == cleanTarget || rowUID.replace(/,/g, '') == cleanTarget.replace(/,/g, '')) {
            return {
                name: data[i][1],  // Col B
                phone: data[i][2], // Col C
                class: data[i][3]  // Col D
            };
        }
    }
    return null; // Not found
}

function response(data) {
    return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}
