import os
import logging
import pandas as pd
from datetime import datetime

class FileOrganizer:
    def create_excel_report(self, data, output_dir):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"youtube_analysis_{timestamp}.xlsx")

            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Channel Overview sheet
                channel_data = []
                for channel in data:
                    channel_data.append({
                        'Channel Name': channel['channel_name'],
                        'Subscribers': channel['subscriber_count'],
                        'Videos Analyzed': len(channel['videos'])
                    })

                pd.DataFrame(channel_data).to_excel(writer, sheet_name='Channel Overview', index=False)

                # Video Details sheet
                video_data = []
                for channel in data:
                    for video in channel['videos']:
                        video_data.append({
                            'Channel': channel['channel_name'],
                            'Title': video['title'],
                            'Views': video['views'],
                            'Upload Date': video['date'],
                            'URL': video['url'],
                            'Thumbnail Path': video.get('thumbnail_path', '')
                        })

                pd.DataFrame(video_data).to_excel(writer, sheet_name='Video Details', index=False)

            logging.info(f"Excel report created: {filename}")
            return filename
        except Exception as e:
            logging.error(f"Error creating Excel report: {str(e)}")
            return None
