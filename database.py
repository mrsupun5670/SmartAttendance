# database.py
# This file will handle all SQLite database interactions.

import sqlite3
from datetime import datetime
import os

# Placeholder for database functions
class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id TEXT NOT NULL,
                    location TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error during table creation: {e}")
        finally:
            if conn:
                conn.close()

    def log_attendance(self, card_id, location, action):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO attendance_logs (card_id, location, action, timestamp) VALUES (?, ?, ?, ?)",
                (card_id, location, action, timestamp)
            )
            conn.commit()
            print(f"Logged: Card ID: {card_id}, Location: {location}, Action: {action}, Timestamp: {timestamp}")
            return True
        except sqlite3.Error as e:
            print(f"Database error during logging: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_all_logs(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM attendance_logs ORDER BY timestamp DESC")
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error during fetching logs: {e}")
            return []
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    # Example usage for testing the database module
    db_file = "test_attendance.db"
    if os.path.exists(db_file):
        os.remove(db_file) # Clean up previous test db

    db_manager = DatabaseManager(db_file)
    print("Database created and table checked.")

    # Log some dummy data
    db_manager.log_attendance("NFC123", "School Gate", "SCHOOL_ENTRY")
    db_manager.log_attendance("NFC456", "Bus Stop A", "BUS_BOARDING")

    # Retrieve and print logs
    logs = db_manager.get_all_logs()
    print("\nAll attendance logs:")
    for log in logs:
        print(log)

    os.remove(db_file) # Clean up test db
    print("\nTest database removed.")
