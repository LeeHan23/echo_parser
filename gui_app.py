import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import threading
import sys
import os
import queue

# Import the processing logic
try:
    import echo_parser
except ImportError:
    # If running as executable, we might need to adjust path or it's bundled
    pass

class EchoParserGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Echo Report Parser")
        self.root.geometry("600x450")

        # Variables
        self.input_dir = tk.StringVar()
        self.is_processing = False
        self.log_queue = queue.Queue()

        # UI Layout
        self.create_widgets()
        
        # Start checking queue
        self.root.after(100, self.process_log_queue)

    def create_widgets(self):
        # Header
        header_frame = tk.Frame(self.root, pady=10)
        header_frame.pack(fill="x", padx=10)
        
        tk.Label(header_frame, text="Echo Report Parser", font=("Arial", 16, "bold")).pack()
        tk.Label(header_frame, text="Extract data from Echo PDF reports to Excel", font=("Arial", 10)).pack()

        # Input Selection
        input_frame = tk.Frame(self.root, pady=5)
        input_frame.pack(fill="x", padx=10)
        
        tk.Label(input_frame, text="Input Folder:").pack(side="left")
        tk.Entry(input_frame, textvariable=self.input_dir, width=50).pack(side="left", padx=5)
        tk.Button(input_frame, text="Browse", command=self.browse_folder).pack(side="left")

        # Log Area
        log_frame = tk.Frame(self.root, pady=10)
        log_frame.pack(fill="both", expand=True, padx=10)
        
        tk.Label(log_frame, text="Status Log:").pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        # Actions
        action_frame = tk.Frame(self.root, pady=10)
        action_frame.pack(fill="x", padx=10)
        
        self.start_btn = tk.Button(action_frame, text="Start Processing", command=self.start_processing_thread, bg="#4CAF50", fg="black", font=("Arial", 12, "bold"))
        self.start_btn.pack(fill="x")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_dir.set(folder)
            self.log(f"Selected input folder: {folder}")

    def log(self, message):
        self.log_queue.put(message)

    def process_log_queue(self):
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.log_text.config(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(100, self.process_log_queue)

    def start_processing_thread(self):
        input_path = self.input_dir.get()
        if not input_path:
            messagebox.showwarning("Input Required", "Please select an input folder first.")
            return
            
        if self.is_processing:
            return

        # Disable button
        self.start_btn.config(state="disabled", text="Processing...")
        self.is_processing = True
        
        # Ask for save location
        output_file = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile="echo_dataset_annotations.xlsx",
            title="Save Output As"
        )
        
        if not output_file:
            self.start_btn.config(state="normal", text="Start Processing")
            self.is_processing = False
            return

        # Start thread
        thread = threading.Thread(target=self.run_processing, args=(input_path, output_file))
        thread.start()

    def run_processing(self, input_path, output_file):
        try:
            # We need to import echo_parser here if it's not at top level or to handle errors gracefully
            # Note: in a packaged app, echo_parser logic should be available.
            
            self.log("-" * 40)
            self.log(f"Starting processing for: {input_path}")
            self.log(f"Saving to: {output_file}")
            
            echo_parser.process_directory(input_path, output_file, log_callback=self.log)
            
            self.log("Done!")
            messagebox.showinfo("Success", "Processing Complete!")
            
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
        finally:
            self.root.after(0, self.reset_ui)

    def reset_ui(self):
        self.is_processing = False
        self.start_btn.config(state="normal", text="Start Processing")

if __name__ == "__main__":
    # If running from PyInstaller, we need to ensure local modules are found?
    # Usually PyInstaller handles imports fine if they are at top level.
    
    root = tk.Tk()
    app = EchoParserGUI(root)
    root.mainloop()
