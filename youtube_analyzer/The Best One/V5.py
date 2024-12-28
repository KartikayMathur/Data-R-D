import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import subprocess
import sys
import os
import json
import time
import logging
import threading
from datetime import datetime
import re

# Data handling
import pandas as pd

# Network requests / images
import requests
from PIL import Image, ImageTk

# Selenium / browser automation
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# OCR and image processing
import pytesseract
from PIL import Image

class YouTubeAnalyzerDemo:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube Analyzer - Demonstration with Updated Extractors")
        self.root.geometry("930x680")
        self.root.minsize(800, 600)

        # Internal state
        self.is_running = False
        self.driver = None

        # Setup logging
        self.setup_logging()

        # Build GUI
        self.create_widgets()

    def setup_logging(self):
        """Configure logging to both file and console."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('youtube_analyzer_qmenu.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_widgets(self):
        """Set up the main tkinter UI."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Expandable row for the log text
        main_frame.grid_rowconfigure(9, weight=1)

        # --- Row 0: Keyword ---
        ttk.Label(main_frame, text="Search Keyword:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.keyword_entry = ttk.Entry(main_frame, width=40)
        self.keyword_entry.grid(row=0, column=1, columnspan=3, sticky="ew", pady=5)

        # --- Row 1: #Channels to find ---
        ttk.Label(main_frame, text="Max Channels:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_channels_spin = ttk.Spinbox(main_frame, from_=1, to=200, width=10)
        self.max_channels_spin.set(5)
        self.max_channels_spin.grid(row=1, column=1, sticky=tk.W, pady=5)

        # --- Row 2: #Videos per channel ---
        ttk.Label(main_frame, text="Top Videos per Channel:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.top_videos_spin = ttk.Spinbox(main_frame, from_=1, to=200, width=10)
        self.top_videos_spin.set(3)
        self.top_videos_spin.grid(row=2, column=1, sticky=tk.W, pady=5)

        # --- Row 3: Output Directory ---
        ttk.Label(main_frame, text="Output Directory:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_dir_entry = ttk.Entry(main_frame, width=40)
        self.output_dir_entry.grid(row=3, column=1, columnspan=3, sticky="ew", pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.select_output_dir).grid(row=3, column=4, padx=5, pady=5)

        # --- Row 4: Dependency check & Q-menu toggles ---
        self.deps_check_var = tk.BooleanVar(value=False)
        self.qmenu_var = tk.BooleanVar(value=False)
        self.new_selectors_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            main_frame, text="Check & Install Dependencies", variable=self.deps_check_var
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        ttk.Checkbutton(
            main_frame, text="Enable Q-Menu (manual selectors if fails)", variable=self.qmenu_var
        ).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        ttk.Checkbutton(
            main_frame, text="Use New YouTube Selectors", variable=self.new_selectors_var
        ).grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # --- Row 7: Control Buttons ---
        self.start_button = ttk.Button(main_frame, text="Start Analysis", command=self.start_analysis)
        self.start_button.grid(row=7, column=0, padx=5, pady=5)

        self.stop_button = ttk.Button(main_frame, text="Stop", command=self.stop_analysis, state=tk.DISABLED)
        self.stop_button.grid(row=7, column=1, padx=5, pady=5)

        # --- Row 7 (cont): Progress ---
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100, length=300)
        self.progress_bar.grid(row=7, column=2, columnspan=3, sticky=tk.W, padx=5, pady=5)

        # --- Row 9: Log Text ---
        self.log_text = tk.Text(main_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=9, column=0, columnspan=5, sticky="nsew", padx=5, pady=5)
        scroll_y = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scroll_y.grid(row=9, column=5, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scroll_y.set)

    def select_output_dir(self):
        """Prompt user for output directory."""
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, directory)

    def check_and_install_dependencies(self):
        """Check & install required packages if needed."""
        self.log("Checking for required dependencies...")
        required_packages = [
            "selenium",
            "pandas",
            "Pillow",
            "requests",
            "openpyxl",
            "undetected-chromedriver",
            "pytesseract"
        ]

        missing_packages = []
        for pkg in required_packages:
            try:
                __import__(pkg.replace('-', '_'))
            except ImportError:
                missing_packages.append(pkg)

        if missing_packages:
            self.log(f"Installing missing packages: {', '.join(missing_packages)}")
            for pkg in missing_packages:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                    self.log(f"Installed {pkg}")
                except subprocess.CalledProcessError as e:
                    self.log(f"Failed to install {pkg}: {str(e)}")
                    return False

        self.log("All dependencies are installed.")
        return True

    def start_analysis(self):
        """Validate input, then start a new thread for analysis."""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showerror("Error", "Please enter a search keyword.")
            return

        out_dir = self.output_dir_entry.get().strip()
        if not out_dir:
            messagebox.showerror("Error", "Please select an output directory.")
            return
        if not os.path.isdir(out_dir):
            messagebox.showerror("Error", "Specified output directory does not exist.")
            return

        try:
            max_channels = int(self.max_channels_spin.get())
            top_videos_count = int(self.top_videos_spin.get())
            if max_channels < 1 or top_videos_count < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter positive integers for channels/videos counts.")
            return

        # Check & install dependencies if checkbox is selected
        if self.deps_check_var.get():
            if not self.check_and_install_dependencies():
                return

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.log_text.delete("1.0", tk.END)

        threading.Thread(target=self.run_analysis, daemon=True).start()

    def stop_analysis(self):
        """User requests stopping."""
        self.is_running = False
        self.log("Stop requested by user...")

    def run_analysis(self):
        """Main scraping logic."""
        try:
            if not self.setup_browser():
                self.log("Failed to launch browser driver. Stopping.")
                return

            keyword = self.keyword_entry.get().strip()
            max_channels = int(self.max_channels_spin.get())
            top_videos_count = int(self.top_videos_spin.get())
            base_path = self.output_dir_entry.get().strip()

            # Create a "youtube_analysis" folder in the base path
            analysis_dir = os.path.join(base_path, "youtube_analysis")
            os.makedirs(analysis_dir, exist_ok=True)

            # Step 1) Search for channels
            self.log(f"Searching YouTube for channels matching: {keyword}")
            channels_data = self.search_channels_demo(keyword, max_channels)

            total_channels = len(channels_data)
            all_channel_data = []

            for idx, channel_info in enumerate(channels_data, start=1):
                if not self.is_running:
                    break
                self.update_progress((idx / total_channels) * 100)

                channel_name = channel_info.get("channel_name", "UnknownChannel")
                channel_url = channel_info.get("channel_url", "")

                self.log(f"[{idx}/{total_channels}] Processing channel: {channel_name}")
                if not channel_url:
                    self.log("No channel URL found, skipping.")
                    continue

                # Step 2) Channel stats
                stats = self.scrape_channel_stats(channel_url)

                # Step 3) "Popular" tab -> top N videos
                videos_data = self.scrape_popular_videos(channel_url, top_videos_count)

                # Combine
                full_data = {
                    "channel_name": channel_name,
                    "channel_url": channel_url,
                    "stats": stats,
                    "videos": videos_data
                }
                all_channel_data.append(full_data)

                # Step 4) Save data in subfolder
                self.save_channel_data(analysis_dir, full_data)

            # Step 5) Summary
            if all_channel_data:
                self.create_summary_excel(analysis_dir, all_channel_data)
                self.log(f"Analysis complete! See folder: {analysis_dir}")
                messagebox.showinfo("Analysis Complete", f"Data saved in:\n{analysis_dir}")
            else:
                self.log("No channel data to save.")
                messagebox.showinfo("No Data", "No valid channels were found or analyzed.")

        except Exception as e:
            self.log(f"Analysis failed: {e}", level="error")
            messagebox.showerror("Error", f"Analysis failed:\n{str(e)}")
        finally:
            self.cleanup_browser()
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress_var.set(0)

    def setup_browser(self):
        """Initialize undetected Chrome driver."""
        try:
            options = uc.ChromeOptions()
            # options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            self.driver = uc.Chrome(options=options)
            self.driver.set_window_size(1280, 800)
            return True
        except Exception as e:
            self.log(f"Browser setup error: {e}", level="error")
            return False

    def cleanup_browser(self):
        """Close the browser driver if open."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def search_channels_demo(self, keyword, max_channels):
        """Search YouTube by keyword, gather up to max_channels from ytd-channel-renderer (demo)."""
        search_url = f"https://www.youtube.com/results?search_query={keyword}"
        self.driver.get(search_url)
        time.sleep(2)

        found_channels = []
        tries = 0
        max_tries = 5

        while len(found_channels) < max_channels and tries < max_tries and self.is_running:
            try:
                channel_elems = self.driver.find_elements(By.CSS_SELECTOR, "ytd-channel-renderer")
                for ce in channel_elems:
                    if len(found_channels) >= max_channels:
                        break
                    try:
                        link_elem = ce.find_element(By.CSS_SELECTOR, "a#main-link")
                        ch_url = link_elem.get_attribute("href")
                        ch_name = link_elem.text.strip() or "Unnamed"

                        found_channels.append({
                            "channel_name": ch_name,
                            "channel_url": ch_url
                        })
                        self.log(f"Found channel: {ch_name}")
                    except Exception as e:
                        self.log(f"Skipping channel: {e}", "debug")
            except Exception as e:
                self.log(f"Error searching channels: {e}", "debug")

            if len(found_channels) < max_channels:
                self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                tries += 1

        self.log(f"Discovered {len(found_channels)} channel(s).")
        return found_channels

    def scrape_channel_stats(self, channel_url):
        """
        Attempt to parse:
         - channel name (if needed)
         - subscriber count
         - total videos
         - description
        from the /about page or from the new snippet if needed.
        """
        stats = {
            "subscribers": "N/A",
            "total_videos": "N/A",
            "description": "N/A"
        }
        try:
            about_url = channel_url.rstrip('/') + "/about"
            self.driver.get(about_url)
            time.sleep(2)

            # Capture screenshot of the about page
            screenshot_path = "about_section.png"
            self.driver.save_screenshot(screenshot_path)

            # Use OCR to extract text from the screenshot
            text = self.extract_text_from_image(screenshot_path)

            # Parse the extracted text
            stats = self.parse_channel_stats(text)

        except Exception as e:
            self.log(f"Channel stats error: {e}", level="error")

        return stats

    def extract_text_from_image(self, image_path):
        """Use OCR to extract text from an image."""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            self.log(f"OCR error: {e}", level="error")
            return ""

    def parse_channel_stats(self, text):
        """Parse the extracted text to get channel stats."""
        stats = {
            "subscribers": "N/A",
            "total_videos": "N/A",
            "description": "N/A"
        }
        try:
            # Parse subscribers
            subscribers_match = re.search(r"(\d[\d,]*) subscribers?", text, re.IGNORECASE)
            if subscribers_match:
                stats["subscribers"] = subscribers_match.group(1)

            # Parse total videos
            videos_match = re.search(r"(\d[\d,]*) videos?", text, re.IGNORECASE)
            if videos_match:
                stats["total_videos"] = videos_match.group(1)

            # Parse description
            description_match = re.search(r"Description\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
            if description_match:
                stats["description"] = description_match.group(1).strip()

        except Exception as e:
            self.log(f"Parsing error: {e}", level="error")

        return stats

    def scrape_popular_videos(self, channel_url, max_videos):
        """Open channel > 'Popular' tab, scrape up to max_videos, open each video, parse new snippet."""
        videos_data = []
        try:
            videos_url = channel_url.rstrip('/') + "/videos"
            self.driver.get(videos_url)
            time.sleep(2)

            # Attempt to click "Popular" tab
            try:
                popular_tab = self.safe_find_element(
                    "xpath", '//yt-formatted-string[@title="Popular"]',
                    qprompt_name="Popular Tab", wait_secs=3
                )
                if popular_tab:
                    popular_tab.click()
                    time.sleep(2)
            except:
                self.log("Could not click 'Popular' tab. Using default ordering (Latest?).")

            # Gather up to max_videos
            scroll_attempts = 0
            while len(videos_data) < max_videos and scroll_attempts < 8 and self.is_running:
                grid_items = self.driver.find_elements(By.CSS_SELECTOR, "ytd-grid-video-renderer")
                for gi in grid_items:
                    if len(videos_data) >= max_videos:
                        break
                    try:
                        vid_title_elem = gi.find_element(By.CSS_SELECTOR, "a#video-title")
                        vid_title = vid_title_elem.text.strip()
                        vid_url = vid_title_elem.get_attribute("href")

                        data_dict = self.scrape_video_details(vid_url, vid_title)
                        videos_data.append(data_dict)
                    except Exception as e:
                        self.log(f"Error scraping video item: {e}", level="debug")
                if len(videos_data) < max_videos:
                    self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                    time.sleep(2)
                    scroll_attempts += 1

        except Exception as e:
            self.log(f"scrape_popular_videos error: {e}", level="error")

        return videos_data[:max_videos]

    def scrape_video_details(self, video_url, video_title):
        """
        Open video, parse (1) 'channel' snippet, (2) 'title' snippet,
        (3) 'views & upload date', (4) 'likes', (5) 'thumbnailUrl' etc.
        """
        result = {
            "title": video_title,
            "url": video_url,
            "channel": "N/A",
            "views": "N/A",
            "upload_date": "N/A",
            "likes": "N/A",
            "thumbnail_url": "N/A"
        }
        try:
            main_handle = self.driver.current_window_handle
            self.driver.execute_script(f"window.open('{video_url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(2)

            # 1) Channel name (from new snippet):
            #   e.g. <span class="yt-core-attributed-string ...">askNK ...</span>
            chan_elem = self.safe_find_element(
                "css",
                "span.yt-core-attributed-string.yt-core-attributed-string--white-space-pre-wrap",
                qprompt_name="Video Channel Span",
                wait_secs=3
            )
            if chan_elem:
                result["channel"] = chan_elem.text.strip()

            # 2) Title (from new snippet):
            #   e.g. <yt-formatted-string class="style-scope ytd-watch-metadata">Title here</yt-formatted-string>
            title_elem = self.safe_find_element(
                "css",
                "yt-formatted-string.style-scope.ytd-watch-metadata",
                qprompt_name="Video Title",
                wait_secs=3
            )
            if title_elem:
                result["title"] = title_elem.text.strip()

            # 3) Views & Upload date together:
            #   e.g. <yt-formatted-string id="info" class="style-scope ytd-watch-info-text">
            #          <span dir="auto" ...>19K views</span>
            #          <span dir="auto" ...>1 day ago</span>
            #        </yt-formatted-string>
            info_elem = self.safe_find_element(
                "css",
                "yt-formatted-string#info.style-scope.ytd-watch-info-text",
                qprompt_name="Views/Date info",
                wait_secs=3
            )
            if info_elem:
                text_info = info_elem.text.strip()  # e.g. "19K views  1 day ago  #asknk #something"
                # Quick parse or regex for "(\S+ views).*(\d+ day[s]? ago|...)"
                # For demonstration:
                match_views = re.search(r'(\S+\sviews)', text_info)
                match_date = re.search(r'(\d+\s\w+\sago|\d+\sday[s]?\sago)', text_info)
                if match_views:
                    result["views"] = match_views.group(1)
                if match_date:
                    result["upload_date"] = match_date.group(1)

            # 4) Likes:
            #   e.g. <button ... aria-label="like this video along with 836 other people" ...>
            #         <div class="yt-spec-button-shape-next__button-text-content">836</div>
            #       ...
            # We'll attempt a direct approach:
            like_btn = self.safe_find_element(
                "css",
                'button[aria-label^="like this video along"] div.yt-spec-button-shape-next__button-text-content',
                qprompt_name="Likes Button Div",
                wait_secs=3
            )
            if like_btn:
                result["likes"] = like_btn.text.strip()

            # 5) Check page source for "thumbnailUrl" (like in the original script)
            page_source = self.driver.page_source
            match_thumb = re.search(r'"thumbnailUrl":"([^"]+)"', page_source)
            if match_thumb:
                thumb_url = match_thumb.group(1)
                result["thumbnail_url"] = thumb_url

        except Exception as e:
            self.log(f"scrape_video_details error: {e}", level="debug")
        finally:
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(main_handle)

        return result

    def safe_find_element(self, by_method, selector, qprompt_name="Element", wait_secs=5):
        """
        Attempt a find_element with the given by_method & selector.
        If fails and Q-menu is enabled, prompt user for a new selector, then retry.
        """
        try:
            if by_method == "css":
                elem = WebDriverWait(self.driver, wait_secs).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            elif by_method == "xpath":
                elem = WebDriverWait(self.driver, wait_secs).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
            else:
                raise ValueError("Unsupported by_method")
            return elem
        except:
            self.log(f"Could not find {qprompt_name} with {by_method}='{selector}'", "debug")
            if self.qmenu_var.get():
                # Q-menu: ask user for a new selector
                new_selector = simpledialog.askstring(
                    "Q-Menu: Missing Element",
                    f"Failed to find {qprompt_name}.\n\nEnter a new {by_method.upper()} selector or 'skip':",
                    parent=self.root
                )
                if new_selector and new_selector.lower() != "skip":
                    try:
                        if by_method == "css":
                            elem = WebDriverWait(self.driver, wait_secs).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, new_selector))
                            )
                        else:
                            elem = WebDriverWait(self.driver, wait_secs).until(
                                EC.presence_of_element_located((By.XPATH, new_selector))
                            )
                        return elem
                    except:
                        self.log(f"Q-menu: Still cannot find {qprompt_name}. Skipping...", "debug")
                        return None
            return None

    def save_channel_data(self, base_dir, channel_data):
        """
        Save data for a single channel:
          1) channel_stats.json
          2) videos_data.xlsx
          3) thumbnails => videoTitle_thumb.jpg
        """
        ch_name = channel_data.get("channel_name", "NoName")
        # The crucial fix: remove newlines and invalid path chars:
        safe_ch_name = re.sub(r'[<>:"/\\|?*\r\n]+', ' ', ch_name).strip()
        # If channel_name is extremely long, consider truncating:
        if len(safe_ch_name) > 100:
            safe_ch_name = safe_ch_name[:100]

        ch_folder = os.path.join(base_dir, safe_ch_name)
        os.makedirs(ch_folder, exist_ok=True)

        # Save stats:
        stats_file = os.path.join(ch_folder, "channel_stats.json")
        try:
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump({
                    "channel_name": ch_name,
                    "channel_url": channel_data.get("channel_url", ""),
                    "stats": channel_data.get("stats", {})
                }, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"Failed to save channel_stats.json: {e}", level="error")

        # Prepare videos & thumbnails
        thumb_dir = os.path.join(ch_folder, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)

        video_list = channel_data.get("videos", [])
        recs = []
        for vid in video_list:
            # sanitize title
            raw_title = vid.get("title", "NoTitle")
            safe_title = re.sub(r'[<>:"/\\|?*\r\n]+', ' ', raw_title).strip()
            if len(safe_title) > 100:  # optional
                safe_title = safe_title[:100]

            thumb_name = f"{safe_title}_thumb.jpg"
            thumb_path = os.path.join(thumb_dir, thumb_name)

            thumb_url = vid.get("thumbnail_url", "")
            saved_thumb = None
            if thumb_url:
                saved_thumb = self.download_thumbnail(thumb_url, thumb_path)

            recs.append({
                "Channel": vid.get("channel", "N/A"),
                "Title": raw_title,
                "URL": vid.get("url", ""),
                "Views": vid.get("views", "N/A"),
                "Likes": vid.get("likes", "N/A"),
                "Upload Date": vid.get("upload_date", "N/A"),
                "Thumbnail URL": thumb_url,
                "Thumbnail Path": saved_thumb if saved_thumb else "Not downloaded"
            })

        # Save to Excel
        videos_file = os.path.join(ch_folder, "videos_data.xlsx")
        try:
            df = pd.DataFrame(recs)
            df.to_excel(videos_file, index=False, sheet_name="Videos")
        except Exception as e:
            self.log(f"Failed to save videos_data.xlsx: {e}", level="error")

    def download_thumbnail(self, url, path):
        """Download thumbnail from url to path. Return path if OK, else None."""
        if not url:
            return None
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    f.write(r.content)
                return path
        except Exception as e:
            self.log(f"Thumbnail download error: {e}", level="debug")
        return None

    def create_summary_excel(self, base_dir, channel_data_list):
        """
        Create an 'analysis_summary.xlsx' with:
          1) Channels Overview
          2) All Videos
        """
        summary_path = os.path.join(base_dir, "analysis_summary.xlsx")

        try:
            channels_info = []
            all_videos = []

            for c in channel_data_list:
                ch_stats = c.get("stats", {})
                channels_info.append({
                    "Channel Name": c.get("channel_name", ""),
                    "Channel URL": c.get("channel_url", ""),
                    "Subscribers": ch_stats.get("subscribers", "N/A"),
                    "Total Videos": ch_stats.get("total_videos", "N/A")
                })
                vids = c.get("videos", [])
                for v in vids:
                    all_videos.append({
                        "Channel": v.get("channel", "N/A"),
                        "Title": v.get("title", ""),
                        "URL": v.get("url", ""),
                        "Views": v.get("views", "N/A"),
                        "Likes": v.get("likes", "N/A"),
                        "Upload Date": v.get("upload_date", "N/A")
                    })

            df_channels = pd.DataFrame(channels_info)
            df_videos = pd.DataFrame(all_videos)

            with pd.ExcelWriter(summary_path, engine="openpyxl") as writer:
                df_channels.to_excel(writer, sheet_name="Channels Overview", index=False)
                df_videos.to_excel(writer, sheet_name="All Videos", index=False)

            self.log(f"Created summary Excel at: {summary_path}")
        except Exception as e:
            self.log(f"Error creating analysis_summary.xlsx: {e}", level="error")

    def update_progress(self, value):
        """Update progress bar safely."""
        self.progress_var.set(value)
        self.root.update_idletasks()

    def log(self, message, level="info"):
        """
        Log to console/file and add to the text widget.
        levels: "info", "debug", "error", etc.
        """
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        full_message = f"{timestamp} {message}\n"

        if level == "debug":
            self.logger.debug(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        else:
            self.logger.info(message)

        self.log_text.insert(tk.END, full_message)
        self.log_text.see(tk.END)

    def on_closing(self):
        """Confirm quit if analysis is running."""
        if self.is_running:
            if not messagebox.askokcancel("Quit", "Analysis is running. Stop and quit?"):
                return
            self.is_running = False

        self.cleanup_browser()
        self.root.destroy()

    def run(self):
        """Launch the Tkinter app."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

def main():
    app = YouTubeAnalyzerDemo()
    app.run()

if __name__ == "__main__":
    main()
