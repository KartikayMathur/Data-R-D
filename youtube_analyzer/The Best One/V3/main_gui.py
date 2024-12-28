import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
from datetime import datetime
import json
import os
from browser_module import BrowserManager
from scraping_module import YouTubeScraper
from file_organization_module import FileOrganizer

class YouTubeAnalyzer:
    def __init__(self):
        self.setup_logging()
        self.root = tk.Tk()
        self.root.title("YouTube Channel Analyzer")
        self.root.geometry("800x600")
        self.setup_gui()
        self.browser_manager = BrowserManager()
        self.scraper = YouTubeScraper(self.browser_manager)
        self.file_organizer = FileOrganizer()
        self.is_running = False

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('youtube_analyzer.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_gui(self):
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Input section
        ttk.Label(self.main_frame, text="Search Keyword:").grid(row=0, column=0, sticky=tk.W)
        self.keyword_entry = ttk.Entry(self.main_frame, width=40)
        self.keyword_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E))

        ttk.Label(self.main_frame, text="Initial Videos to Analyze:").grid(row=1, column=0, sticky=tk.W)
        self.initial_videos_count = ttk.Spinbox(self.main_frame, from_=1, to=50, width=10)
        self.initial_videos_count.set(10)
        self.initial_videos_count.grid(row=1, column=1, sticky=tk.W)

        ttk.Label(self.main_frame, text="Top Videos per Channel:").grid(row=2, column=0, sticky=tk.W)
        self.top_videos_count = ttk.Spinbox(self.main_frame, from_=1, to=100, width=10)
        self.top_videos_count.set(12)
        self.top_videos_count.grid(row=2, column=1, sticky=tk.W)

        # Output directory selection
        ttk.Label(self.main_frame, text="Output Directory:").grid(row=3, column=0, sticky=tk.W)
        self.output_dir = ttk.Entry(self.main_frame, width=40)
        self.output_dir.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E))
        ttk.Button(self.main_frame, text="Browse", command=self.select_output_dir).grid(row=3, column=3)

        # Dependencies checker
        self.deps_var = tk.BooleanVar()
        ttk.Checkbutton(self.main_frame, text="Check/Install Dependencies",
                       variable=self.deps_var).grid(row=4, column=0, columnspan=2, sticky=tk.W)

        # Control buttons
        self.start_button = ttk.Button(self.main_frame, text="Start Analysis", command=self.start_analysis)
        self.start_button.grid(row=5, column=0)

        self.stop_button = ttk.Button(self.main_frame, text="Stop", command=self.stop_analysis, state=tk.DISABLED)
        self.stop_button.grid(row=5, column=1)

        # Progress section
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.main_frame, length=300, mode='determinate',
                                      variable=self.progress_var)
        self.progress.grid(row=6, column=0, columnspan=4, sticky=(tk.W, tk.E))

        # Status log
        self.log_text = tk.Text(self.main_frame, height=15, width=70)
        self.log_text.grid(row=7, column=0, columnspan=4, sticky=(tk.W, tk.E))
        scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=7, column=4, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = scrollbar.set

    def select_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir.delete(0, tk.END)
            self.output_dir.insert(0, directory)

    def start_analysis(self):
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please select an output directory")
            return

        if not self.keyword_entry.get():
            messagebox.showerror("Error", "Please enter a search keyword")
            return

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Start analysis in a separate thread
        threading.Thread(target=self.run_analysis, daemon=True).start()

    def stop_analysis(self):
        self.is_running = False
        self.log_message("Stopping analysis...")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def run_analysis(self):
        try:
            if self.deps_var.get() and not self.browser_manager.check_dependencies():
                messagebox.showerror("Error", "Failed to install dependencies")
                return

            if not self.browser_manager.setup_browser():
                messagebox.showerror("Error", "Failed to setup browser")
                return

            keyword = self.keyword_entry.get()
            output_base_dir = self.output_dir.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(output_base_dir, f"youtube_analysis_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)

            self.log_message(f"Starting analysis for keyword: {keyword}")

            # Search for videos
            videos = self.scraper.search_youtube(keyword, int(self.initial_videos_count.get()))
            if not videos:
                self.log_message("No videos found")
                return

            # Process each channel
            channel_data = []
            for i, video in enumerate(videos):
                if not self.is_running:
                    break

                try:
                    channel_link = video.find_element(By.CSS_SELECTOR, "#channel-name a").get_attribute("href")
                    channel_info = self.scraper.get_channel_info(channel_link, int(self.top_videos_count.get()))

                    if channel_info:
                        # Create channel directory
                        channel_dir = os.path.join(output_dir, channel_info['channel_name'])
                        os.makedirs(os.path.join(channel_dir, 'thumbnails'), exist_ok=True)

                        # Download thumbnails
                        for j, video_info in enumerate(channel_info['videos']):
                            thumbnail_path = os.path.join(channel_dir, 'thumbnails', f"video_{j+1}.jpg")
                            if self.scraper.download_thumbnail(video_info['thumbnail'], thumbnail_path):
                                video_info['thumbnail_path'] = thumbnail_path

                        channel_data.append(channel_info)

                        # Update progress
                        progress = (i + 1) / len(videos) * 100
                        self.progress_var.set(progress)
                        self.log_message(f"Processed channel: {channel_info['channel_name']}")
                except Exception as e:
                    self.log_message(f"Error processing video {i+1}: {str(e)}")

            if channel_data:
                self.file_organizer.create_excel_report(channel_data, output_dir)
                self.log_message("Analysis completed successfully")

        except Exception as e:
            self.log_message(f"Analysis failed: {str(e)}")
            self.logger.exception("Detailed error information:")
            # Show error message to user
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")

        finally:
            self.browser_manager.quit_browser()
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress_var.set(0)  # Reset progress bar

    def log_message(self, message):
        """Add a message to the log text widget and logging system"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        # Add to GUI log
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)

        # Add to system log
        self.logger.info(message)

    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = YouTubeAnalyzer()
    app.run()
