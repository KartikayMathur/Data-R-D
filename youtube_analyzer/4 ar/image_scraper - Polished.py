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


def extract_links_from_menu(url, html_content):
    """Extract links specifically from navigation menus."""
    soup = BeautifulSoup(html_content, "html.parser")
    nav_links = set()

    # Look for <nav>, <ul>, or dropdown-like containers
    for nav in soup.find_all(["nav", "ul"]):
        for a_tag in nav.find_all("a", href=True):
            link = urljoin(url, a_tag["href"])
            if urlparse(link).netloc == urlparse(url).netloc:  # Internal links only
                nav_links.add(link)

    return nav_links


def fetch_images(url, html_content, page_name):
    """Fetch images from the current page and name them after the page."""
    soup = BeautifulSoup(html_content, "html.parser")
    images = soup.find_all("img")
    image_urls = []

    for index, img in enumerate(images):
        img_src = img.get("src")
        if img_src:
            img_url = urljoin(url, img_src)
            image_name = f"{page_name}_img{index + 1}.jpg"  # Naming format
            image_urls.append((img_url, image_name))

    return image_urls


def download_image(img_url, image_name, output_folder):
    """Download a single image with a specific name."""
    try:
        response = requests.get(img_url, stream=True, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        file_path = os.path.join(output_folder, image_name)

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded: {file_path}")
    except requests.RequestException as e:
        print(f"Failed to download {img_url}: {e}")


def scrape_site_structure(url, base_folder, max_depth=2, visited=None, parent_name="home"):
    """Recursively scrape the site structure."""
    if visited is None:
        visited = set()

    if url in visited or max_depth == 0:
        return []

    visited.add(url)
    html_content = fetch_html(url)
    if not html_content:
        return []

    # Extract navigation menu links
    sub_links = extract_links_from_menu(url, html_content)

    # Extract images, using the parent name as part of the image name
    page_name = urlparse(url).path.strip("/").replace("/", "-") or parent_name
    image_urls = fetch_images(url, html_content, page_name)

    all_images = image_urls

    # Recursively process sub-links
    for link in sub_links:
        subpage_name = link.split("/")[-1].replace("-", "_") or parent_name
        all_images.extend(scrape_site_structure(link, base_folder, max_depth - 1, visited, subpage_name))

    return all_images


def scrape_entire_site(urls, max_threads=5, crawl_depth=2):
    output_folder = create_output_folder()
    all_images = []

    for url in urls:
        print(f"Scraping: {url}")
        all_images.extend(scrape_site_structure(url, output_folder, crawl_depth))

    # Download images concurrently
    with ThreadPoolExecutor(max_threads) as executor:
        for img_url, image_name in all_images:
            executor.submit(download_image, img_url, image_name, output_folder)

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
