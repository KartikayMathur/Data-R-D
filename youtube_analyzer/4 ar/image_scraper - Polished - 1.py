import os
import requests
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
from queue import Queue


class ImageScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Image Scraper")
        self.root.geometry("800x600")

        # Queue for logging
        self.log_queue = Queue()

        # Input URLs
        tk.Label(root, text="Enter URLs (one per line):").pack()
        self.url_input = tk.Text(root, height=5, width=80)
        self.url_input.pack()

        # Crawl Depth
        tk.Label(root, text="Crawl Depth:").pack()
        self.depth_var = tk.StringVar(value="2")
        self.depth_entry = tk.Entry(root, textvariable=self.depth_var, width=10)
        self.depth_entry.pack()

        # Small Image Filter
        tk.Label(root, text="Skip images smaller than (in KB):").pack()
        self.size_var = tk.StringVar(value="10")  # Default 10 KB
        self.size_entry = tk.Entry(root, textvariable=self.size_var, width=10)
        self.size_entry.pack()

        # Custom Output Path
        tk.Label(root, text="Output Folder:").pack()
        self.output_path = tk.StringVar(value="Downloaded_Images")
        tk.Entry(root, textvariable=self.output_path, width=50).pack()
        tk.Button(root, text="Browse", command=self.select_output_folder).pack()

        # Progress Bar
        self.progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Log Panel
        tk.Label(root, text="Logs:").pack()
        self.log_panel = tk.Text(root, height=15, width=100, state="disabled")
        self.log_panel.pack()

        # Buttons
        self.start_button = ttk.Button(root, text="Start Scraping", command=self.start_scraping)
        self.start_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.stop_event = threading.Event()

    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.set(folder)

    def log_message(self, message):
        """Log messages to the GUI and save to a log file."""
        self.log_queue.put(message)
        with open("scraper_log.txt", "a") as log_file:
            log_file.write(message + "\n")

    def update_logs(self):
        """Update the log panel with messages from the queue."""
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.log_panel.config(state="normal")
            self.log_panel.insert(tk.END, message + "\n")
            self.log_panel.config(state="disabled")
            self.log_panel.see(tk.END)
        self.root.after(100, self.update_logs)

    def clean_url(self, url):
        """Retain only the homepage."""
        parsed_url = urlparse(url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"

    def fetch_html(self, url):
        """Fetch HTML content of a page."""
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            self.log_message(f"Failed to access {url}: {e}")
            return None

    def extract_links_from_menu(self, url, html_content):
        """Extract links from navigation menus."""
        soup = BeautifulSoup(html_content, "html.parser")
        nav_links = set()
        for nav in soup.find_all(["nav", "ul"]):
            for a_tag in nav.find_all("a", href=True):
                link = urljoin(url, a_tag["href"])
                if urlparse(link).netloc == urlparse(url).netloc:
                    nav_links.add(link)
        return nav_links

    def fetch_images(self, url, html_content, page_name, min_size_kb):
        """Fetch images from the current page."""
        soup = BeautifulSoup(html_content, "html.parser")
        images = soup.find_all("img")
        image_urls = []
        for index, img in enumerate(images):
            img_src = img.get("src")
            if img_src:
                img_url = urljoin(url, img_src)
                try:
                    response = requests.head(img_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                    response.raise_for_status()
                    size = int(response.headers.get("Content-Length", 0)) / 1024  # Size in KB
                    if size >= min_size_kb:
                        filename = f"{page_name}_img{index + 1}{os.path.splitext(img_url)[1]}"
                        image_urls.append((img_url, filename))
                except requests.RequestException:
                    continue
        return image_urls

    def download_image(self, img_url, image_name, output_folder):
        """Download an image."""
        try:
            response = requests.get(img_url, stream=True, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            file_path = os.path.join(output_folder, image_name)
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            self.log_message(f"Downloaded: {file_path}")
        except requests.RequestException as e:
            self.log_message(f"Failed to download {img_url}: {e}")

    def scrape_site_structure(self, url, base_folder, max_depth, visited, parent_name, min_size_kb):
        """Recursively scrape the site structure."""
        if url in visited or max_depth == 0 or self.stop_event.is_set():
            return []

        visited.add(url)
        html_content = self.fetch_html(url)
        if not html_content:
            return []

        page_name = urlparse(url).path.strip("/").replace("/", "-") or parent_name
        image_urls = self.fetch_images(url, html_content, page_name, min_size_kb)
        all_images = image_urls

        sub_links = self.extract_links_from_menu(url, html_content)
        for link in sub_links:
            all_images.extend(self.scrape_site_structure(
                link, base_folder, max_depth - 1, visited, page_name, min_size_kb
            ))

        return all_images

    def scrape_entire_site(self, urls, crawl_depth, min_size_kb):
        output_folder = self.output_path.get()
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        all_images = []
        for url in urls:
            clean_home = self.clean_url(url)
            site_folder = os.path.join(output_folder, urlparse(clean_home).netloc.replace(".", "_"))
            os.makedirs(site_folder, exist_ok=True)
            all_images.extend(self.scrape_site_structure(clean_home, site_folder, crawl_depth, set(), "home", min_size_kb))

        total_images = len(all_images)
        self.progress_bar["maximum"] = total_images
        self.progress_bar["value"] = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            for img_url, image_name in all_images:
                if self.stop_event.is_set():
                    break
                executor.submit(self.download_image, img_url, image_name, site_folder)
                self.progress_bar["value"] += 1
                self.root.update_idletasks()

        messagebox.showinfo("Success", "Image scraping completed!")

    def start_scraping(self):
        urls = self.url_input.get("1.0", tk.END).strip().split("\n")
        urls = [self.clean_url(url.strip()) for url in urls if url.strip()]
        crawl_depth = int(self.depth_var.get())
        min_size_kb = int(self.size_var.get())

        if not urls:
            messagebox.showerror("Error", "Please enter at least one URL.")
            return

        self.stop_event.clear()
        threading.Thread(target=self.scrape_entire_site, args=(urls, crawl_depth, min_size_kb)).start()
        self.update_logs()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageScraperApp(root)
    root.mainloop()
