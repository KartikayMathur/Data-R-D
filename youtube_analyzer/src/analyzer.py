# youtube_analyzer/src/analyzer.py
import os
import pandas as pd
from .utils import download_image, log_info, log_error
from . import utils
from ..config import SPREADSHEETS_DIR, THUMBNAILS_DIR

def analyze_channels(channels_data):
    """
    Sort videos by likes & views, download thumbnails,
    and save data to a spreadsheet.
    """
    log_info("Analyzing channels...")
    
    all_videos = []
    for channel in channels_data:
        channel_name = channel["channel_name"]
        for video in channel["videos"]:
            # Download thumbnail
            thumb_url = video["thumbnail_url"]
            thumbnail_path = ""
            if thumb_url:
                thumbnail_path = download_image(thumb_url, THUMBNAILS_DIR)
            
            all_videos.append({
                "Channel": channel_name,
                "Video Title": video["title"],
                "Likes": video["likes"],
                "Views": video["views"],
                "Video Link": video["link"],
                "Thumbnail Path": thumbnail_path
            })

    # Convert to DataFrame
    df = pd.DataFrame(all_videos)
    if not df.empty:
        # Sort by Likes and then by Views (descending)
        df.sort_values(by=["Likes", "Views"], ascending=False, inplace=True)
        
        os.makedirs(SPREADSHEETS_DIR, exist_ok=True)
        output_file = os.path.join(SPREADSHEETS_DIR, "youtube_analysis.xlsx")
        df.to_excel(output_file, index=False)
        
        log_info(f"Spreadsheet saved to: {output_file}")
    else:
        log_info("No videos found to analyze.")
