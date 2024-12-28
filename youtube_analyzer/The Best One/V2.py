import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import sys
import os
import json
import time
import logging
import threading
from datetime import datetime
from PIL import Image, ImageTk
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc

class YouTubeAnalyzer:
    def __init__(self):
        self.setup_logging()
        self.root = tk.Tk()
        self.root.title("YouTube Channel Analyzer")
        self.root.geometry("800x600")
        self.setup_gui()
        self.driver = None
        self.is_running = False
        self.current_task = None

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

    def check_dependencies(self):
        required_packages = [
            'selenium', 'pandas', 'Pillow', 'requests', 'openpyxl',
            'undetected-chromedriver'
        ]

        self.log_message("Checking dependencies...")
        missing_packages = []

        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            self.log_message(f"Installing missing packages: {', '.join(missing_packages)}")
            for package in missing_packages:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                    self.log_message(f"Successfully installed {package}")
                except subprocess.CalledProcessError as e:
                    self.log_message(f"Failed to install {package}: {str(e)}")
                    return False

        self.log_message("All dependencies are installed.")
        return True

    def setup_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        try:
            self.driver = uc.Chrome(options=options)
            self.log_message("Browser setup successful")
            return True
        except Exception as e:
            self.log_message(f"Failed to setup browser: {str(e)}")
            return False

    def search_youtube(self, keyword):
        try:
            search_url = f"https://www.youtube.com/results?search_query={keyword}&sp=CAMSAhAB"
            self.driver.get(search_url)
            time.sleep(3)  # Allow time for dynamic content to load

            videos = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-video-renderer"))
            )

            return videos[:int(self.initial_videos_count.get())]
        except Exception as e:
            self.log_message(f"Error during YouTube search: {str(e)}")
            return []

    def get_channel_info(self, channel_url):
        try:
            self.driver.get(channel_url)
            time.sleep(3)

            channel_name = self.driver.find_element(By.CSS_SELECTOR, "#channel-name").text
            subscriber_count = self.driver.find_element(By.CSS_SELECTOR, "#subscriber-count").text

            # Switch to Videos tab and sort by popularity
            videos_tab = self.driver.find_element(By.CSS_SELECTOR, "tp-yt-paper-tab:nth-child(4)")
            videos_tab.click()
            time.sleep(2)

            sort_button = self.driver.find_element(By.CSS_SELECTOR, "#sort-menu")
            sort_button.click()
            time.sleep(1)

            popularity_option = self.driver.find_element(By.CSS_SELECTOR, "tp-yt-paper-listbox > a:nth-child(3)")
            popularity_option.click()
            time.sleep(3)

            return {
                'channel_name': channel_name,
                'subscriber_count': subscriber_count,
                'videos': self.get_video_info(int(self.top_videos_count.get()))
            }
        except Exception as e:
            self.log_message(f"Error getting channel info: {str(e)}")
            return None

    def get_video_info(self, count):
        videos = []
        try:
            video_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-grid-video-renderer"))
            )

            for video in video_elements[:count]:
                title = video.find_element(By.CSS_SELECTOR, "#video-title").text
                views = video.find_element(By.CSS_SELECTOR, "#metadata-line > span:nth-child(1)").text
                date = video.find_element(By.CSS_SELECTOR, "#metadata-line > span:nth-child(2)").text
                url = video.find_element(By.CSS_SELECTOR, "#video-title").get_attribute("href")
                thumbnail = video.find_element(By.CSS_SELECTOR, "img").get_attribute("src")

                videos.append({
                    'title': title,
                    'views': views,
                    'date': date,
                    'url': url,
                    'thumbnail': thumbnail
                })
        except Exception as e:
            self.log_message(f"Error getting video info: {str(e)}")

        return videos

    def download_thumbnail(self, url, filepath):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            self.log_message(f"Error downloading thumbnail: {str(e)}")
        return False

    def create_excel_report(self, data, output_dir):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"youtube_analysis_{timestamp}.xlsx")

            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Channel Overview sheet
                channel_data = []
                for channel in data:
                    channel_data.append({
                        'Channel Name': channel['channel_name'],
                        'Subscribers': channel['subscriber_count'],
                        'Videos Analyzed': len(channel['videos'])
                    })

                pd.DataFrame(channel_data).to_excel(writer, sheet_name='Channel Overview', index=False)

                # Video Details sheet
                video_data = []
                for channel in data:
                    for video in channel['videos']:
                        video_data.append({
                            'Channel': channel['channel_name'],
                            'Title': video['title'],
                            'Views': video['views'],
                            'Upload Date': video['date'],
                            'URL': video['url'],
                            'Thumbnail Path': video.get('thumbnail_path', '')
                        })

                pd.DataFrame(video_data).to_excel(writer, sheet_name='Video Details', index=False)

            self.log_message(f"Excel report created: {filename}")
            return filename
        except Exception as e:
            self.log_message(f"Error creating Excel report: {str(e)}")
            return None

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
            if self.deps_var.get() and not self.check_dependencies():
                messagebox.showerror("Error", "Failed to install dependencies")
                return

            if not self.setup_browser():
                messagebox.showerror("Error", "Failed to setup browser")
                return

            keyword = self.keyword_entry.get()
            output_base_dir = self.output_dir.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(output_base_dir, f"youtube_analysis_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)

            self.log_message(f"Starting analysis for keyword: {keyword}")

            # Search for videos
            videos = self.search_youtube(keyword)
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
                    channel_info = self.get_channel_info(channel_link)

                    if channel_info:
                        # Create channel directory
                        channel_dir = os.path.join(output_dir, channel_info['channel_name'])
                        os.makedirs(os.path.join(channel_dir, 'thumbnails'), exist_ok=True)

                        # Download thumbnails
                        for j, video_info in enumerate(channel_info['videos']):
                            thumbnail_path = os.path.join(channel_dir, 'thumbnails', f"video_{j+1}.jpg")
                            if self.download_thumbnail(video_info['thumbnail'], thumbnail_path):
                                video_info['thumbnail_path'] = thumbnail_path

                        channel_data.append(channel_info)

                        # Update progress
                        progress = (i + 1) / len(videos) * 100
                        self.progress_var.set(progress)
                        self.log_message(f"Processed channel: {channel_info['channel_name']}")
                except Exception as e:
                    self.log_message(f"Error processing video {i+1}: {str(e)}")

            if channel_data:
                self.create_excel_report(channel_data, output_dir)
                self.log_message("Analysis completed successfully")

        except Exception as e:
            self.log_message(f"Analysis failed: {str(e)}")
            self.logger.exception("Detailed error information:")
            # Show error message to user
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")

        finally:
            if self.driver:
                self.driver.quit()
            self.driver = None
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

    def update_progress(self, value):
        """Update the progress bar value"""
        self.progress_var.set(value)
        self.root.update_idletasks()

    def validate_inputs(self):
        """Validate user inputs before starting analysis"""
        if not self.keyword_entry.get().strip():
            messagebox.showerror("Error", "Please enter a search keyword")
            return False

        try:
            initial_count = int(self.initial_videos_count.get())
            top_count = int(self.top_videos_count.get())

            if initial_count < 1 or top_count < 1:
                messagebox.showerror("Error", "Video counts must be positive numbers")
                return False

            if initial_count > 50:
                messagebox.showerror("Error", "Initial videos count cannot exceed 50")
                return False

            if top_count > 100:
                messagebox.showerror("Error", "Top videos per channel cannot exceed 100")
                return False

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for video counts")
            return False

        if not self.output_dir.get().strip():
            messagebox.showerror("Error", "Please select an output directory")
            return False

        if not os.path.isdir(self.output_dir.get()):
            messagebox.showerror("Error", "Selected output directory does not exist")
            return False

        return True

    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Select Output Directory", command=self.select_output_dir)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Check Dependencies", command=self.check_dependencies)
        tools_menu.add_command(label="Clear Log", command=lambda: self.log_text.delete(1.0, tk.END))

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def show_about(self):
        """Show about dialog"""
        about_text = """YouTube Channel Analyzer
Version 1.0

A tool for analyzing YouTube channels and their content.
Created with Python using Selenium and tkinter.

© 2024"""

        messagebox.showinfo("About", about_text)

    def save_preferences(self):
        """Save current preferences to a JSON file"""
        prefs = {
            'last_directory': self.output_dir.get(),
            'initial_videos': self.initial_videos_count.get(),
            'top_videos': self.top_videos_count.get(),
            'check_dependencies': self.deps_var.get()
        }

        try:
            with open('preferences.json', 'w') as f:
                json.dump(prefs, f)
        except Exception as e:
            self.log_message(f"Error saving preferences: {str(e)}")

    def load_preferences(self):
        """Load saved preferences from JSON file"""
        try:
            if os.path.exists('preferences.json'):
                with open('preferences.json', 'r') as f:
                    prefs = json.load(f)

                if 'last_directory' in prefs and os.path.isdir(prefs['last_directory']):
                    self.output_dir.insert(0, prefs['last_directory'])

                if 'initial_videos' in prefs:
                    self.initial_videos_count.set(prefs['initial_videos'])

                if 'top_videos' in prefs:
                    self.top_videos_count.set(prefs['top_videos'])

                if 'check_dependencies' in prefs:
                    self.deps_var.set(prefs['check_dependencies'])

        except Exception as e:
            self.log_message(f"Error loading preferences: {str(e)}")

    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.save_preferences()
            if self.driver:
                self.driver.quit()
            self.root.destroy()

    def run(self):
        """Start the application"""
        self.create_menu()
        self.load_preferences()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

def main():
    """Main entry point for the application"""
    try:
        app = YouTubeAnalyzer()
        app.run()
    except Exception as e:
        logging.error(f"Application failed to start: {str(e)}")
        messagebox.showerror("Error", f"Application failed to start: {str(e)}")

if __name__ == "__main__":
    main()
