import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from main_system import SmartAttendance
import threading
import time

class AttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Attendance System - Admin Panel")
        self.root.geometry("600x450")
        
        # Initialize Backend
        self.system = SmartAttendance()
        self.system.log_callback = self.log_to_gui # Hook logs
        
        # UI Setup
        self.setup_ui()
        
    def setup_ui(self):
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Tab 1: Dashboard
        self.frame_dashboard = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_dashboard, text='Dashboard')
        self.setup_dashboard(self.frame_dashboard)
        
        # Tab 2: Manage Students
        self.frame_manage = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_manage, text='Manage Students')
        self.setup_manage(self.frame_manage)
        
    # ----------------------------------------------------------------------
    # DASHBOARD
    # ----------------------------------------------------------------------
    def setup_dashboard(self, parent):
        # Controls
        control_frame = ttk.LabelFrame(parent, text="System Controls", padding=10)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        self.btn_start = ttk.Button(control_frame, text="Start Attendance", command=self.start_attendance)
        self.btn_start.pack(side='left', padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="Stop", command=self.stop_attendance, state='disabled')
        self.btn_stop.pack(side='left', padx=5)
        
        self.lbl_status = ttk.Label(control_frame, text="Status: STOPPED", foreground="red")
        self.lbl_status.pack(side='right', padx=5)
        
        # Logs
        log_frame = ttk.LabelFrame(parent, text="System Logs", padding=10)
        log_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.log_text = tk.Text(log_frame, height=15, state='disabled')
        self.log_text.pack(expand=True, fill='both', side='left')
        
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text['yscrollcommand'] = scrollbar.set

    def log_to_gui(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + "\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def start_attendance(self):
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.lbl_status.config(text="Status: RUNNING", foreground="green")
        self.system.start_scanning()

    def stop_attendance(self):
        self.system.stop_scanning()
        self.btn_start.config(state='normal')
        self.btn_stop.config(state='disabled')
        self.lbl_status.config(text="Status: STOPPED", foreground="red")

    # ----------------------------------------------------------------------
    # MANAGE STUDENTS
    # ----------------------------------------------------------------------
    def setup_manage(self, parent):
        # List
        self.tree = ttk.Treeview(parent, columns=('UID', 'Name', 'Phone', 'Class'), show='headings')
        self.tree.heading('UID', text='UID')
        self.tree.heading('Name', text='Student Name')
        self.tree.heading('Phone', text='Parent Phone')
        self.tree.heading('Class', text='Class')
        self.tree.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Refresh List", command=self.refresh_list).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Add Student (Scan)", command=self.add_student_flow).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_student).pack(side='right', padx=5)
        
        self.refresh_list()

    def refresh_list(self):
        # Clear
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Repopulate
        for uid, data in self.system.students_cache.items():
            self.tree.insert('', 'end', values=(uid, data['Name'], data['ParentPhone'], data['Class']))

    def add_student_flow(self):
        # 1. Ask to Scan
        msg = tk.Toplevel(self.root)
        msg.title("Scan Card")
        tk.Label(msg, text="Please scan the NEW card now...", padx=20, pady=20).pack()
        
        # Run scan in thread
        self.new_uid = None
        
        def scan_check():
            # Stop attendance loop momentarily if running? 
            # Ideally yes, but scan_once handles resource locking if designed well.
            # However, sharing SPI might be tricky. The main loop might enable 'running' flag.
            
            was_running = self.system.running
            if was_running:
                self.system.running = False # Pause loop logic
                # Wait for loop to finish current iteration?
                time.sleep(1) 
            
            # Try to read for 10 seconds
            start = time.time()
            found_uid = None
            
            while time.time() - start < 10:
                found_uid = self.system.scan_once()
                if found_uid: break
                time.sleep(0.2)
            
            if was_running:
                self.system.running = True # Resume
                threading.Thread(target=self.system._scan_loop, daemon=True).start()
            
            if found_uid:
                self.root.after(0, lambda: self.input_student_details(msg, found_uid))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "No card detected within 10 seconds."))
                self.root.after(0, msg.destroy)

        threading.Thread(target=scan_check).start()

    def input_student_details(self, popup, uid):
        popup.destroy()
        
        # Check if exists
        if uid in self.system.students_cache:
            messagebox.showwarning("Duplicate", f"Card {uid} is already registered!")
            return

        # Input Dialogs
        name = simpledialog.askstring("Input", f"Card Detected: {uid}\nEnter Student Name:")
        if not name: return
        
        phone = simpledialog.askstring("Input", "Enter Parent Phone:")
        if not phone: return
        
        student_class = simpledialog.askstring("Input", "Enter Class:")
        if not student_class: return
        
        # Save
        if self.system.add_student(uid, name, phone, student_class):
            messagebox.showinfo("Success", "Student Added Successfully!")
            self.refresh_list()
        else:
            messagebox.showerror("Error", "Failed to save to Cloud.")

    def delete_student(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a student first.")
            return
            
        uid = self.tree.item(selected[0])['values'][0]
        
        if messagebox.askyesno("Confirm", f"Delete student with UID {uid}?"):
            if self.system.delete_student(uid):
                messagebox.showinfo("Success", "Student Deleted.")
                self.refresh_list()
            else:
                messagebox.showerror("Error", "Failed to delete from Cloud.")

    def on_close(self):
        if self.system.running:
            self.system.stop_scanning()
        self.system.close()
        self.root.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = AttendanceApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Critical Error", str(e))
