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


def fetch_html(url):
    """Fetch the HTML content of a page."""
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        print(f"Failed to access {url}: {e}")
        return None


def extract_links(url, html_content):
    """Extract links from the HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    links = set()
    for a_tag in soup.find_all("a", href=True):
        link = urljoin(url, a_tag["href"])
        if urlparse(link).netloc == urlparse(url).netloc:  # Only include links from the same domain
            links.add(link)
    return links


def fetch_images(url, html_content, base_folder):
    """Fetch images from the current page."""
    soup = BeautifulSoup(html_content, "html.parser")
    page_name = urlparse(url).path.strip("/").replace("/", "_")
    page_folder = os.path.join(base_folder, page_name if page_name else "Home")

    if not os.path.exists(page_folder):
        os.makedirs(page_folder)

    images = soup.find_all("img")
    image_urls = []
    for img in images:
        img_src = img.get("src")
        if img_src:
            img_url = urljoin(url, img_src)
            image_urls.append((img_url, page_folder))

    return image_urls


def download_image(img_url, save_folder):
    """Download a single image."""
    try:
        response = requests.get(img_url, stream=True, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        filename = os.path.basename(urlparse(img_url).path) or "image.jpg"
        file_path = os.path.join(save_folder, filename)

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded: {file_path}")
    except requests.RequestException as e:
        print(f"Failed to download {img_url}: {e}")


def scrape_site_structure(url, base_folder, max_depth=2, visited=None):
    """Recursively scrape the site structure."""
    if visited is None:
        visited = set()

    if url in visited or max_depth == 0:
        return []

    visited.add(url)
    html_content = fetch_html(url)
    if not html_content:
        return []

    # Extract links and images
    sub_links = extract_links(url, html_content)
    image_urls = fetch_images(url, html_content, base_folder)

    all_images = image_urls

    # Recursively process sub-links
    for link in sub_links:
        all_images.extend(scrape_site_structure(link, base_folder, max_depth - 1, visited))

    return all_images


def scrape_entire_site(urls, max_threads=5, crawl_depth=2):
    output_folder = create_output_folder()
    all_images = []

    for url in urls:
        print(f"Scraping: {url}")
        all_images.extend(scrape_site_structure(url, output_folder, crawl_depth))

    # Download images concurrently
    with ThreadPoolExecutor(max_threads) as executor:
        for img_url, folder in all_images:
            executor.submit(download_image, img_url, folder)

    print("\nImage scraping completed. Check the 'Downloaded_Images' folder.")


if __name__ == "__main__":
    print("Enter the website URLs (comma-separated):")
    urls = input().strip().split(",")
    urls = [url.strip() for url in urls]

    if not urls:
        print("No URLs provided. Exiting.")
    else:
        print("Enter the crawling depth (default is 2):")
        try:
            crawl_depth = int(input().strip())
        except ValueError:
            crawl_depth = 2

        scrape_entire_site(urls, max_threads=10, crawl_depth=crawl_depth)
