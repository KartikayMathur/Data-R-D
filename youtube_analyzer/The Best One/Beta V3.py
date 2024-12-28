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
import re

# For Excel/data handling
import pandas as pd

# For image downloads
import requests
from PIL import Image, ImageTk

# For web scraping
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class YouTubeAnalyzerV3:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube Channel Analyzer V3")
        self.root.geometry("900x650")
        self.root.minsize(800, 600)

        # Logging setup
        self.setup_logging()

        # GUI state variables
        self.is_running = False
        self.driver = None

        # Set up GUI elements
        self.create_widgets()

    def setup_logging(self):
        """Set up logging to a file and console."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('youtube_analyzer_v3.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_widgets(self):
        """Create the main UI layout."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(7, weight=1)  # Expandable log area

        # ---------- Search Parameters ----------
        ttk.Label(main_frame, text="Search Keyword:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.keyword_entry = ttk.Entry(main_frame, width=40)
        self.keyword_entry.grid(row=0, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=2)

        ttk.Label(main_frame, text="Initial Videos to Scrape:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.initial_videos_spin = ttk.Spinbox(main_frame, from_=1, to=200, width=10)
        self.initial_videos_spin.set(20)
        self.initial_videos_spin.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(main_frame, text="Top Videos per Channel:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.top_videos_spin = ttk.Spinbox(main_frame, from_=1, to=200, width=10)
        self.top_videos_spin.set(12)
        self.top_videos_spin.grid(row=2, column=1, sticky=tk.W, pady=2)

        # ---------- Output Directory ----------
        ttk.Label(main_frame, text="Output Directory:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.output_dir_entry = ttk.Entry(main_frame, width=40)
        self.output_dir_entry.grid(row=3, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        ttk.Button(main_frame, text="Browse...", command=self.select_output_dir).grid(row=3, column=4, padx=5, pady=2)

        # ---------- Dependencies Option ----------
        self.deps_check_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            main_frame, text="Check & Install Dependencies", variable=self.deps_check_var
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)

        # ---------- Control Buttons ----------
        self.start_button = ttk.Button(main_frame, text="Start Analysis", command=self.start_analysis)
        self.start_button.grid(row=5, column=0, padx=5, pady=5)

        self.stop_button = ttk.Button(main_frame, text="Stop", command=self.stop_analysis, state=tk.DISABLED)
        self.stop_button.grid(row=5, column=1, padx=5, pady=5)

        # ---------- Progress Bar ----------
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100, length=300)
        self.progress_bar.grid(row=5, column=2, columnspan=3, sticky=tk.W, padx=5, pady=5)

        # ---------- Log/Status Output ----------
        self.log_text = tk.Text(main_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=7, column=0, columnspan=5, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        scroll_y = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scroll_y.grid(row=7, column=5, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scroll_y.set)

    def select_output_dir(self):
        """Open a directory selection dialog for output."""
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, directory)

    def check_and_install_dependencies(self):
        """Check and install required Python packages if requested."""
        self.log("Checking for required dependencies...")
        required_packages = [
            "selenium",
            "pandas",
            "Pillow",
            "requests",
            "openpyxl",
            "undetected-chromedriver"
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
                    self.log(f"Successfully installed {pkg}")
                except subprocess.CalledProcessError as e:
                    self.log(f"Failed to install {pkg}: {str(e)}")
                    return False

        self.log("All dependencies are now installed.")
        return True

    def start_analysis(self):
        """Validate input and start the analysis thread."""
        # Validate inputs
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showerror("Error", "Please enter a search keyword.")
            return

        try:
            initial_videos = int(self.initial_videos_spin.get())
            top_videos = int(self.top_videos_spin.get())
            if initial_videos < 1 or top_videos < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter valid positive integers for video counts.")
            return

        out_dir = self.output_dir_entry.get().strip()
        if not out_dir:
            messagebox.showerror("Error", "Please select an output directory.")
            return
        if not os.path.isdir(out_dir):
            messagebox.showerror("Error", "Specified output directory does not exist.")
            return

        # If the user opted to check/install dependencies
        if self.deps_check_var.get():
            if not self.check_and_install_dependencies():
                return

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.log_text.delete("1.0", tk.END)

        # Start the analysis in a separate thread
        analysis_thread = threading.Thread(target=self.run_analysis, daemon=True)
        analysis_thread.start()

    def stop_analysis(self):
        """Signal to stop the analysis."""
        self.is_running = False
        self.log("Stop requested by user...")

    def run_analysis(self):
        """Main analysis workflow."""
        try:
            self.log("Starting web driver...")
            if not self.setup_driver():
                self.log("Failed to launch web driver. Stopping analysis.")
                return

            keyword = self.keyword_entry.get().strip()
            initial_videos = int(self.initial_videos_spin.get())
            top_videos = int(self.top_videos_spin.get())
            base_output_dir = self.output_dir_entry.get().strip()

            # Create/Use a base "youtube_analysis" directory inside user-chosen location
            analysis_folder = os.path.join(base_output_dir, "youtube_analysis")
            os.makedirs(analysis_folder, exist_ok=True)

            # Step 1: Search for videos to find unique channels
            self.log(f"Searching YouTube for '{keyword}' ...")
            channels_data = self.search_videos_for_channels(keyword, initial_videos)

            # Step 2: For each channel, gather stats + top videos
            all_channel_data = []
            total_channels = len(channels_data)
            for index, channel_info in enumerate(channels_data, start=1):
                if not self.is_running:
                    break

                channel_url = channel_info["channel_url"]
                channel_name = channel_info["channel_name"]
                self.log(f"Analyzing channel {index}/{total_channels}: {channel_name}")
                self.update_progress((index / total_channels) * 100)

                # Get channel stats from the "About" page
                stats = self.get_channel_stats(channel_url)
                if not stats:
                    self.log(f"Failed to retrieve stats for {channel_name}, skipping...")
                    continue

                # Get top videos
                top_videos_data = self.get_top_videos(channel_url, top_videos)

                # Combine data into a channel dict
                channel_data = {
                    "channel_name": channel_name,
                    "channel_url": channel_url,
                    "stats": stats,
                    "videos": top_videos_data
                }
                all_channel_data.append(channel_data)

                # Save the channel’s data into its own folder
                self.save_individual_channel_data(analysis_folder, channel_data)

            # Step 3: Create a summary Excel for all channels in youtube_analysis/analysis_summary.xlsx
            if all_channel_data:
                self.create_summary_excel(analysis_folder, all_channel_data)
                self.log(f"Analysis complete! Data saved to {analysis_folder}")
                messagebox.showinfo("Analysis Complete", f"Data saved in:\n{analysis_folder}")
            else:
                self.log("No channel data to save.")
                messagebox.showinfo("No Data", "No valid channel data was found or analyzed.")

        except Exception as e:
            self.log(f"Analysis failed: {str(e)}", level="error")
            messagebox.showerror("Error", f"Analysis failed:\n{str(e)}")
        finally:
            self.cleanup_driver()
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress_var.set(0)

    def setup_driver(self):
        """Set up and launch the undetected Chrome driver."""
        try:
            options = uc.ChromeOptions()
            # Add any desired options, e.g. headless
            # options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')

            self.driver = uc.Chrome(options=options)
            self.driver.set_window_size(1280, 800)
            return True
        except Exception as e:
            self.log(f"Failed to set up driver: {e}", level="error")
            return False

    def cleanup_driver(self):
        """Close the web driver if running."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def search_videos_for_channels(self, keyword, desired_count):
        """
        Perform a YouTube search for the given keyword and collect up to desired_count unique channels.
        Return a list of dicts with channel_name & channel_url.
        """
        search_url = f"https://www.youtube.com/results?search_query={keyword}"
        self.driver.get(search_url)
        time.sleep(2)

        discovered_channels = []
        channel_urls = set()
        scroll_attempts = 0
        max_scroll = 10

        while len(discovered_channels) < desired_count and scroll_attempts < max_scroll and self.is_running:
            video_elems = self.driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer")
            for elem in video_elems:
                if len(discovered_channels) >= desired_count:
                    break
                try:
                    # Channel link & name
                    channel_link_elem = elem.find_element(By.CSS_SELECTOR, "#channel-name a")
                    channel_url = channel_link_elem.get_attribute("href")
                    channel_name = channel_link_elem.text.strip()

                    if channel_url not in channel_urls:
                        channel_urls.add(channel_url)
                        discovered_channels.append({
                            "channel_name": channel_name,
                            "channel_url": channel_url
                        })
                        self.log(f"Found channel: {channel_name}")
                except Exception as ex:
                    self.log(f"Skipping a video: {ex}", level="debug")

            # Scroll down
            if len(discovered_channels) < desired_count:
                self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                scroll_attempts += 1

        self.log(f"Discovered {len(discovered_channels)} channels matching '{keyword}'")
        return discovered_channels

    def get_channel_stats(self, channel_url):
        """Scrape channel about page for stats (subscribers, total videos, creation date, description, etc.)."""
        try:
            about_url = channel_url.rstrip('/') + "/about"
            self.driver.get(about_url)
            time.sleep(2)

            stats = {}

            # Subscriber count
            try:
                subs_elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#subscriber-count"))
                )
                stats['subscribers'] = subs_elem.text.strip()
            except TimeoutException:
                stats['subscribers'] = 'N/A'

            # Total videos
            # Some channels show the total videos in #videos-count
            try:
                vids_elem = self.driver.find_element(By.CSS_SELECTOR, "#videos-count")
                stats['total_videos'] = vids_elem.text.strip()
            except:
                stats['total_videos'] = 'N/A'

            # Channel description
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, "#description")
                stats['description'] = desc_elem.text.strip()
            except:
                stats['description'] = 'N/A'

            # Channel creation date: might be in #right-column > yt-formatted-string (for official channels).
            # or we parse 'Joined <date>' from #right-column. This can vary by region/language.
            try:
                about_text = self.driver.find_element(By.CSS_SELECTOR, "#right-column").text
                # Attempt a regex to find something like "Joined Jan 1, 2020"
                match = re.search(r"Joined\s(.+)", about_text)
                if match:
                    stats['creation_date'] = match.group(1).strip()
                else:
                    stats['creation_date'] = 'N/A'
            except:
                stats['creation_date'] = 'N/A'

            return stats
        except Exception as e:
            self.log(f"Error retrieving channel stats: {e}", level="error")
            return None

    def get_top_videos(self, channel_url, count):
        """
        Go to channel videos page sorted by popularity.
        Scrape up to `count` videos: title, url, views, likes, comments, upload date, thumbnail.
        """
        videos_url = channel_url.rstrip('/') + "/videos?sort=p"
        self.driver.get(videos_url)
        time.sleep(2)

        collected_videos = []
        scroll_attempts = 0
        max_scroll = 15

        while len(collected_videos) < count and scroll_attempts < max_scroll and self.is_running:
            video_elems = self.driver.find_elements(By.CSS_SELECTOR, "ytd-grid-video-renderer")
            for elem in video_elems:
                if len(collected_videos) >= count:
                    break

                try:
                    title_elem = elem.find_element(By.CSS_SELECTOR, "#video-title")
                    title = title_elem.text.strip()
                    video_url = title_elem.get_attribute("href")

                    # Thumbnails
                    thumb_elem = elem.find_element(By.CSS_SELECTOR, "img")
                    thumbnail_url = thumb_elem.get_attribute("src")

                    # Metadata line: e.g. "1.2M views" and "2 weeks ago"
                    meta_elems = elem.find_elements(By.CSS_SELECTOR, "#metadata-line span")
                    views = meta_elems[0].text.strip() if len(meta_elems) > 0 else "N/A"
                    upload_date = meta_elems[1].text.strip() if len(meta_elems) > 1 else "N/A"

                    # (Optional) To get likes/comments, we can open the video in new tab:
                    likes, comments = self.get_video_likes_comments(video_url)

                    collected_videos.append({
                        "title": title,
                        "url": video_url,
                        "views": views,
                        "likes": likes,
                        "comments": comments,
                        "upload_date": upload_date,
                        "thumbnail_url": thumbnail_url
                    })
                    self.log(f"Scraped video: {title}")

                except Exception as ex:
                    self.log(f"Video scraping error: {ex}", level="debug")

            # Scroll down if more videos are needed
            if len(collected_videos) < count:
                self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                scroll_attempts += 1

        return collected_videos[:count]

    def get_video_likes_comments(self, video_url):
        """
        Open video in a new tab, scrape likes and comment count (if available), then close the tab.
        """
        likes_str = "N/A"
        comments_str = "N/A"
        try:
            main_window = self.driver.current_window_handle

            # Open new tab
            self.driver.execute_script(f"window.open('{video_url}','_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(3)

            # Wait for the like button
            try:
                likes_elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'ytd-toggle-button-renderer[is-icon-button]'))
                )
                # Attempt to read aria-label or text
                likes_str = likes_elem.get_attribute("aria-label") or likes_elem.text
            except:
                pass

            # Comments count
            try:
                comments_count_elem = self.driver.find_element(By.CSS_SELECTOR, "#count .count-text")
                comments_str = comments_count_elem.text.strip()
            except:
                pass

        except Exception as e:
            self.log(f"Error retrieving video likes/comments: {e}", level="debug")
        finally:
            # Close tab and return
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

        return likes_str, comments_str

    def save_individual_channel_data(self, base_dir, channel_data):
        """
        Save each channel’s data in:
        base_dir/
            {channel_name}/
                videos_data.xlsx
                channel_stats.json
                thumbnails/
                    video_1.jpg
                    ...
        """
        # Sanitise channel name for folder creation
        safe_channel_name = re.sub(r'[<>:"/\\|?*]', '', channel_data["channel_name"])
        channel_folder = os.path.join(base_dir, safe_channel_name)
        os.makedirs(channel_folder, exist_ok=True)

        # ----- Save channel_stats.json -----
        stats_path = os.path.join(channel_folder, "channel_stats.json")
        try:
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump({
                    "channel_name": channel_data["channel_name"],
                    "channel_url": channel_data["channel_url"],
                    "stats": channel_data["stats"]
                }, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"Failed to save channel_stats.json: {e}", level="error")

        # ----- Download Thumbnails & Prepare Video DataFrame -----
        thumb_dir = os.path.join(channel_folder, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)

        video_records = []
        for idx, vid in enumerate(channel_data["videos"], start=1):
            thumbnail_file = f"video_{idx}.jpg"
            thumbnail_path = os.path.join(thumb_dir, thumbnail_file)

            # Attempt to download the thumbnail
            downloaded_path = self.download_thumbnail(vid["thumbnail_url"], thumbnail_path)
            if not downloaded_path:
                downloaded_path = "Failed to download"

            video_records.append({
                "Title": vid["title"],
                "URL": vid["url"],
                "Views": vid["views"],
                "Likes": vid["likes"],
                "Comments": vid["comments"],
                "Upload Date": vid["upload_date"],
                "Thumbnail Path": downloaded_path
            })

        # ----- Save Video DataFrame to Excel -----
        videos_path = os.path.join(channel_folder, "videos_data.xlsx")
        try:
            df_videos = pd.DataFrame(video_records)
            df_videos.to_excel(videos_path, index=False, sheet_name="Videos")
        except Exception as e:
            self.log(f"Failed to save videos_data.xlsx: {e}", level="error")

    def download_thumbnail(self, url, filepath):
        """Download thumbnail from url to filepath. Return the final local path if successful, else None."""
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                return filepath
        except Exception as e:
            self.log(f"Thumbnail download error: {e}", level="debug")
        return None

    def create_summary_excel(self, base_dir, all_channel_data):
        """
        Create an Excel file named 'analysis_summary.xlsx' in base_dir
        with two sheets: 'Channels Overview' and 'All Videos'
        """
        summary_file = os.path.join(base_dir, "analysis_summary.xlsx")
        try:
            # Sheet1: Channels Overview
            channels_overview = []
            # Sheet2: All Videos
            all_videos = []

            for ch in all_channel_data:
                channels_overview.append({
                    "Channel Name": ch["channel_name"],
                    "Channel URL": ch["channel_url"],
                    "Subscribers": ch["stats"].get("subscribers", "N/A"),
                    "Total Videos (Displayed)": ch["stats"].get("total_videos", "N/A"),
                    "Creation Date": ch["stats"].get("creation_date", "N/A"),
                })

                for vid in ch["videos"]:
                    all_videos.append({
                        "Channel Name": ch["channel_name"],
                        "Video Title": vid["title"],
                        "Video URL": vid["url"],
                        "Views": vid["views"],
                        "Likes": vid["likes"],
                        "Comments": vid["comments"],
                        "Upload Date": vid["upload_date"]
                    })

            df_channels = pd.DataFrame(channels_overview)
            df_all_videos = pd.DataFrame(all_videos)

            with pd.ExcelWriter(summary_file, engine="openpyxl") as writer:
                df_channels.to_excel(writer, sheet_name="Channels Overview", index=False)
                df_all_videos.to_excel(writer, sheet_name="All Videos", index=False)

            self.log(f"Created summary Excel: {summary_file}")
        except Exception as e:
            self.log(f"Failed to create analysis_summary.xlsx: {e}", level="error")

    def update_progress(self, value):
        """Update progress bar."""
        self.progress_var.set(value)
        self.root.update_idletasks()

    def log(self, message, level="info"):
        """
        Log a message to both the text widget and the logger.
        level can be "info", "debug", "warning", "error", etc.
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

        # Write to GUI log
        self.log_text.insert(tk.END, full_message)
        self.log_text.see(tk.END)

    def run(self):
        """Run the Tkinter mainloop."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Handle closing the application window."""
        if self.is_running:
            if not messagebox.askokcancel("Quit", "Analysis is running. Stop and quit?"):
                return
            self.is_running = False

        self.cleanup_driver()
        self.root.destroy()


def main():
    app = YouTubeAnalyzerV3()
    app.run()


if __name__ == "__main__":
    main()
