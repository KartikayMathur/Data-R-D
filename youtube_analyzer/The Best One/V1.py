import os
import sys
import time
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import requests
from datetime import datetime
import re
import threading

class YouTubeAnalyzer:
    def __init__(self):
        self.setup_logging()
        self.create_gui()
        self.driver = None
        self.is_running = False

    def setup_logging(self):
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            filename='logs/analyzer.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("YouTube Channel Analyzer")
        self.root.geometry("800x600")

        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Search section
        search_frame = ttk.LabelFrame(main_frame, text="Search Configuration", padding="10")
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(search_frame, text="Search Keyword:").grid(row=0, column=0, sticky="w", pady=5)
        self.keyword_entry = ttk.Entry(search_frame, width=40)
        self.keyword_entry.grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(search_frame, text="Initial Videos to Check:").grid(row=1, column=0, sticky="w", pady=5)
        self.initial_videos_entry = ttk.Entry(search_frame, width=10)
        self.initial_videos_entry.grid(row=1, column=1, sticky="w", padx=5)
        self.initial_videos_entry.insert(0, "20")

        ttk.Label(search_frame, text="Top Videos per Channel:").grid(row=2, column=0, sticky="w", pady=5)
        self.top_videos_entry = ttk.Entry(search_frame, width=10)
        self.top_videos_entry.grid(row=2, column=1, sticky="w", padx=5)
        self.top_videos_entry.insert(0, "12")

        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=10)

        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(progress_frame, length=400, mode='determinate', variable=self.progress_var)
        self.progress.grid(row=0, column=0, columnspan=2, pady=10, padx=5)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var, wraplength=380)
        self.status_label.grid(row=1, column=0, columnspan=2, pady=5)

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=10)

        self.start_button = ttk.Button(button_frame, text="Start Analysis", command=self.start_analysis)
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_analysis, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5)

        # Stats display
        self.stats_text = tk.Text(main_frame, height=10, width=60)
        self.stats_text.grid(row=3, column=0, pady=10)
        self.stats_text.insert("1.0", "Analysis statistics will appear here...")
        self.stats_text.config(state="disabled")

        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

    def update_status(self, message):
        self.status_var.set(message)
        logging.info(message)

    def update_stats(self, message):
        self.stats_text.config(state="normal")
        self.stats_text.insert("end", f"\n{message}")
        self.stats_text.see("end")
        self.stats_text.config(state="disabled")

    def start_analysis(self):
        """Start the analysis process"""
        if not self.keyword_entry.get().strip():
            messagebox.showerror("Error", "Please enter a search keyword")
            return

        try:
            initial_videos = int(self.initial_videos_entry.get())
            top_videos = int(self.top_videos_entry.get())
            if initial_videos <= 0 or top_videos <= 0:
                raise ValueError("Video counts must be positive numbers")
        except ValueError as e:
            messagebox.showerror("Error", "Please enter valid numbers for video counts")
            return

        if not self.is_running:
            self.is_running = True
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.stats_text.config(state="normal")
            self.stats_text.delete("1.0", tk.END)
            self.stats_text.config(state="disabled")
            threading.Thread(target=self.run_analysis, daemon=True).start()

    def stop_analysis(self):
        """Stop the analysis process"""
        if self.is_running:
            self.is_running = False
            self.update_status("Stopping analysis...")

    def search_videos(self, keyword, video_count):
        """Search videos and get their channels"""
        self.driver.get(f"https://www.youtube.com/results?search_query={keyword}")
        time.sleep(3)

        videos_data = []
        channels_seen = set()
        scroll_attempts = 0
        max_scroll_attempts = 10

        while len(videos_data) < video_count and scroll_attempts < max_scroll_attempts:
            # Find video elements
            video_elements = self.driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer")

            for video in video_elements:
                if len(videos_data) >= video_count:
                    break

                try:
                    # Get video info
                    title_elem = video.find_element(By.CSS_SELECTOR, "#video-title")
                    channel_elem = video.find_element(By.CSS_SELECTOR, "#channel-name a")

                    channel_url = channel_elem.get_attribute("href")
                    channel_name = channel_elem.text

                    if channel_url not in channels_seen:
                        channels_seen.add(channel_url)
                        videos_data.append({
                            'title': title_elem.text,
                            'video_url': title_elem.get_attribute("href"),
                            'channel_name': channel_name,
                            'channel_url': channel_url
                        })

                        self.update_stats(f"Found channel: {channel_name}")

                except Exception as e:
                    logging.error(f"Error processing video: {str(e)}")
                    continue

            if len(videos_data) < video_count:
                # Scroll down to load more videos
                self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                scroll_attempts += 1

        return videos_data

    def get_channel_stats(self, channel_url):
        """Get channel statistics"""
        try:
            self.driver.get(f"{channel_url}/about")
            time.sleep(3)

            stats = {}

            # Get subscriber count
            try:
                stats['subscribers'] = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "#subscriber-count"
                ).text
            except:
                stats['subscribers'] = 'N/A'

            # Get total videos
            try:
                stats['total_videos'] = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "#videos-count"
                ).text
            except:
                stats['total_videos'] = 'N/A'

            # Get channel description
            try:
                stats['description'] = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "#description"
                ).text
            except:
                stats['description'] = 'N/A'

            return stats
        except Exception as e:
            logging.error(f"Error getting channel stats: {str(e)}")
            return {
                'subscribers': 'N/A',
                'total_videos': 'N/A',
                'description': 'N/A'
            }

    def get_video_details(self, video_url):
        """Get detailed video statistics"""
        try:
            self.driver.get(video_url)
            time.sleep(3)

            # Wait for likes element
            wait = WebDriverWait(self.driver, 10)
            likes_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label*="like"]')))
            likes = likes_element.get_attribute('aria-label')

            # Get comments count
            try:
                comments = self.driver.find_element(By.CSS_SELECTOR, '#comments #count').text
            except:
                comments = 'N/A'

            return likes, comments
        except Exception as e:
            logging.error(f"Error getting video details: {str(e)}")
            return 'N/A', 'N/A'

    def get_top_videos(self, channel_url, video_count):
        """Get top videos from a channel"""
        try:
            # Go to videos tab sorted by popularity
            self.driver.get(f"{channel_url}/videos?sort=p")
            time.sleep(3)

            videos = []
            scroll_attempts = 0
            max_scroll_attempts = 10

            while len(videos) < video_count and scroll_attempts < max_scroll_attempts:
                video_elements = self.driver.find_elements(By.CSS_SELECTOR, "ytd-grid-video-renderer")

                for video in video_elements[:video_count]:
                    if len(videos) >= video_count:
                        break

                    try:
                        # Basic video info
                        title = video.find_element(By.CSS_SELECTOR, "#video-title").text
                        video_url = video.find_element(By.CSS_SELECTOR, "#video-title").get_attribute("href")
                        thumbnail = video.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
                        metadata = video.find_elements(By.CSS_SELECTOR, "#metadata-line span")

                        # Get views and date
                        views = metadata[0].text if len(metadata) > 0 else "N/A"
                        upload_date = metadata[1].text if len(metadata) > 1 else "N/A"

                        # Get detailed stats in a new tab
                        self.driver.execute_script(f'window.open("{video_url}", "_blank");')
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        likes, comments = self.get_video_details(video_url)
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])

                        video_data = {
                            'title': title,
                            'url': video_url,
                            'views': views,
                            'date': upload_date,
                            'likes': likes,
                            'comments': comments,
                            'thumbnail': thumbnail
                        }
                        videos.append(video_data)

                        self.update_stats(f"Processed video: {title}")

                    except Exception as e:
                        logging.error(f"Error processing video: {str(e)}")
                        continue

                if len(videos) < video_count:
                    self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                    time.sleep(2)
                    scroll_attempts += 1

            return videos

        except Exception as e:
            logging.error(f"Error getting top videos: {str(e)}")
            return []

    def save_channel_data(self, base_dir, channel_name, channel_data):
        """Save channel data and thumbnails"""
        try:
            # Create channel directory
            safe_channel_name = re.sub(r'[<>:"/\\|?*]', '', channel_name)
            channel_dir = os.path.join(base_dir, safe_channel_name)
            os.makedirs(channel_dir, exist_ok=True)
            os.makedirs(os.path.join(channel_dir, 'thumbnails'), exist_ok=True)

            # Save thumbnails
            for i, video in enumerate(channel_data['videos']):
                try:
                    response = requests.get(video['thumbnail'])
                    if response.status_code == 200:
                        thumbnail_path = os.path.join(channel_dir, 'thumbnails', f'video_{i+1}.jpg')
                        with open(thumbnail_path, 'wb') as f:
                            f.write(response.content)
                        video['thumbnail_path'] = thumbnail_path
                except Exception as e:
                    logging.error(f"Error saving thumbnail: {str(e)}")
                    video['thumbnail_path'] = 'Failed to download'

            # Save channel data to Excel
            excel_path = os.path.join(channel_dir, 'videos_data.xlsx')

            # Create DataFrames
            channel_info_df = pd.DataFrame([{
                'Channel Name': channel_data['name'],
                'Channel URL': channel_data['url'],
                'Total Videos': channel_data['stats']['total_videos'],
                'Subscribers': channel_data['stats']['subscribers'],
                'Description': channel_data['stats']['description']
            }])

            videos_df = pd.DataFrame(channel_data['videos'])

            # Save to Excel with multiple sheets
            with pd.ExcelWriter(excel_path) as writer:
                channel_info_df.to_excel(writer, sheet_name='Channel Info', index=False)
                videos_df.to_excel(writer, sheet_name='Videos', index=False)

            return channel_dir

        except Exception as e:
            logging.error(f"Error saving channel data: {str(e)}")
            return None

    def run_analysis(self):
        try:
            # Setup Chrome
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            self.driver = uc.Chrome(options=options)

            # Get parameters
            keyword = self.keyword_entry.get()
            initial_videos = int(self.initial_videos_entry.get())
            top_videos_per_channel = int(self.top_videos_entry.get())

            # Create main directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_dir = f'youtube_analysis_{timestamp}'
            os.makedirs(base_dir)

            # Search videos
            self.update_status("Searching for videos...")
            videos_data = self.search_videos(keyword, initial_videos)

            # Process each channel
            all_channel_data = []
            for i, video in enumerate(videos_data):
                if not self.is_running:
                    break

                channel_name = video['channel_name']
                channel_url = video['channel_url']

                self.update_status(f"Analyzing channel {i+1}/{len(videos_data)}: {channel_name}")
                self.progress_var.set((i / len(videos_data)) * 100)

                # Get channel stats
                channel_stats = self.get_channel_stats(channel_url)

                # Get top videos
                top_videos = self.get_top_videos(channel_url, top_videos_per_channel)

                channel_data = {
                    'name': channel_name,
                    'url': channel_url,
                    'stats': channel_stats,
                    'videos': top_videos
                }

                # Save channel data
                channel_dir = self.save_channel_data(base_dir, channel_name, channel_data)
                all_channel_data.append(channel_data)

                self.update_stats(f"Completed analysis of {channel_name}")

            # Create summary Excel
            if all_channel_data:
                summary_path = os.path.join(base_dir, 'analysis_summary.xlsx')
                with pd.ExcelWriter(summary_path) as writer:
                    # Channel overview sheet
                    channels_df = pd.DataFrame([{
                        'Channel Name': cd['name'],
                        'Total Videos': cd['stats']['total_videos'],
                        'Analyzed Videos': len(cd['videos']),
                        'Channel URL': cd['url']
                    } for cd in all_channel_data])
                    channels_df.to_excel(writer, sheet_name='Channels Overview', index=False)

                    # All videos sheet
                    all_videos = []
                    for cd in all_channel_data:
                        for video in cd['videos']:
                            video_data = {
                                'Channel': cd['name'],
                                'Title': video['title'],
                                'URL': video['url'],
                                'Views': video['views'],
                                'Likes': video['likes'],
                                'Comments': video['comments'],
                                'Upload Date': video['date'],
                                'Thumbnail Path': video.get('thumbnail_path', 'N/A')
                            }
                            all_videos.append(video_data)

                    pd.DataFrame(all_videos).to_excel(writer, sheet_name='All Videos', index=False)

            self.update_status(f"Analysis complete! Data saved in: {base_dir}")
            messagebox.showinfo("Success", f"Analysis complete!\nData saved in: {base_dir}")

        except Exception as e:
            logging.error(f"Analysis failed: {str(e)}")
            self.update_status(f"Analysis failed: {str(e)}")
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")

        finally:
            if self.driver:
                self.driver.quit()
            self.is_running = False
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.progress_var.set(0)

if __name__ == "__main__":
    app = YouTubeAnalyzer()
    app.root.mainloop()
