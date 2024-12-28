import os
import json
import pandas as pd
from datetime import datetime

class FileManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def create_directory_structure(self, keyword, num_channels, num_top_videos):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.base_dir = os.path.join(self.base_dir, f"{keyword}-{num_channels}-{num_top_videos}_{timestamp}")
        os.makedirs(self.base_dir, exist_ok=True)

    def save_channel_stats(self, channel_name, stats):
        channel_dir = os.path.join(self.base_dir, channel_name)
        os.makedirs(channel_dir, exist_ok=True)
        with open(os.path.join(channel_dir, 'channel_stats.json'), 'w') as f:
            json.dump(stats, f)

    def save_videos_data(self, channel_name, videos_data):
        channel_dir = os.path.join(self.base_dir, channel_name)
        videos_data.to_excel(os.path.join(channel_dir, 'videos_data.xlsx'), index=False)

    def save_thumbnail(self, channel_name, video_id, image_data):
        thumbnails_dir = os.path.join(self.base_dir, channel_name, 'thumbnails')
        os.makedirs(thumbnails_dir, exist_ok=True)
        with open(os.path.join(thumbnails_dir, f'{video_id}.jpg'), 'wb') as f:
            f.write(image_data)

    def save_analysis_summary(self, summary_data):
        summary_data.to_excel(os.path.join(self.base_dir, 'analysis_summary.xlsx'), index=False)

# Example usage
if __name__ == "__main__":
    base_dir = "youtube_analysis"
    file_manager = FileManager(base_dir)

    # Create directory structure
    keyword = "python"
    num_channels = 5
    num_top_videos = 10
    file_manager.create_directory_structure(keyword, num_channels, num_top_videos)

    # Save channel stats
    channel_name = "example_channel"
    channel_stats = {
        "channel_name": channel_name,
        "subscriber_count": 1000,
        "total_videos": 50
    }
    file_manager.save_channel_stats(channel_name, channel_stats)

    # Save videos data
    videos_data = pd.DataFrame({
        "title": ["Video 1", "Video 2"],
        "view_count": [100, 200],
        "like_count": [10, 20],
        "comment_count": [5, 10],
        "thumbnail_url": ["url1", "url2"]
    })
    file_manager.save_videos_data(channel_name, videos_data)

    # Save thumbnail
    video_id = "video_1"
    image_data = b"dummy_image_data"  # Replace with actual image data
    file_manager.save_thumbnail(channel_name, video_id, image_data)

    # Save analysis summary
    summary_data = pd.DataFrame({
        "channel_name": ["example_channel"],
        "total_videos": [50],
        "subscriber_count": [1000],
        "average_views": [150]
    })
    file_manager.save_analysis_summary(summary_data)
