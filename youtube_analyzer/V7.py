import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import threading
import subprocess
import sys
import os
from PIL import Image, ImageTk, ImageGrab
import logging
import json
import pandas as pd
from datetime import datetime
import requests
import re
import time
import pyautogui
import win32gui
import win32con

# Selenium / Chrome-Driver related imports
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Numpy and OpenCV for advanced/optional image operations
import numpy as np
import cv2


class DependencyManager:
    def __init__(self):
        # Added numpy and opencv-python to handle advanced metrics + image ops
        self.required_packages = [
            'customtkinter',
            'selenium',
            'undetected-chromedriver',
            'pandas',
            'Pillow',
            'requests',
            'beautifulsoup4',
            'openpyxl',
            'numpy',
            'opencv-python'
        ]

    def check_and_install_dependencies(self):
        """
        Checks for required packages. If any are missing, they are installed automatically.
        """
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
        """
        Installs missing packages using pip.
        """
        for package in packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])


class WindowsAutomation:
    """
    This class handles the creation of the necessary directories on Windows.
    """
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.setup_directory_structure()

    def setup_directory_structure(self):
        """
        Creates the folder structure:
         - Channel_Data
         - Video_Screenshots
         - Channel_Screenshots
         - Raw_Data
         - Spreadsheets
         - Thumbnails
        """
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
    """
    Core functionality for analyzing YouTube channels and their videos.
    This class can:
      - Set up the Selenium driver (undetected Chrome).
      - Search for channels by keyword.
      - Extract channel-level data.
      - Extract video-level data.
      - Navigate between videos, capturing screenshots, etc.
    """
    def __init__(self):
        self.setup_logging()
        self.driver = None
        self.wait = None
        self.stop_flag = False
        # Default output directory
        self.output_dir = os.path.join(os.path.expanduser("~"), "Documents", "YouTube_Analysis")
        self.create_directory_structure()

    def setup_logging(self):
        """
        Sets up logging to file and console.
        """
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/youtube_analyzer_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler()
            ]
        )

    def create_directory_structure(self):
        """
        Ensures the main output directory exists.
        """
        os.makedirs(self.output_dir, exist_ok=True)

    def setup_driver(self):
        """
        Sets up the undetected Chrome driver in maximized mode, with various
        performance and anti-detection settings.
        """
        try:
            options = uc.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # Add a user agent to reduce detection likelihood
            options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            self.driver = uc.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 20)
            self.driver.set_page_load_timeout(30)
            return True
        except Exception as e:
            logging.error(f"Failed to setup driver: {str(e)}")
            return False

    def search_channels(self, keyword, num_channels):
        """
        Searches YouTube by keyword, aiming to gather channel links.
        Returns up to num_channels channel URLs.
        """
        self.driver.get(f"https://www.youtube.com/results?search_query={keyword}&sp=CAMSAhAB")
        channels = []
        while len(channels) < num_channels and not self.stop_flag:
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
            # Scroll to load more results
            self.driver.execute_script("window.scrollBy(0, 1000)")
            time.sleep(2)
        return channels

    def extract_channel_data(self):
        """
        Extracts some basic data from the channel's main page (Name, subscribers, creation date, etc.).
        """
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
        """
        Opens a new browser tab for the given video URL and waits for the page to load.
        """
        try:
            self.driver.execute_script(f'window.open("{video_url}", "_blank");')
            self.driver.switch_to.window(self.driver.window_handles[-1])

            self.wait.until(EC.presence_of_element_located((By.ID, "page-manager")))
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-watch-metadata")))

            # Scroll to ensure data loads
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)
            return True
        except Exception as e:
            logging.error(f"Error navigating to video: {str(e)}")
            return False

    def extract_video_data(self, video_element):
        """
        Extracts data from a single video element in the channel's "Videos" section.
        This includes title, URL, thumbnail, likes, views, comments, etc.
        """
        try:
            video_data = {}
            # Basic info
            video_data['title'] = video_element.find_element(By.ID, "video-title").text
            video_data['url'] = video_element.find_element(By.ID, "video-title").get_attribute("href")
            video_data['thumbnail'] = video_element.find_element(By.CSS_SELECTOR, "img").get_attribute("src")

            # Navigate to the video in a new tab
            if not self.navigate_to_video(video_data['url']):
                return None

            # Detailed metrics
            try:
                video_data['views'] = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ytd-video-view-count-renderer")
                )).text

                video_data['likes'] = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ytd-menu-renderer ytd-toggle-button-renderer:first-child")
                )).text

                video_data['upload_date'] = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ytd-video-primary-info-renderer "
                                      "yt-formatted-string.ytd-video-primary-info-renderer:last-child")
                )).text

                video_data['comments'] = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ytd-comments-header-renderer h2 yt-formatted-string")
                )).text

            except Exception as e:
                logging.error(f"Error extracting video metrics: {str(e)}")

            # Screenshot the video page
            screenshot_path = self.capture_screenshot(f"video_{video_data['title'][:30]}")
            video_data['screenshot'] = screenshot_path

            # Download the thumbnail
            thumbnail_path = self.download_thumbnail(video_data['thumbnail'], video_data['title'])
            video_data['thumbnail_path'] = thumbnail_path

            # Calculate advanced metrics
            video_data.update(self.calculate_advanced_metrics(video_data))

            # Close the video tab
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            return video_data

        except Exception as e:
            logging.error(f"Error in extract_video_data: {str(e)}")
            return None

    def calculate_advanced_metrics(self, video_data):
        """
        Examples of advanced metrics: engagement rate, likes per view, etc.
        """
        try:
            views = int(re.sub(r'[^\d]', '', video_data['views']))
            likes = int(re.sub(r'[^\d]', '', video_data['likes']))
            comments = int(re.sub(r'[^\d]', '', video_data['comments']))

            metrics = {
                'engagement_rate': round((likes + comments) / max(views, 1) * 100, 2),
                'likes_per_view': round(likes / max(views, 1) * 100, 2),
                'comments_per_view': round(comments / max(views, 1) * 100, 2),
            }

            # Example "virality" metric
            try:
                virality_score = round(np.log10(views) * (likes + comments) / max(views, 1) * 100, 2)
            except ValueError:
                virality_score = 0
            metrics['virality_score'] = virality_score

            # Attempt to parse upload date for time-based metrics
            try:
                upload_date_parsed = datetime.strptime(video_data['upload_date'], '%b %d, %Y')
                days_since_upload = (datetime.now() - upload_date_parsed).days
                metrics['views_per_day'] = round(views / max(days_since_upload, 1), 2)
            except:
                metrics['views_per_day'] = 0

            return metrics
        except Exception as e:
            logging.error(f"Error calculating advanced metrics: {str(e)}")
            return {}

    def capture_screenshot(self, filename):
        """
        Captures a full-page screenshot by scrolling.
        This uses PIL's ImageGrab on Windows.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = re.sub(r'[\\/*?:"<>|]', "", filename)
            filepath = os.path.join(self.output_dir, 'Video_Screenshots', f"{file_name}_{timestamp}.png")
            os.makedirs(os.path.join(self.output_dir, 'Video_Screenshots'), exist_ok=True)

            total_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            window_width = self.driver.execute_script("return window.innerWidth")

            # Create a new image to stitch screenshots
            full_screenshot = Image.new('RGB', (window_width, total_height))
            offset = 0

            while offset < total_height:
                self.driver.execute_script(f"window.scrollTo(0, {offset})")
                time.sleep(0.5)  # allow page to render
                screenshot = ImageGrab.grab()  # captures entire screen
                full_screenshot.paste(screenshot, (0, offset))
                offset += viewport_height

            full_screenshot.save(filepath)
            return filepath

        except Exception as e:
            logging.error(f"Error capturing screenshot: {str(e)}")
            return None

    def download_thumbnail(self, url, title):
        """
        Downloads the thumbnail from the given URL and optionally enhances it with OpenCV.
        """
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = os.path.join(self.output_dir, 'Thumbnails', f"{safe_title}_{timestamp}.jpg")
                os.makedirs(os.path.join(self.output_dir, 'Thumbnails'), exist_ok=True)

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                # Check and enhance thumbnail if needed
                img = cv2.imread(filepath)
                if img is not None:
                    height, width = img.shape[:2]
                    if width < 1280 or height < 720:
                        logging.warning(f"Low resolution thumbnail for video: {title}")

                    # Optional example: apply detail enhancement
                    img = cv2.detailEnhance(img, sigma_s=10, sigma_r=0.15)
                    cv2.imwrite(filepath, img)

                return filepath
        except Exception as e:
            logging.error(f"Error downloading thumbnail: {str(e)}")
        return None

    def analyze_channel(self, channel_url, num_videos):
        """
        Orchestrates the channel analysis:
          1. Go to channel main page, extract data.
          2. Navigate to Videos → popular sorting
          3. Grab the specified number of videos.
          4. Return both channel data and videos data.
        """
        try:
            self.driver.get(channel_url)
            channel_data = self.extract_channel_data()

            # Construct "Videos" URL + sort by popularity (sort=p)
            videos_url = f"{channel_url}/videos?view=0&sort=p"
            self.driver.get(videos_url)
            time.sleep(2)

            # Gather the top N video elements
            video_elements = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "ytd-grid-video-renderer")
            ))[:num_videos]

            videos_data = []
            for video_element in video_elements:
                video_data = self.extract_video_data(video_element)
                if video_data:
                    videos_data.append(video_data)

            return channel_data, videos_data

        except Exception as e:
            logging.error(f"Error analyzing channel: {str(e)}")
            return None, []


class EnhancedYouTubeAnalyzer(AdvancedYouTubeAnalyzer):
    """
    Extends AdvancedYouTubeAnalyzer with "right-click → open in new tab" steps
    and capturing screenshots of both the video page and channel "About" page.
    Also saves raw data to text files before combining into an Excel sheet.
    """
    def __init__(self):
        super().__init__()
        self.windows_automation = WindowsAutomation(self.output_dir)
        self.create_directory_structure()  # Ensure directories exist

    def create_directory_structure(self):
        """
        Create the main YouTube_Analysis directory structure.
        """
        os.makedirs(self.output_dir, exist_ok=True)

    def analyze_popular_videos(self, channel_url, num_videos):
        """
        Directly navigates to the channel's "Videos" page sorted by popularity
        and processes each video by right-click → open new tab approach.
        """
        try:
            videos_url = f"{channel_url}/videos?view=0&sort=p"
            self.driver.get(videos_url)
            time.sleep(2)

            video_elements = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "ytd-grid-video-renderer")
            ))[:num_videos]

            videos_data = []
            for index, video_element in enumerate(video_elements, start=1):
                vid_data = self.process_single_video(video_element, index)
                if vid_data:
                    videos_data.append(vid_data)

            return videos_data
        except Exception as e:
            logging.error(f"Error in analyze_popular_videos: {str(e)}")
            return []

    def process_single_video(self, video_element, video_number):
        """
        Implements the "right-click → open in new tab" approach, then
        captures screenshots of both the video page and the channel's 'About' page.
        """
        try:
            video_title_el = video_element.find_element(By.ID, "video-title")
            video_link = video_title_el.get_attribute("href")

            # Right-click and open in new tab via pyautogui
            actions = ActionChains(self.driver)
            actions.context_click(video_title_el).perform()
            time.sleep(1)

            # "Open in new tab" is typically a few 'down' presses, then 'enter'
            pyautogui.press('down', presses=3)
            pyautogui.press('enter')

            # Switch to new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.wait.until(EC.presence_of_element_located((By.ID, "page-manager")))

            # Screenshot of video page
            video_screenshot = self.capture_full_page(f"video_{video_number}")

            # Extract video data
            video_data = self.extract_video_detailed_data()

            # Navigate to channel About page
            channel_link = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#channel-name a")
            )).get_attribute("href")
            self.driver.get(f"{channel_link}/about")
            time.sleep(2)

            # Screenshot of About page
            about_screenshot = self.capture_full_page(f"channel_{video_number}")

            # Extract channel data
            channel_data = self.extract_channel_detailed_data()

            # Combine
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

            # Save raw data to a text file
            self.save_raw_data(combined_data, video_number)

            # Close the current tab and switch back
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            return combined_data
        except Exception as e:
            logging.error(f"Error processing video {video_number}: {str(e)}")
            return None

    def capture_full_page(self, filename):
        """
        Scroll-captures the entire page using multiple screenshots and stitches them together.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sanitized_name = re.sub(r'[\\/*?:"<>|]', "", filename)
            if "video" in filename.lower():
                folder = "Video_Screenshots"
            else:
                folder = "Channel_Screenshots"

            screenshot_path = os.path.join(
                self.output_dir, folder, f"{sanitized_name}_{timestamp}.png"
            )
            os.makedirs(os.path.join(self.output_dir, folder), exist_ok=True)

            total_height = self.driver.execute_script("return document.body.scrollHeight")
            window_height = self.driver.execute_script("return window.innerHeight")
            total_width = self.driver.execute_script("return window.innerWidth")

            offset = 0
            screenshots = []

            while offset < total_height:
                self.driver.execute_script(f"window.scrollTo(0, {offset});")
                time.sleep(0.5)
                img = ImageGrab.grab()
                screenshots.append(img)
                offset += window_height

            combined_screenshot = Image.new('RGB', (total_width, total_height))
            current_height = 0

            for sc in screenshots:
                combined_screenshot.paste(sc, (0, current_height))
                current_height += sc.height

            combined_screenshot.save(screenshot_path)
            return screenshot_path
        except Exception as e:
            logging.error(f"Error capturing screenshot: {str(e)}")
            return None

    def extract_video_detailed_data(self):
        """
        Extracts video metrics from the currently open video page.
        """
        data = {}
        try:
            # Title
            data["title"] = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title.ytd-watch-metadata"))
            ).text.strip()

            # Views
            view_count_el = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-video-view-count-renderer span"))
            )
            data["views"] = view_count_el.text.strip()

            # Likes
            # In some YouTube layouts, likes might be hidden behind new structures.
            # This is an attempt to retrieve it from the toggle button.
            try:
                like_button = self.driver.find_elements(
                    By.CSS_SELECTOR, "ytd-toggle-button-renderer.ytd-menu-renderer"
                )
                data["likes"] = like_button[0].text.strip() if like_button else "0"
            except:
                data["likes"] = "0"

            # Comments
            try:
                comments_el = self.driver.find_element(By.CSS_SELECTOR, "ytd-comments-header-renderer #count")
                data["comments"] = comments_el.text.strip()
            except:
                data["comments"] = "0"

            # Upload date
            try:
                date_el = self.driver.find_element(
                    By.CSS_SELECTOR, "div#info-strings yt-formatted-string"
                )
                data["upload_date"] = date_el.text.strip()
            except:
                data["upload_date"] = "Unknown"

            return data
        except Exception as e:
            logging.error(f"Error extracting detailed video data: {str(e)}")
            return data

    def extract_channel_detailed_data(self):
        """
        Extracts details from the channel's "About" page (e.g., total videos, total views, etc.).
        """
        try:
            channel_data = {
                "name": "Unknown",
                "subscribers": "Unknown",
                "total_videos": "Unknown",
                "total_views": "Unknown"
            }

            # Channel name
            try:
                name_el = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#channel-name")))
                channel_data["name"] = name_el.text.strip()
            except:
                pass

            # Subscriber count
            try:
                subs_el = self.driver.find_element(By.CSS_SELECTOR, "#subscriber-count")
                channel_data["subscribers"] = subs_el.text.strip()
            except:
                pass

            # "Stats" appear on the right-hand side under "#right-column yt-formatted-string"
            try:
                stats = self.driver.find_elements(By.CSS_SELECTOR, "#right-column yt-formatted-string")
                for stat in stats:
                    text = stat.text.lower()
                    if "videos" in text:
                        channel_data["total_videos"] = text.split()[0]
                    elif "views" in text:
                        channel_data["total_views"] = text.split()[0]
            except:
                pass

            return channel_data
        except Exception as e:
            logging.error(f"Error extracting channel detailed data: {str(e)}")
            return {}

    def save_raw_data(self, data, video_number):
        """
        Saves the combined data for each video to a text file.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"video_{video_number}_data_{timestamp}.txt"
            filepath = os.path.join(self.output_dir, "Raw_Data", filename)
            os.makedirs(os.path.join(self.output_dir, "Raw_Data"), exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                for k, v in data.items():
                    f.write(f"{k}: {v}\n")

            return filepath
        except Exception as e:
            logging.error(f"Error saving raw data: {str(e)}")
            return None

    def create_excel_report(self, all_data):
        """
        Creates an Excel spreadsheet with:
          1. Channel Data
          2. Video Data
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_path = os.path.join(self.output_dir, "Spreadsheets", f"analysis_report_{timestamp}.xlsx")
            os.makedirs(os.path.join(self.output_dir, "Spreadsheets"), exist_ok=True)

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Channel Data Sheet
                channel_data_list = []
                for video_data in all_data:
                    channel_data_list.append({
                        "Channel Name": video_data["channel_name"],
                        "Subscribers": video_data["channel_subscribers"],
                        "Total Videos": video_data["channel_total_videos"],
                        "Total Views": video_data["channel_total_views"]
                    })
                df_channel = pd.DataFrame(channel_data_list).drop_duplicates()
                df_channel.to_excel(writer, sheet_name='Channel Data', index=False)

                # Video Data Sheet
                video_data_list = []
                for d in all_data:
                    video_data_list.append({
                        "Video Title": d["video_title"],
                        "Views": d["video_views"],
                        "Likes": d["video_likes"],
                        "Comments": d["video_comments"],
                        "Upload Date": d["video_upload_date"],
                        "Video URL": d["video_url"],
                        "Video Screenshot": d["video_screenshot_path"],
                        "Channel Screenshot": d["channel_screenshot_path"]
                    })
                df_video = pd.DataFrame(video_data_list)
                df_video.to_excel(writer, sheet_name='Video Data', index=False)

            return excel_path
        except Exception as e:
            logging.error(f"Error creating Excel report: {str(e)}")
            return None


