# youtube_analyzer/src/utils.py
import os
import requests
import logging
from ..config import LOG_FILE

def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def log_info(message):
    logging.info(message)
    print(message)

def log_error(message):
    logging.error(message)
    print(f"ERROR: {message}")

def download_image(url, folder):
    """
    Download an image from `url` and save it in `folder`.
    Returns the local path to the saved file.
    """
    if not url:
        return ""
    os.makedirs(folder, exist_ok=True)

    try:
        filename = url.split('/')[-1]
        if not filename.endswith('.jpg'):
            filename += '.jpg'
        file_path = os.path.join(folder, filename)

        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            log_info(f"Thumbnail saved: {file_path}")
            return file_path
        else:
            log_error(f"Failed to download image: {url} (status code: {r.status_code})")
    except Exception as e:
        log_error(f"Exception during image download: {e}")
    return ""
