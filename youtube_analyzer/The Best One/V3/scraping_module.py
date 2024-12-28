import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

class YouTubeScraper:
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager

    def search_youtube(self, keyword, count):
        try:
            search_url = f"https://www.youtube.com/results?search_query={keyword}&sp=CAMSAhAB"
            self.browser_manager.get_driver().get(search_url)
            time.sleep(3)  # Allow time for dynamic content to load

            videos = WebDriverWait(self.browser_manager.get_driver(), 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-video-renderer"))
            )

            return videos[:count]
        except Exception as e:
            logging.error(f"Error during YouTube search: {str(e)}")
            return []

    def get_channel_info(self, channel_url, top_videos_count):
        try:
            self.browser_manager.get_driver().get(channel_url)
            time.sleep(3)

            channel_name = self.browser_manager.get_driver().find_element(By.CSS_SELECTOR, "#channel-name").text
            subscriber_count = self.browser_manager.get_driver().find_element(By.CSS_SELECTOR, "#subscriber-count").text

            # Switch to Videos tab and sort by popularity
            videos_tab = self.browser_manager.get_driver().find_element(By.CSS_SELECTOR, "tp-yt-paper-tab:nth-child(4)")
            videos_tab.click()
            time.sleep(2)

            sort_button = self.browser_manager.get_driver().find_element(By.CSS_SELECTOR, "#sort-menu")
            sort_button.click()
            time.sleep(1)

            popularity_option = self.browser_manager.get_driver().find_element(By.CSS_SELECTOR, "tp-yt-paper-listbox > a:nth-child(3)")
            popularity_option.click()
            time.sleep(3)

            return {
                'channel_name': channel_name,
                'subscriber_count': subscriber_count,
                'videos': self.get_video_info(top_videos_count)
            }
        except Exception as e:
            logging.error(f"Error getting channel info: {str(e)}")
            return None

    def get_video_info(self, count):
        videos = []
        try:
            video_elements = WebDriverWait(self.browser_manager.get_driver(), 10).until(
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
            logging.error(f"Error getting video info: {str(e)}")

        return videos

    def download_thumbnail(self, url, filepath):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            logging.error(f"Error downloading thumbnail: {str(e)}")
        return False