class AnalyzerGUI:
    """
    The GUI that integrates with the EnhancedYouTubeAnalyzer. It allows:
      - Dependency check/installation
      - Input fields for keyword, channel count, videos count
      - Output directory selection
      - Start and stop analysis
      - Progress bar, status text, and thumbnail preview
    """
    def __init__(self):
        self.analyzer = EnhancedYouTubeAnalyzer()
        self.root = ctk.CTk()
        self.root.title("YouTube Channel Analyzer")

        # Dependency manager
        self.dependency_manager = DependencyManager()

        self.setup_gui()

    def setup_gui(self):
        """
        Builds out all GUI elements and places them in the app window.
        """
        # Make the window resizable
        self.root.geometry("900x500")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # ==== Left Frame: Search/Settings ====
        search_frame = ctk.CTkFrame(self.root)
        search_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Dependency checker
        self.dep_var = tk.BooleanVar(value=False)
        dep_check = ctk.CTkCheckBox(
            search_frame, text="Check/Install Dependencies?", variable=self.dep_var
        )
        dep_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Keyword input
        ctk.CTkLabel(search_frame, text="Search Keyword:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.keyword_entry = ctk.CTkEntry(search_frame)
        self.keyword_entry.grid(row=1, column=1, padx=5, pady=5)

        # Number of channels
        ctk.CTkLabel(search_frame, text="Number of Channels:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.channels_entry = ctk.CTkEntry(search_frame)
        self.channels_entry.grid(row=2, column=1, padx=5, pady=5)

        # Number of videos per channel
        ctk.CTkLabel(search_frame, text="Videos per Channel:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.videos_entry = ctk.CTkEntry(search_frame)
        self.videos_entry.grid(row=3, column=1, padx=5, pady=5)

        # Output directory selector
        dir_button = ctk.CTkButton(
            search_frame, text="Select Output Directory", command=self.select_output_dir
        )
        dir_button.grid(row=4, column=0, columnspan=2, pady=10)

        # Start/Stop buttons
        self.start_button = ctk.CTkButton(search_frame, text="Start Analysis", command=self.start_analysis)
        self.start_button.grid(row=5, column=0, pady=10)

        self.stop_button = ctk.CTkButton(search_frame, text="Stop", command=self.stop_analysis)
        self.stop_button.grid(row=5, column=1, pady=10)

        # ==== Right Frame: Progress & Status ====
        progress_frame = ctk.CTkFrame(self.root)
        progress_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Status text
        self.status_text = tk.Text(progress_frame, height=18, width=50)
        self.status_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Thumbnail preview label
        self.preview_label = ctk.CTkLabel(progress_frame, text="")
        self.preview_label.grid(row=2, column=0, padx=5, pady=5)

        # Make the second column (progress_frame) expand
        progress_frame.grid_rowconfigure(1, weight=1)
        progress_frame.grid_columnconfigure(0, weight=1)

    def select_output_dir(self):
        """
        Prompts user to choose an output directory where results will be saved.
        """
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.analyzer.output_dir = dir_path
            self.update_status(f"Output directory set to: {dir_path}")

    def start_analysis(self):
        """
        Initiates the analysis in a separate thread.
        """
        if self.dep_var.get():
            self.update_status("Checking and installing dependencies...")
            self.dependency_manager.check_and_install_dependencies()

        keyword = self.keyword_entry.get()
        num_channels = self.channels_entry.get()
        num_videos = self.videos_entry.get()

        # Basic validation
        if not keyword:
            messagebox.showerror("Error", "Please enter a search keyword.")
            return
        if not num_channels.isdigit() or not num_videos.isdigit():
            messagebox.showerror("Error", "Please enter valid numbers for channels/videos.")
            return

        num_channels = int(num_channels)
        num_videos = int(num_videos)

        # Disable start button while thread is active
        self.start_button.configure(state=tk.DISABLED)

        self.analysis_thread = threading.Thread(
            target=self.run_analysis,
            args=(keyword, num_channels, num_videos),
            daemon=True
        )
        self.analysis_thread.start()

    def stop_analysis(self):
        """
        Tries to stop the analysis gracefully by quitting the driver.
        """
        if hasattr(self, 'analysis_thread') and self.analysis_thread.is_alive():
            self.analyzer.stop_flag = True
            if self.analyzer.driver:
                try:
                    self.analyzer.driver.quit()
                except:
                    pass
            self.analysis_thread.join()
            self.update_status("Analysis stopped by user.")
            self.start_button.configure(state=tk.NORMAL)

    def run_analysis(self, keyword, num_channels, num_videos):
        """
        Main analysis logic: search channels → analyze each.
        """
        try:
            driver_ok = self.analyzer.setup_driver()
            if not driver_ok:
                self.update_status("Failed to set up Chrome driver.")
                return

            self.update_status("Searching for channels...")
            channels = self.analyzer.search_channels(keyword, num_channels)
            self.update_status(f"Found {len(channels)} channel(s).")

            self.progress_bar["maximum"] = len(channels)
            all_data = []

            for i, channel_url in enumerate(channels):
                if self.analyzer.stop_flag:
                    break

                self.update_status(f"Analyzing channel {i+1}/{len(channels)}: {channel_url}")
                channel_data, videos_data = self.analyzer.analyze_channel(channel_url, num_videos)

                if channel_data and videos_data:
                    # We can store each video's combined info, or channel+videos separately
                    for vd in videos_data:
                        # Merge channel and video data for easier output
                        merged = {
                            "channel_name": channel_data["channel_name"],
                            "channel_subscribers": channel_data["subscribers"],
                            "channel_total_videos": "N/A",
                            "channel_total_views": "N/A",
                            "video_title": vd["title"],
                            "video_views": vd.get("views", ""),
                            "video_likes": vd.get("likes", ""),
                            "video_comments": vd.get("comments", ""),
                            "video_upload_date": vd.get("upload_date", ""),
                            "video_url": vd.get("url", ""),
                            "thumbnail_path": vd.get("thumbnail_path", ""),
                            "video_screenshot": vd.get("screenshot", "")
                        }
                        all_data.append(merged)

                self.progress_bar["value"] = i + 1
                self.root.update()

            self.update_status("Analysis complete. Saving results...")
            self.save_results(all_data)
            self.update_status("All done!")
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
        finally:
            try:
                if self.analyzer.driver:
                    self.analyzer.driver.quit()
            except:
                pass
            self.start_button.configure(state=tk.NORMAL)

    def save_results(self, all_data):
        """
        Saves results into an Excel spreadsheet. Also updates the GUI preview if any thumbnail is available.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_path = os.path.join(self.analyzer.output_dir, f'analysis_results_{timestamp}.xlsx')
        os.makedirs(self.analyzer.output_dir, exist_ok=True)

        # Write to Excel
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Channel overview sheet
            channel_info = {}
            for d in all_data:
                cname = d["channel_name"]
                if cname not in channel_info:
                    channel_info[cname] = {
                        "Channel Name": cname,
                        "Subscribers": d["channel_subscribers"],
                        "Creation Date": "N/A",
                        "URL": "N/A",
                        "Average Views (of Analyzed)": 0,
                        "Videos Analyzed": 0
                    }

            # Calculate average views among analyzed videos
            for d in all_data:
                cname = d["channel_name"]
                try:
                    views = int(re.sub(r'[^\d]', '', d["video_views"]))
                except:
                    views = 0
                channel_info[cname]["Average Views (of Analyzed)"] += views
                channel_info[cname]["Videos Analyzed"] += 1

            for cname, info in channel_info.items():
                if info["Videos Analyzed"] > 0:
                    info["Average Views (of Analyzed)"] = int(
                        info["Average Views (of Analyzed)"] / info["Videos Analyzed"]
                    )

            df_channel = pd.DataFrame(channel_info.values())
            df_channel.to_excel(writer, sheet_name='Channel Overview', index=False)

            # Video details
            video_rows = []
            for d in all_data:
                video_rows.append({
                    "Channel Name": d["channel_name"],
                    "Video Title": d["video_title"],
                    "Views": d["video_views"],
                    "Likes": d["video_likes"],
                    "Comments": d["video_comments"],
                    "Upload Date": d["video_upload_date"],
                    "Video URL": d["video_url"],
                    "Thumbnail Path": d["thumbnail_path"],
                    "Screenshot Path": d["video_screenshot"]
                })
            df_videos = pd.DataFrame(video_rows)
            df_videos.to_excel(writer, sheet_name='Video Details', index=False)

        # Update preview if a thumbnail exists
        if all_data and all_data[0].get("thumbnail_path"):
            self.update_preview(all_data[0]["thumbnail_path"])

    def update_status(self, message):
        """
        Writes a timestamped message to the status_text box in the GUI.
        """
        self.status_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.status_text.see(tk.END)
        self.root.update()

    def update_preview(self, image_path):
        """
        Displays a small thumbnail preview in the GUI.
        """
        try:
            if not os.path.isfile(image_path):
                return
            image = Image.open(image_path)
            image.thumbnail((200, 200))
            photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=photo, text="")
            self.preview_label.image = photo
        except Exception as e:
            logging.error(f"Error updating preview: {str(e)}")

    def run(self):
        self.root.mainloop()


def main():
    """
    Entry point:
      1. Check dependencies
      2. Launch the GUI
    """
    dep_manager = DependencyManager()
    # You can uncomment the line below to auto-check on every script launch:
    # dep_manager.check_and_install_dependencies()

    app = AnalyzerGUI()
    app.run()


if __name__ == "__main__":
    main()
