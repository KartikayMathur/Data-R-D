import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import threading
import subprocess
import sys
import os
from PIL import Image, ImageTk
import logging
import json
import pandas as pd
from datetime import datetime
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import re
import time
import pyautogui
from PIL import ImageGrab
import win32gui
import win32con

class DependencyManager:
    def __init__(self):
        self.required_packages = [
            'customtkinter',
            'selenium',
            'undetected-chromedriver',
            'pandas',
            'Pillow',
            'requests',
            'beautifulsoup4',
            'openpyxl'
        ]

    def check_and_install_dependencies(self):
        missing_packages = []
        for package in self.required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            self.install_packages(missing_packages)
            return True
        return False

    def install_packages(self, packages):
        for package in packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

class WindowsAutomation:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.setup_directory_structure()

    def setup_directory_structure(self):
        """Creates the necessary folder structure on Windows"""
        folders = [
            "Channel_Data",
            "Video_Screenshots",
            "Channel_Screenshots",
            "Raw_Data",
            "Spreadsheets",
            "Thumbnails"
        ]

        for folder in folders:
            folder_path = os.path.join(self.base_dir, folder)
            os.makedirs(folder_path, exist_ok=True)

        return os.path.join(self.base_dir)

class AdvancedYouTubeAnalyzer:
    def __init__(self):
        self.setup_logging()
        self.driver = None
        self.wait = None
        self.stop_flag = False
        self.output_dir = os.path.join(os.path.expanduser("~"), "Documents", "YouTube_Analysis")
        self.create_directory_structure()

    def setup_logging(self):
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/youtube_analyzer_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler()
            ]
        )

    def setup_driver(self):
        try:
            options = uc.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Add user agent to avoid detection
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = uc.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 20)
            self.driver.set_page_load_timeout(30)
            return True
        except Exception as e:
            logging.error(f"Failed to setup driver: {str(e)}")
            return False

    def search_channels(self, keyword, num_channels):
        self.driver.get(f"https://www.youtube.com/results?search_query={keyword}&sp=CAMSAhAB")
        channels = []
        while len(channels) < num_channels:
            try:
                channel_elements = self.wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "ytd-channel-renderer")
                ))
                for element in channel_elements:
                    if len(channels) >= num_channels:
                        break
                    channel_url = element.find_element(By.CSS_SELECTOR, "a#main-link").get_attribute("href")
                    channels.append(channel_url)
            except Exception as e:
                logging.error(f"Error searching channels: {str(e)}")
                break
            self.driver.execute_script("window.scrollBy(0, 1000)")
            time.sleep(2)
        return channels

    def extract_channel_detailed_data(self):
        """Extract detailed channel information"""
        try:
            channel_data = {
                "name": self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#channel-name")
                )).text,
                "subscribers": self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#subscriber-count")
                )).text,
                "total_videos": "N/A",
                "total_views": "N/A"
            }

            # Try to get total videos and views
            try:
                stats = self.wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "#right-column yt-formatted-string")
                ))
                for stat in stats:
                    text = stat.text.lower()
                    if 'videos' in text:
                        channel_data["total_videos"] = text.split()[0]
                    elif 'views' in text:
                        channel_data["total_views"] = text.split()[0]
            except:
                logging.warning("Could not extract complete channel statistics")

            return channel_data
        except Exception as e:
            logging.error(f"Error extracting channel data: {str(e)}")
            return None

    def analyze_channel(self, channel_url, num_videos):
        try:
            self.driver.get(channel_url)
            channel_data = self.extract_channel_data()
            videos_data = self.extract_videos_data(num_videos)
            return channel_data, videos_data
        except Exception as e:
            logging.error(f"Error analyzing channel: {str(e)}")
            return None, None

    def extract_channel_data(self):
        try:
            channel_name = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#channel-name")
            )).text

            about_tab = self.driver.find_element(By.CSS_SELECTOR, "tp-yt-paper-tab:nth-child(7)")
            about_tab.click()

            subscribers = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#subscriber-count")
            )).text

            creation_date = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#right-column yt-formatted-string:nth-child(2)")
            )).text

            return {
                "channel_name": channel_name,
                "subscribers": subscribers,
                "creation_date": creation_date,
                "url": self.driver.current_url
            }
        except Exception as e:
            logging.error(f"Error extracting channel data: {str(e)}")
            return None

    def navigate_to_video(self, video_url):
        try:
            # Use JavaScript to open in new tab
            self.driver.execute_script(f'window.open("{video_url}", "_blank");')
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Wait for key elements with explicit waits
            self.wait.until(EC.presence_of_element_located((By.ID, "page-manager")))
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-watch-metadata")))
            
            # Scroll to load all content
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)  # Allow time for dynamic content to load
            
            return True
        except Exception as e:
            logging.error(f"Error navigating to video: {str(e)}")
            return False


    def extract_video_data(self, video_element):
        try:
            video_data = {}
            
            # Extract basic info with explicit error handling
            try:
                video_data['title'] = video_element.find_element(By.ID, "video-title").text
                video_data['url'] = video_element.find_element(By.ID, "video-title").get_attribute("href")
                video_data['thumbnail'] = video_element.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
            except Exception as e:
                logging.error(f"Error extracting basic video info: {str(e)}")
                return None

            # Navigate to video
            if not self.navigate_to_video(video_data['url']):
                return None

            # Extract detailed metrics
            try:
                video_data['views'] = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ytd-video-view-count-renderer")
                )).text
                
                video_data['likes'] = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ytd-menu-renderer ytd-toggle-button-renderer:first-child")
                )).text
                
                video_data['upload_date'] = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ytd-video-primary-info-renderer yt-formatted-string.ytd-video-primary-info-renderer:last-child")
                )).text
                
                video_data['comments'] = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ytd-comments-header-renderer h2 yt-formatted-string")
                )).text
            except Exception as e:
                logging.error(f"Error extracting video metrics: {str(e)}")

            # Take screenshot
            screenshot_path = self.capture_screenshot(f"video_{video_data['title'][:30]}")
            video_data['screenshot'] = screenshot_path

            # Download thumbnail
            thumbnail_path = self.download_thumbnail(video_data['thumbnail'], video_data['title'])
            video_data['thumbnail_path'] = thumbnail_path

            # Add advanced metrics
            video_data.update(self.calculate_advanced_metrics(video_data))

            # Close video tab and switch back
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            return video_data

        except Exception as e:
            logging.error(f"Error in extract_video_data: {str(e)}")
            return None


    def extract_single_video_data(self, video_element):
        try:
            title = video_element.find_element(By.ID, "video-title").text
            url = video_element.find_element(By.ID, "video-title").get_attribute("href")
            thumbnail_url = video_element.find_element(By.CSS_SELECTOR, "img").get_attribute("src")

            self.driver.execute_script(f'window.open("{url}", "_blank");')
            self.driver.switch_to.window(self.driver.window_handles[-1])

            views = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ytd-video-view-count-renderer")
            )).text

            likes = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ytd-menu-renderer span")
            )).text

            upload_date = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#info-strings yt-formatted-string")
            )).text

            comments = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ytd-comments-header-renderer h2")
            )).text

            # Download thumbnail
            thumbnail_path = self.download_thumbnail(thumbnail_url, title)

            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            return {
                "title": title,
                "url": url,
                "views": views,
                "likes": likes,
                "upload_date": upload_date,
                "comments": comments,
                "thumbnail_path": thumbnail_path
            }
        except Exception as e:
            logging.error(f"Error extracting single video data: {str(e)}")
            return None

    def calculate_advanced_metrics(self, video_data):
        """Calculate advanced metrics for video analysis"""
        try:
            views = int(re.sub(r'[^\d]', '', video_data['views']))
            likes = int(re.sub(r'[^\d]', '', video_data['likes']))
            comments = int(re.sub(r'[^\d]', '', video_data['comments']))
            
            metrics = {
                'engagement_rate': round((likes + comments) / views * 100, 2),
                'likes_per_view': round(likes / views * 100, 2),
                'comments_per_view': round(comments / views * 100, 2),
                'virality_score': round(np.log10(views) * (likes + comments) / views * 100, 2)
            }
            
            # Add time-based metrics
            upload_date = datetime.strptime(video_data['upload_date'], '%b %d, %Y')
            days_since_upload = (datetime.now() - upload_date).days
            
            metrics['views_per_day'] = round(views / max(days_since_upload, 1), 2)
            metrics['performance_score'] = round(
                (metrics['engagement_rate'] * 0.4) +
                (metrics['virality_score'] * 0.3) +
                (np.log10(metrics['views_per_day']) * 0.3), 2
            )
            
            return metrics
            
        except Exception as e:
            logging.error(f"Error calculating advanced metrics: {str(e)}")
            return {}

    def capture_screenshot(self, filename):
        """Capture full page screenshot with improved reliability"""
        try:
            # Ensure unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.output_dir, 'screenshots', f"{filename}_{timestamp}.png")
            
            # Get page dimensions
            total_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            
            # Create full page screenshot
            full_screenshot = Image.new('RGB', (self.driver.execute_script("return window.innerWidth"), total_height))
            offset = 0
            
            while offset < total_height:
                # Scroll to position
                self.driver.execute_script(f"window.scrollTo(0, {offset})")
                time.sleep(0.5)  # Wait for content to load
                
                # Capture viewport
                screenshot = ImageGrab.grab()
                full_screenshot.paste(screenshot, (0, offset))
                
                offset += viewport_height
            
            # Save screenshot
            full_screenshot.save(filepath)
            return filepath
            
        except Exception as e:
            logging.error(f"Error capturing screenshot: {str(e)}")
            return None

    def download_thumbnail(self, url, title):
        """Download and process video thumbnail"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Create unique filename
                safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = os.path.join(self.output_dir, 'thumbnails', f"{safe_title}_{timestamp}.jpg")
                
                # Save thumbnail
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                # Process thumbnail for quality check
                img = cv2.imread(filepath)
                if img is not None:
                    # Check resolution
                    height, width = img.shape[:2]
                    if width < 1280 or height < 720:
                        logging.warning(f"Low resolution thumbnail for video: {title}")
                    
                    # Enhance thumbnail if needed
                    img = cv2.detailEnhance(img, sigma_s=10, sigma_r=0.15)
                    cv2.imwrite(filepath, img)
                
                return filepath
        except Exception as e:
            logging.error(f"Error downloading thumbnail: {str(e)}")
            return None

class EnhancedYouTubeAnalyzer:
    def __init__(self):
        super().__init__()
        self.output_dir = os.path.join(os.path.expanduser("~"), "Documents", "YouTube_Analysis")
        self.windows_automation = WindowsAutomation(self.output_dir)

    def analyze_popular_videos(self, channel_url, num_videos):
        try:
            # Navigate to channel's videos tab and sort by popularity
            videos_url = f"{channel_url}/videos?view=0&sort=p"
            self.driver.get(videos_url)
            time.sleep(2)  # Wait for page load

            # Get video elements
            video_elements = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "ytd-grid-video-renderer")
            ))[:num_videos]

            videos_data = []
            for index, video in enumerate(video_elements):
                video_data = self.process_single_video(video, index + 1)
                if video_data:
                    videos_data.append(video_data)

            return videos_data

        except Exception as e:
            logging.error(f"Error in analyze_popular_videos: {str(e)}")
            return []

    def process_single_video(self, video_element, video_number):
        try:
            # Get video link
            video_link = video_element.find_element(By.ID, "video-title").get_attribute("href")

            # Right click and open in new tab
            actions = ActionChains(self.driver)
            video_title = video_element.find_element(By.ID, "video-title")
            actions.context_click(video_title).perform()

            # Find and click "Open in new tab" option
            time.sleep(1)  # Wait for context menu
            pyautogui.press('down', presses=3)  # Navigate to "Open in new tab"
            pyautogui.press('enter')

            # Switch to new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])

            # Wait for video page to load
            self.wait.until(EC.presence_of_element_located((By.ID, "page-manager")))

            # Take screenshot of video page
            video_screenshot = self.capture_full_page(f"video_{video_number}")

            # Extract video data
            video_data = self.extract_video_detailed_data()

            # Navigate to channel about page
            channel_link = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#channel-name a")
            )).get_attribute("href")

            self.driver.get(f"{channel_link}/about")
            time.sleep(2)

            # Take screenshot of about page
            about_screenshot = self.capture_full_page(f"channel_{video_number}")

            # Extract channel data
            channel_data = self.extract_channel_detailed_data()

            # Combine data
            combined_data = {
                "video_title": video_data["title"],
                "video_url": video_link,
                "video_views": video_data["views"],
                "video_likes": video_data["likes"],
                "video_comments": video_data["comments"],
                "video_upload_date": video_data["upload_date"],
                "channel_name": channel_data["name"],
                "channel_subscribers": channel_data["subscribers"],
                "channel_total_videos": channel_data["total_videos"],
                "channel_total_views": channel_data["total_views"],
                "video_screenshot_path": video_screenshot,
                "channel_screenshot_path": about_screenshot
            }

            # Save raw data to text file
            self.save_raw_data(combined_data, video_number)

            # Close current tab and switch back
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            return combined_data

        except Exception as e:
            logging.error(f"Error processing video {video_number}: {str(e)}")
            return None

    def capture_full_page(self, filename):
        """Captures full page screenshot using PIL"""
        try:
            # Get page dimensions
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            window_height = self.driver.execute_script("return window.innerHeight")

            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Prepare screenshot path
            screenshot_path = os.path.join(
                self.output_dir,
                "Video_Screenshots" if "video" in filename else "Channel_Screenshots",
                f"{filename}_{timestamp}.png"
            )

            # Take screenshots while scrolling
            offset = 0
            screenshots = []
            while offset < total_height:
                self.driver.execute_script(f"window.scrollTo(0, {offset});")
                time.sleep(0.5)  # Wait for elements to load

                screenshot = ImageGrab.grab()
                screenshots.append(screenshot)

                offset += window_height

            # Combine screenshots
            total_width = screenshots[0].width
            combined_screenshot = Image.new('RGB', (total_width, total_height))

            current_height = 0
            for screenshot in screenshots:
                combined_screenshot.paste(screenshot, (0, current_height))
                current_height += screenshot.height

            # Save combined screenshot
            combined_screenshot.save(screenshot_path)
            return screenshot_path

        except Exception as e:
            logging.error(f"Error capturing screenshot: {str(e)}")
            return None

    def save_raw_data(self, data, video_number):
        """Saves raw data to text file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"video_{video_number}_data_{timestamp}.txt"
            filepath = os.path.join(self.output_dir, "Raw_Data", filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                for key, value in data.items():
                    f.write(f"{key}: {value}\n")

            return filepath

        except Exception as e:
            logging.error(f"Error saving raw data: {str(e)}")
            return None

    def create_excel_report(self, all_data):
        """Creates comprehensive Excel report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_path = os.path.join(self.output_dir, "Spreadsheets", f"analysis_report_{timestamp}.xlsx")

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Channel Data Sheet
                channel_data = []
                for video_data in all_data:
                    channel_data.append({
                        "Channel Name": video_data["channel_name"],
                        "Subscribers": video_data["channel_subscribers"],
                        "Total Videos": video_data["channel_total_videos"],
                        "Total Views": video_data["channel_total_views"]
                    })
                pd.DataFrame(channel_data).drop_duplicates().to_excel(
                    writer, sheet_name='Channel Data', index=False
                )

                # Video Data Sheet
                video_data = [{
                    "Video Title": d["video_title"],
                    "Views": d["video_views"],
                    "Likes": d["video_likes"],
                    "Comments": d["video_comments"],
                    "Upload Date": d["video_upload_date"],
                    "Video URL": d["video_url"],
                    "Video Screenshot": d["video_screenshot_path"],
                    "Channel Screenshot": d["channel_screenshot_path"]
                } for d in all_data]
                pd.DataFrame(video_data).to_excel(
                    writer, sheet_name='Video Data', index=False
                )

            return excel_path

        except Exception as e:
            logging.error(f"Error creating Excel report: {str(e)}")
            return None


class AnalyzerGUI:
    def __init__(self):
        self.analyzer = EnhancedYouTubeAnalyzer()
        self.root = ctk.CTk()
        self.root.title("YouTube Channel Analyzer")
        self.setup_gui()
        self.dependency_manager = DependencyManager()

    def setup_gui(self):
        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # Search frame
        search_frame = ctk.CTkFrame(self.root)
        search_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Dependency checker
        self.dep_var = tk.BooleanVar(value=False)
        dep_check = ctk.CTkCheckBox(search_frame, text="Check Dependencies", variable=self.dep_var)
        dep_check.grid(row=0, column=0, padx=5, pady=5)

        # Inputs
        ctk.CTkLabel(search_frame, text="Search Keyword:").grid(row=1, column=0, padx=5, pady=5)
        self.keyword_entry = ctk.CTkEntry(search_frame)
        self.keyword_entry.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(search_frame, text="Number of Channels:").grid(row=2, column=0, padx=5, pady=5)
        self.channels_entry = ctk.CTkEntry(search_frame)
        self.channels_entry.grid(row=2, column=1, padx=5, pady=5)

        ctk.CTkLabel(search_frame, text="Videos per Channel:").grid(row=3, column=0, padx=5, pady=5)
        self.videos_entry = ctk.CTkEntry(search_frame)
        self.videos_entry.grid(row=3, column=1, padx=5, pady=5)

        # Output directory selection
        ctk.CTkButton(search_frame, text="Select Output Directory",
                     command=self.select_output_dir).grid(row=4, column=0, columnspan=2, pady=10)

        # Start and Stop buttons
        self.start_button = ctk.CTkButton(search_frame, text="Start Analysis", command=self.start_analysis)
        self.start_button.grid(row=5, column=0, pady=10)

        self.stop_button = ctk.CTkButton(search_frame, text="Stop", command=self.stop_analysis)
        self.stop_button.grid(row=5, column=1, pady=10)

        # Progress frame
        progress_frame = ctk.CTkFrame(self.root)
        progress_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.status_text = tk.Text(progress_frame, height=10, width=40)
        self.status_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Thumbnail preview
        self.preview_label = ctk.CTkLabel(progress_frame, text="")
        self.preview_label.grid(row=2, column=0, padx=5, pady=5)

    def select_output_dir(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.analyzer.output_dir = dir_path
            self.update_status(f"Output directory set to: {dir_path}")

    def start_analysis(self):
        if self.dep_var.get():
            self.dependency_manager.check_and_install_dependencies()

        keyword = self.keyword_entry.get()
        num_channels = int(self.channels_entry.get())
        num_videos = int(self.videos_entry.get())

        self.analysis_thread = threading.Thread(
            target=self.run_analysis,
            args=(keyword, num_channels, num_videos)
        )
        self.analysis_thread.start()

    def stop_analysis(self):
        if hasattr(self, 'analysis_thread') and self.analysis_thread.is_alive():
            self.analyzer.driver.quit()
            self.analysis_thread.join()
            self.update_status("Analysis stopped by user")

    def run_analysis(self, keyword, num_channels, num_videos):
        try:
            self.analyzer.setup_driver()
            self.update_status("Searching for channels...")

            channels = self.analyzer.search_channels(keyword, num_channels)
            self.progress_bar["maximum"] = len(channels)

            all_data = []
            for i, channel_url in enumerate(channels):
                self.update_status(f"Analyzing channel {i+1}/{len(channels)}")
                channel_data, videos_data = self.analyzer.analyze_channel(channel_url, num_videos)

                if channel_data and videos_data:
                    all_data.append({
                        "channel": channel_data,
                        "videos": videos_data
                    })

                self.progress_bar["value"] = i + 1
                self.root.update()

            self.save_results(all_data)
            self.update_status("Analysis completed!")

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
        finally:
            if self.analyzer.driver:
                self.analyzer.driver.quit()

    def save_results(self, all_data):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_path = os.path.join(self.analyzer.output_dir, f'analysis_results_{timestamp}.xlsx')

        # Create Excel writer
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Channel overview sheet
            channel_overview = []
            for data in all_data:
                channel = data["channel"]
                videos = data["videos"]
                channel_overview.append({
                    "Channel Name": channel["channel_name"],
                    "Subscribers": channel["subscribers"],
                    "Creation Date": channel["creation_date"],
                    "URL": channel["url"],
                    "Total Videos Analyzed": len(videos),
                    "Average Views": sum(int(re.sub(r'[^\d]', '', v["views"])) for v in videos) / len(videos)
                })

            pd.DataFrame(channel_overview).to_excel(writer, sheet_name='Channel Overview', index=False)

            # Video details sheet
            video_details = []
            for data in all_data:
                channel = data["channel"]
                for video in data["videos"]:
                    video_details.append({
                        "Channel Name": channel["channel_name"],
                        "Video Title": video["title"],
                        "Views": video["views"],
                        "Likes": video["likes"],
                        "Comments": video["comments"],
                        "Upload Date": video["upload_date"],
                        "Video URL": video["url"],
                        "Thumbnail Path": video["thumbnail_path"]
                    })

            pd.DataFrame(video_details).to_excel(writer, sheet_name='Video Details', index=False)

    def update_status(self, message):
        self.status_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.status_text.see(tk.END)
        self.root.update()

    def update_preview(self, image_path):
        try:
            image = Image.open(image_path)
            image.thumbnail((200, 200))
            photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=photo)
            self.preview_label.image = photo
        except Exception as e:
            logging.error(f"Error updating preview: {str(e)}")

    def run(self):
        self.root.mainloop()

# Advanced Features

class AdvancedAnalytics:
    @staticmethod
    def calculate_engagement_rate(views, likes, comments):
        try:
            views = int(re.sub(r'[^\d]', '', views))
            likes = int(re.sub(r'[^\d]', '', likes))
            comments = int(re.sub(r'[^\d]', '', comments))
            return ((likes + comments) / views) * 100
        except:
            return 0

    @staticmethod
    def calculate_growth_rate(videos_data):
        try:
            # Sort videos by upload date
            sorted_videos = sorted(videos_data, key=lambda x: datetime.strptime(x['upload_date'], '%b %d, %Y'))

            # Calculate views growth rate
            view_counts = [int(re.sub(r'[^\d]', '', v['views'])) for v in sorted_videos]
            growth_rates = []

            for i in range(1, len(view_counts)):
                rate = ((view_counts[i] - view_counts[i-1]) / view_counts[i-1]) * 100
                growth_rates.append(rate)

            return sum(growth_rates) / len(growth_rates) if growth_rates else 0
        except:
            return 0

    @staticmethod
    def analyze_upload_frequency(videos_data):
        try:
            # Sort videos by upload date
            sorted_videos = sorted(videos_data, key=lambda x: datetime.strptime(x['upload_date'], '%b %d, %Y'))

            # Calculate days between uploads
            upload_dates = [datetime.strptime(v['upload_date'], '%b %d, %Y') for v in sorted_videos]
            days_between = []

            for i in range(1, len(upload_dates)):
                delta = (upload_dates[i] - upload_dates[i-1]).days
                days_between.append(delta)

            return sum(days_between) / len(days_between) if days_between else 0
        except:
            return 0

    @staticmethod
    def get_best_performing_time(videos_data):
        try:
            # Create dictionary to store performance by hour
            hour_performance = {}

            for video in videos_data:
                upload_date = datetime.strptime(video['upload_date'], '%b %d, %Y')
                hour = upload_date.hour
                views = int(re.sub(r'[^\d]', '', video['views']))

                if hour in hour_performance:
                    hour_performance[hour].append(views)
                else:
                    hour_performance[hour] = [views]

            # Calculate average views per hour
            hour_averages = {
                hour: sum(views) / len(views)
                for hour, views in hour_performance.items()
            }

            # Find best performing hour
            best_hour = max(hour_averages.items(), key=lambda x: x[1])
            return best_hour[0]
        except:
            return None

class EnhancedYouTubeAnalyzer(AdvancedYouTubeAnalyzer):
    def __init__(self):
        super().__init__()
        self.output_dir = os.path.join(os.path.expanduser("~"), "Documents", "YouTube_Analysis")
        self.windows_automation = WindowsAutomation(self.output_dir)
        self.create_directory_structure()  # Ensure the directory structure is created

    def analyze_popular_videos(self, channel_url, num_videos):
        try:
            # Navigate to channel's videos tab and sort by popularity
            videos_url = f"{channel_url}/videos?view=0&sort=p"
            self.driver.get(videos_url)
            time.sleep(2)  # Wait for page load

            # Get video elements
            video_elements = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "ytd-grid-video-renderer")
            ))[:num_videos]

            videos_data = []
            for index, video in enumerate(video_elements):
                video_data = self.process_single_video(video, index + 1)
                if video_data:
                    videos_data.append(video_data)

            return videos_data

        except Exception as e:
            logging.error(f"Error in analyze_popular_videos: {str(e)}")
            return []

    def process_single_video(self, video_element, video_number):
        try:
            # Get video link
            video_link = video_element.find_element(By.ID, "video-title").get_attribute("href")

            # Right click and open in new tab
            actions = ActionChains(self.driver)
            video_title = video_element.find_element(By.ID, "video-title")
            actions.context_click(video_title).perform()

            # Find and click "Open in new tab" option
            time.sleep(1)  # Wait for context menu
            pyautogui.press('down', presses=3)  # Navigate to "Open in new tab"
            pyautogui.press('enter')

            # Switch to new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])

            # Wait for video page to load
            self.wait.until(EC.presence_of_element_located((By.ID, "page-manager")))

            # Take screenshot of video page
            video_screenshot = self.capture_full_page(f"video_{video_number}")

            # Extract video data
            video_data = self.extract_video_detailed_data()

            # Navigate to channel about page
            channel_link = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#channel-name a")
            )).get_attribute("href")

            self.driver.get(f"{channel_link}/about")
            time.sleep(2)

            # Take screenshot of about page
            about_screenshot = self.capture_full_page(f"channel_{video_number}")

            # Extract channel data
            channel_data = self.extract_channel_detailed_data()

            # Combine data
            combined_data = {
                "video_title": video_data["title"],
                "video_url": video_link,
                "video_views": video_data["views"],
                "video_likes": video_data["likes"],
                "video_comments": video_data["comments"],
                "video_upload_date": video_data["upload_date"],
                "channel_name": channel_data["name"],
                "channel_subscribers": channel_data["subscribers"],
                "channel_total_videos": channel_data["total_videos"],
                "channel_total_views": channel_data["total_views"],
                "video_screenshot_path": video_screenshot,
                "channel_screenshot_path": about_screenshot
            }

            # Save raw data to text file
            self.save_raw_data(combined_data, video_number)

            # Close current tab and switch back
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            return combined_data

        except Exception as e:
            logging.error(f"Error processing video {video_number}: {str(e)}")
            return None

    def capture_full_page(self, filename):
        """Captures full page screenshot using PIL"""
        try:
            # Get page dimensions
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            window_height = self.driver.execute_script("return window.innerHeight")

            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Prepare screenshot path
            screenshot_path = os.path.join(
                self.output_dir,
                "Video_Screenshots" if "video" in filename else "Channel_Screenshots",
                f"{filename}_{timestamp}.png"
            )

            # Take screenshots while scrolling
            offset = 0
            screenshots = []
            while offset < total_height:
                self.driver.execute_script(f"window.scrollTo(0, {offset});")
                time.sleep(0.5)  # Wait for elements to load

                screenshot = ImageGrab.grab()
                screenshots.append(screenshot)

                offset += window_height

            # Combine screenshots
            total_width = screenshots[0].width
            combined_screenshot = Image.new('RGB', (total_width, total_height))

            current_height = 0
            for screenshot in screenshots:
                combined_screenshot.paste(screenshot, (0, current_height))
                current_height += screenshot.height

            # Save combined screenshot
            combined_screenshot.save(screenshot_path)
            return screenshot_path

        except Exception as e:
            logging.error(f"Error capturing screenshot: {str(e)}")
            return None

    def save_raw_data(self, data, video_number):
        """Saves raw data to text file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"video_{video_number}_data_{timestamp}.txt"
            filepath = os.path.join(self.output_dir, "Raw_Data", filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                for key, value in data.items():
                    f.write(f"{key}: {value}\n")

            return filepath

        except Exception as e:
            logging.error(f"Error saving raw data: {str(e)}")
            return None

    def create_excel_report(self, all_data):
        """Creates comprehensive Excel report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_path = os.path.join(self.output_dir, "Spreadsheets", f"analysis_report_{timestamp}.xlsx")

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Channel Data Sheet
                channel_data = []
                for video_data in all_data:
                    channel_data.append({
                        "Channel Name": video_data["channel_name"],
                        "Subscribers": video_data["channel_subscribers"],
                        "Total Videos": video_data["channel_total_videos"],
                        "Total Views": video_data["channel_total_views"]
                    })
                pd.DataFrame(channel_data).drop_duplicates().to_excel(
                    writer, sheet_name='Channel Data', index=False
                )

                # Video Data Sheet
                video_data = [{
                    "Video Title": d["video_title"],
                    "Views": d["video_views"],
                    "Likes": d["video_likes"],
                    "Comments": d["video_comments"],
                    "Upload Date": d["video_upload_date"],
                    "Video URL": d["video_url"],
                    "Video Screenshot": d["video_screenshot_path"],
                    "Channel Screenshot": d["channel_screenshot_path"]
                } for d in all_data]
                pd.DataFrame(video_data).to_excel(
                    writer, sheet_name='Video Data', index=False
                )

            return excel_path

        except Exception as e:
            logging.error(f"Error creating Excel report: {str(e)}")
            return None


def main():
    # Initialize dependency manager and check dependencies
    dep_manager = DependencyManager()
    dep_manager.check_and_install_dependencies()

    # Create and run GUI
    app = AnalyzerGUI()
    app.run()

if __name__ == "__main__":
    main()
