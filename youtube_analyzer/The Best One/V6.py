import os
import time
import re
import requests
from PIL import Image
import pytesseract
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup directories
output_dir = "youtube_analysis"
thumbnail_dir = os.path.join(output_dir, "thumbnails")
screenshot_dir = os.path.join(output_dir, "screenshots")
os.makedirs(thumbnail_dir, exist_ok=True)
os.makedirs(screenshot_dir, exist_ok=True)

# Initialize browser
options = webdriver.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=options)
driver.set_window_size(1280, 800)

def extract_text_from_image(image_path):
    """Use OCR to extract text from an image."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"OCR error: {e}")
        return ""

def download_thumbnail(url, path):
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
        print(f"Thumbnail download error: {e}")
    return None

def save_text_to_file(text, file_path):
    """Save extracted text to a file."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

def scrape_channel_details(channel_url):
    """Scrape channel details from the 'About' page."""
    try:
        about_url = channel_url.rstrip('/') + "/about"
        driver.get(about_url)
        time.sleep(2)

        # Take screenshot of the about page
        screenshot_path = os.path.join(screenshot_dir, f"{channel_url.split('/')[-1]}_about.png")
        driver.save_screenshot(screenshot_path)

        # Extract text from the screenshot
        text = extract_text_from_image(screenshot_path)
        save_text_to_file(text, os.path.join(screenshot_dir, f"{channel_url.split('/')[-1]}_about.txt"))

        return text
    except Exception as e:
        print(f"Channel details error: {e}")
        return ""

def scrape_popular_videos(channel_url, max_videos):
    """Scrape popular videos from the channel."""
    videos_data = []
    try:
        videos_url = channel_url.rstrip('/') + "/videos"
        driver.get(videos_url)
        time.sleep(2)

        # Attempt to click "Popular" tab
        try:
            popular_tab = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, '//yt-formatted-string[@title="Popular"]'))
            )
            popular_tab.click()
            time.sleep(2)
        except:
            print("Could not click 'Popular' tab. Using default ordering (Latest?).")

        # Gather up to max_videos
        scroll_attempts = 0
        while len(videos_data) < max_videos and scroll_attempts < 8:
            grid_items = driver.find_elements(By.CSS_SELECTOR, "ytd-grid-video-renderer")
            for gi in grid_items:
                if len(videos_data) >= max_videos:
                    break
                try:
                    vid_title_elem = gi.find_element(By.CSS_SELECTOR, "a#video-title")
                    vid_title = vid_title_elem.text.strip()
                    vid_url = vid_title_elem.get_attribute("href")

                    data_dict = scrape_video_details(vid_url, vid_title)
                    videos_data.append(data_dict)
                except Exception as e:
                    print(f"Error scraping video item: {e}")
            if len(videos_data) < max_videos:
                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                scroll_attempts += 1

    except Exception as e:
        print(f"scrape_popular_videos error: {e}")

    return videos_data[:max_videos]

def scrape_video_details(video_url, video_title):
    """Scrape video details from the video page."""
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
        main_handle = driver.current_window_handle
        driver.execute_script(f"window.open('{video_url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)

        # Take screenshot of the video page
        screenshot_path = os.path.join(screenshot_dir, f"{video_url.split('=')[-1]}_video.png")
        driver.save_screenshot(screenshot_path)

        # Extract text from the screenshot
        text = extract_text_from_image(screenshot_path)
        save_text_to_file(text, os.path.join(screenshot_dir, f"{video_url.split('=')[-1]}_video.txt"))

        # Extract thumbnail URL
        page_source = driver.page_source
        match_thumb = re.search(r'"thumbnailUrl":"([^"]+)"', page_source)
        if match_thumb:
            thumb_url = match_thumb.group(1)
            result["thumbnail_url"] = thumb_url
            thumb_path = os.path.join(thumbnail_dir, f"{video_url.split('=')[-1]}_thumb.jpg")
            download_thumbnail(thumb_url, thumb_path)

    except Exception as e:
        print(f"scrape_video_details error: {e}")
    finally:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(main_handle)

    return result

def main():
    # Example usage
    channel_url = "https://www.youtube.com/@askNK"
    max_videos = 5

    # Scrape channel details
    channel_details = scrape_channel_details(channel_url)
    print("Channel Details:", channel_details)

    # Scrape popular videos
    popular_videos = scrape_popular_videos(channel_url, max_videos)
    print("Popular Videos:", popular_videos)

    # Close browser
    driver.quit()

if __name__ == "__main__":
    main()
