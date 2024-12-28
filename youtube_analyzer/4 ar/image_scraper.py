import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor


def create_output_folder():
    folder = "Downloaded_Images"
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


def fetch_images_from_url(url, output_folder):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to access {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    images = soup.find_all("img")
    domain = urlparse(url).netloc.replace('.', '_')
    domain_folder = os.path.join(output_folder, domain)

    if not os.path.exists(domain_folder):
        os.makedirs(domain_folder)

    image_urls = []
    for img in images:
        img_src = img.get("src")
        if img_src:
            img_url = urljoin(url, img_src)
            image_urls.append((img_url, domain_folder))
    return image_urls


def download_image(img_url, save_folder):
    try:
        response = requests.get(img_url, stream=True, timeout=10)
        response.raise_for_status()
        filename = os.path.basename(urlparse(img_url).path)
        if not filename:
            filename = "image_" + os.path.basename(img_url)
        file_path = os.path.join(save_folder, filename)

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded: {file_path}")
    except requests.RequestException as e:
        print(f"Failed to download {img_url}: {e}")


def scrape_images(urls, max_threads=5):
    output_folder = create_output_folder()
    all_images = []

    # Fetch image URLs
    with ThreadPoolExecutor(max_threads) as executor:
        results = executor.map(fetch_images_from_url, urls, [output_folder] * len(urls))
        for result in results:
            all_images.extend(result)

    # Download images
    with ThreadPoolExecutor(max_threads) as executor:
        for img_url, folder in all_images:
            executor.submit(download_image, img_url, folder)

    print("\nImage scraping completed. Check the 'Downloaded_Images' folder.")


if __name__ == "__main__":
    # Input URLs
    print("Enter the website URLs (comma-separated):")
    urls = input().strip().split(",")
    urls = [url.strip() for url in urls]

    if not urls:
        print("No URLs provided. Exiting.")
    else:
        scrape_images(urls)
