# youtube_analyzer/config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SPREADSHEETS_DIR = os.path.join(DATA_DIR, 'spreadsheets')
THUMBNAILS_DIR = os.path.join(DATA_DIR, 'thumbnails')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOGS_DIR, 'app.log')

# You can also store user agent strings, timeouts, or other config variables here.
