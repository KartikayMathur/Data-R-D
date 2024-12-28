# youtube_analyzer/src/gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os

from .scraper import Scraper
from .utils import setup_logging
from .analyzer import analyze_channels
from . import utils

def start_gui():
    # Create the main window
    root = tk.Tk()
    root.title("YouTube Analyzer")
    root.geometry("400x300")
    
    setup_logging()  # Initialize logging
    
    # Frames and layout
    input_frame = ttk.Frame(root, padding="10 10 10 10")
    input_frame.pack(fill=tk.BOTH, expand=True)
    
    keyword_label = ttk.Label(input_frame, text="Enter Keyword:")
    keyword_label.pack(pady=5)
    
    keyword_var = tk.StringVar()
    keyword_entry = ttk.Entry(input_frame, textvariable=keyword_var, width=30)
    keyword_entry.pack(pady=5)
    
    browser_label = ttk.Label(input_frame, text="Select Browser:")
    browser_label.pack(pady=5)
    
    browser_var = tk.StringVar(value="Chrome")
    browser_options = ["Chrome", "Firefox", "Edge"]  # or whichever browsers you support
    browser_dropdown = ttk.Combobox(input_frame, textvariable=browser_var, values=browser_options, state="readonly")
    browser_dropdown.pack(pady=5)
    
    progress_label = ttk.Label(input_frame, text="")
    progress_label.pack(pady=5)
    
    def run_analysis():
        keyword = keyword_var.get().strip()
        if not keyword:
            messagebox.showerror("Error", "Please enter a keyword.")
            return
        
        progress_label.config(text="Starting analysis...")
        
        # Run scraping and analysis in a separate thread to keep GUI responsive
        def worker():
            scraper = Scraper(browser=browser_var.get())
            try:
                channels_data = scraper.scrape_channels(keyword)
                # Analyze channels data
                analyze_channels(channels_data)
                progress_label.config(text="Analysis complete! Check data folder.")
            except Exception as e:
                utils.log_error(e)
                messagebox.showerror("Error", f"An error occurred: {e}")
            finally:
                scraper.close()
        
        thread = threading.Thread(target=worker)
        thread.start()
        
    start_button = ttk.Button(input_frame, text="Start", command=run_analysis)
    start_button.pack(pady=10)
    
    root.mainloop()
