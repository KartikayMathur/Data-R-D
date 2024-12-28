# youtube_analyzer/src/scraper.py
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from .utils import log_info, log_error
from . import utils

class Scraper:
    def __init__(self, browser="Chrome"):
        self.browser = browser
        self.driver = self._init_driver()

    def _init_driver(self):
        # Adjust your WebDriver paths as necessary
        if self.browser == "Chrome":
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")  # If you want a non-visible browser
            driver = webdriver.Chrome(options=options)
        elif self.browser == "Firefox":
            options = webdriver.FirefoxOptions()
            options.add_argument("--headless")
            driver = webdriver.Firefox(options=options)
        elif self.browser == "Edge":
            # Implement Edge WebDriver if desired
            options = webdriver.EdgeOptions()
            options.add_argument("headless")
            driver = webdriver.Edge(options=options)
        else:
            raise ValueError(f"Unsupported browser: {self.browser}")
        return driver

    def scrape_channels(self, keyword):
        """
        Searches YouTube for the given keyword, finds top channels,
        returns channel data.
        """
        log_info(f"Searching YouTube for keyword: {keyword}")
        self.driver.get("https://www.youtube.com/")
        time.sleep(2)

        # Accept cookies or handle disclaimers if they appear (omitted for brevity)
        # Example: self._accept_cookies()

        # Enter keyword in search
        search_box = self.driver.find_element(By.NAME, "search_query")
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)
        
        # Click on "Filters" and select "Channel" if you want to filter strictly for channels 
        # (Optional approach: modify the logic to truly get the top channels)

        # For demonstration, let's just gather some channels from the results:
        channels_data = []
        channel_elements = self.driver.find_elements(By.XPATH, '//a[@href and contains(@href, "/channel/")]')
        unique_channels = []
        for ch in channel_elements:
            ch_url = ch.get_attribute('href')
            if ch_url not in unique_channels:
                unique_channels.append(ch_url)
        
        # Limit to top 20 unique channel URLs
        unique_channels = unique_channels[:20]
        
        log_info(f"Found {len(unique_channels)} channels.")
        # Gather more detailed data for each channel
        result = []
        for ch_url in unique_channels:
            channel_info = self._get_channel_data(ch_url)
            if channel_info:
                result.append(channel_info)

        return result

    def _get_channel_data(self, channel_url):
        """
        Visits a channel page, scrapes data (video details).
        """
        try:
            self.driver.get(channel_url + "/videos")  # Access channel's video tab
            time.sleep(3)
            
            # Scroll or load more if needed (YouTube might require lazy loading)
            # For simplicity, let's just gather the first few videos:
            videos = self.driver.find_elements(By.XPATH, '//a[@id="video-title"]')
            
            channel_name = self.driver.find_element(By.XPATH, '//div[@id="channel-header-container"]//yt-formatted-string[@id="text"]').text
            
            video_data = []
            for v in videos[:50]:  # limiting to first 50 videos
                title = v.get_attribute('title')
                link = v.get_attribute('href')
                
                # Some data points like likes or exact views might not be directly available:
                # This is a simplified approach (real scraping might require more clicks or API usage).
                # For demonstration, let's just put placeholders or try to scrape if visible.
                
                # In some cases, you have to open each video or use an official API (which is recommended by YouTube).
                # Here, let's assume we have them in the text (not always the case in reality).
                
                # We'll store partial info here and let the analyzer script do the rest or placeholder for likes/views.
                video_data.append({
                    "title": title,
                    "link": link,
                    "likes": 0,   # placeholder
                    "views": 0,   # placeholder
                    "thumbnail_url": self._get_thumbnail_from_video_link(link)
                })
            
            return {
                "channel_name": channel_name,
                "channel_url": channel_url,
                "videos": video_data
            }
        except Exception as e:
            log_error(f"Error scraping channel {channel_url}: {e}")
            return None

    def _get_thumbnail_from_video_link(self, video_link):
        """
        Returns a thumbnail URL for a given video link, if possible.
        This might require a bit more logic or direct calls to YouTube,
        or by analyzing watch pages. We can placeholder or attempt a pattern.
        
        For demonstration, let's use a known pattern for standard YouTube thumbnails:
        https://i.ytimg.com/vi/<VIDEO_ID>/hqdefault.jpg
        """
        # Extract video id from the link:
        # Typical link: https://www.youtube.com/watch?v=VIDEO_ID
        if "watch?v=" in video_link:
            vid_id = video_link.split("watch?v=")[-1].split("&")[0]
            return f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
        return ""

    def close(self):
        self.driver.quit()
