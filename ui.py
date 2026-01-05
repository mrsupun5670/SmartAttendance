import tkinter as tk

def display_hello_message():
    """
    Creates a simple Tkinter window to display "Hello, SmartAttendance!".
    This function is intended to be run on the Raspberry Pi with a connected display.
    """
    root = tk.Tk()
    root.title("SmartAttendance")
    
    # Attempt to set a common resolution for a 5-inch display, adjust as needed
    # A typical 5-inch HDMI display for Raspberry Pi might be 800x480
    root.geometry("800x480") 

    label = tk.Label(root, text="Hello, SmartAttendance!", font=("Arial", 48))
    label.pack(expand=True, fill='both')

    root.mainloop()

if __name__ == "__main__":
    # This block allows testing the UI module directly if needed,
    # but typically main.py will call display_hello_message().
    display_hello_message()
