import requests
from bs4 import BeautifulSoup
import os
import re

# Function to download the YouTube page
def download_youtube_page(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.text
    except requests.RequestException as e:
        print(f"Error downloading the page: {e}")
        return None

# Function to extract the thumbnail URL, video title, and channel name from the YouTube page
def extract_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract video title
    title = soup.find('meta', itemprop='name')['content']

    # Extract channel name
    channel_name = soup.find('link', itemprop='name')['content']

    # Extract thumbnail URL
    thumbnail_url = soup.find('link', itemprop='thumbnailUrl')['href']

    return {
        'title': title,
        'channel_name': channel_name,
        'thumbnail_url': thumbnail_url
    }

# Function to download the thumbnail image
def download_thumbnail(thumbnail_url, output_path):
    try:
        response = requests.get(thumbnail_url)
        response.raise_for_status()  # Raise an error for bad status codes
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"Thumbnail saved to {output_path}")
    except requests.RequestException as e:
        print(f"Error downloading the thumbnail: {e}")

# Function to sanitize the filename
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

# Main function to coordinate the thumbnail extraction and download process
def main(url, output_dir='output'):
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Download the YouTube page
    html_content = download_youtube_page(url)
    if not html_content:
        return

    # Extract the thumbnail URL, video title, and channel name
    video_info = extract_info(html_content)
    if not video_info:
        print("Video information not found")
        return

    # Sanitize the video title and channel name for the filename
    sanitized_title = sanitize_filename(video_info['title'])
    sanitized_channel_name = sanitize_filename(video_info['channel_name'])

    # Construct the filename
    filename = f"{sanitized_title}_{sanitized_channel_name}_thumbnail.jpg"
    output_path = os.path.join(output_dir, filename)

    # Download the thumbnail image
    download_thumbnail(video_info['thumbnail_url'], output_path)

# Example usage
if __name__ == "__main__":
    youtube_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'  # Example YouTube URL
    main(youtube_url)