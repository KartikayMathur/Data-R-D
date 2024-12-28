from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
import undetected_chromedriver as uc

def setup_driver():
    """Initialize Chrome WebDriver with appropriate settings"""
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    return driver, wait

def convert_youtube_url(url):
    """Convert any YouTube URL to channel page URL"""
    driver, wait = setup_driver()
    try:
        parsed_url = urlparse(url)

        if 'youtube.com' not in parsed_url.netloc and 'youtu.be' not in parsed_url.netloc:
            raise ValueError("Not a valid YouTube URL")

        if '/channel/' in url or '/user/' in url or '/c/' in url:
            return url
        elif 'youtube.com/watch' in url or 'youtu.be' in url:
            driver.get(url)
            channel_link_element = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ytd-video-owner-renderer a")
            ))
            channel_link = channel_link_element.get_attribute('href')
            return channel_link

        return url
    finally:
        driver.quit()

# Example usage
if __name__ == "__main__":
    youtube_url = input("Enter YouTube URL: ")
    try:
        channel_url = convert_youtube_url(youtube_url)
        print(f"Channel URL: {channel_url}")
    except Exception as e:
        print(f"An error occurred: {e}")
