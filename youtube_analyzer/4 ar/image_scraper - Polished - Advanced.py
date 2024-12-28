import os
import requests
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from queue import Queue
import random
import csv
from PIL import Image, ImageTk
import time

class ImageScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Image Scraper")
        self.root.geometry("900x700")

        # Queue for tasks and logs
        self.task_queue = Queue()
        self.log_queue = Queue()

        # Input URLs
        tk.Label(root, text="Enter URLs (one per line):").pack()
        self.url_input = tk.Text(root, height=5, width=100)
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

        # Exclude Patterns
        tk.Label(root, text="Exclude URLs containing (comma-separated):").pack()
        self.exclude_patterns = tk.StringVar(value="")
        tk.Entry(root, textvariable=self.exclude_patterns, width=50).pack()

        # Include Patterns
        tk.Label(root, text="Include URLs containing (comma-separated):").pack()
        self.include_patterns = tk.StringVar(value="")
        tk.Entry(root, textvariable=self.include_patterns, width=50).pack()

        # Maximum Threads
        tk.Label(root, text="Max Threads:").pack()
        self.max_threads = tk.StringVar(value="10")
        tk.Entry(root, textvariable=self.max_threads, width=10).pack()

        # Progress Bar
        self.progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Log Panel
        tk.Label(root, text="Logs:").pack()
        self.log_panel = tk.Text(root, height=15, width=100, state="disabled")
        self.log_panel.pack()

        # Image Preview
        tk.Label(root, text="Image Preview:").pack()
        self.image_label = tk.Label(root)
        self.image_label.pack()

        # Buttons
        self.start_button = ttk.Button(root, text="Start Scraping", command=self.start_scraping)
        self.start_button.pack(side=tk.LEFT, padx=10, pady=10)
        self.stop_event = threading.Event()

    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.set(folder)

    def log_message(self, message):
        self.log_queue.put(message)

    def update_logs(self):
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.log_panel.config(state="normal")
            self.log_panel.insert(tk.END, message + "\n")
            self.log_panel.config(state="disabled")
            self.log_panel.see(tk.END)
        self.root.after(100, self.update_logs)

    def validate_url(self, url):
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def fetch_html(self, url):
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": random.choice(self.get_user_agents())})
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            self.log_message(f"Failed to fetch: {url}")
            return None

    def extract_links(self, url, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        links = set()
        for a_tag in soup.find_all("a", href=True):
            link = urljoin(url, a_tag["href"])
            if self.is_valid_link(link, url):
                links.add(link)
        return links

    def is_valid_link(self, link, base_url):
        parsed_link = urlparse(link)
        parsed_base = urlparse(base_url)
        return parsed_link.netloc == parsed_base.netloc

    def fetch_images(self, url, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append(urljoin(url, src))
        return images

    def scrape_page(self, url, depth):
        if depth == 0 or self.stop_event.is_set():
            return
        self.log_message(f"Scraping: {url}")
        html_content = self.fetch_html(url)
        if html_content:
            links = self.extract_links(url, html_content)
            images = self.fetch_images(url, html_content)
            for img in images:
                self.download_image(img)
            for link in links:
                self.task_queue.put((link, depth - 1))

    def download_image(self, url):
        try:
            response = requests.get(url, stream=True, timeout=10, headers={"User-Agent": random.choice(self.get_user_agents())})
            response.raise_for_status()
            filename = os.path.basename(urlparse(url).path)
            output_folder = self.output_path.get()
            os.makedirs(output_folder, exist_ok=True)
            filepath = os.path.join(output_folder, filename)
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            self.log_message(f"Downloaded: {filepath}")
        except requests.RequestException:
            self.log_message(f"Failed to download: {url}")

    def start_scraping(self):
        urls = self.url_input.get("1.0", tk.END).strip().split("\n")
        urls = [url.strip() for url in urls if url.strip()]
        if not urls:
            messagebox.showerror("Error", "No URLs provided")
            return
        for url in urls:
            if self.validate_url(url):
                self.task_queue.put((url, int(self.depth_var.get())))
            else:
                self.log_message(f"Invalid URL: {url}")
        self.stop_event.clear()
        threading.Thread(target=self.worker).start()
        self.update_logs()

    def worker(self):
        threads = []
        for _ in range(int(self.max_threads.get())):
            thread = threading.Thread(target=self.scrape_worker)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
        self.log_message("Scraping completed!")

    def scrape_worker(self):
        while not self.task_queue.empty() and not self.stop_event.is_set():
            try:
                url, depth = self.task_queue.get_nowait()
                self.scrape_page(url, depth)
                self.task_queue.task_done()
            except Exception as e:
                self.log_message(f"Error: {e}")

    def get_user_agents(self):
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64)",
        ]


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageScraperApp(root)
    root.mainloop()
