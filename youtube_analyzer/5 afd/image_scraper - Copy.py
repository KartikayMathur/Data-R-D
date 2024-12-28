import os
import requests
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from queue import Queue
import random
from PIL import Image, ImageTk
import tensorflow as tf
import time
from datetime import datetime

class AdvancedImageScraper:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Image Scraper")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        # Queues and flags
        self.task_queue = Queue()
        self.log_queue = Queue()
        self.stop_event = threading.Event()
        self.visited_links = set()
        self.retries = 3

        # User input widgets
        self._create_widgets()
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure necessary directories and files are created."""
        os.makedirs("Downloaded_Images", exist_ok=True)
        if not os.path.exists("scraper_log.txt"):
            with open("scraper_log.txt", "w") as log_file:
                log_file.write("Scraper Logs\n")

    def _create_widgets(self):
        """Create and organize the user interface elements."""
        # URL Input
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(input_frame, text="Enter URLs (one per line):", font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W)
        self.url_input = tk.Text(input_frame, height=6, width=80)
        self.url_input.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        # Options
        options_frame = tk.Frame(self.root)
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(options_frame, text="Crawl Depth:", font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W)
        self.depth_var = tk.StringVar(value="2")
        tk.Entry(options_frame, textvariable=self.depth_var, width=10).grid(row=0, column=1)

        tk.Label(options_frame, text="Skip images smaller than (in KB):", font=("Arial", 12)).grid(row=0, column=2, sticky=tk.W)
        self.min_size_var = tk.StringVar(value="10")
        tk.Entry(options_frame, textvariable=self.min_size_var, width=10).grid(row=0, column=3)

        tk.Label(options_frame, text="Maximum Threads:", font=("Arial", 12)).grid(row=1, column=0, sticky=tk.W)
        self.max_threads_var = tk.StringVar(value="10")
        tk.Entry(options_frame, textvariable=self.max_threads_var, width=10).grid(row=1, column=1)

        tk.Label(options_frame, text="Output Folder:", font=("Arial", 12)).grid(row=1, column=2, sticky=tk.W)
        self.output_path_var = tk.StringVar(value="Downloaded_Images")
        tk.Entry(options_frame, textvariable=self.output_path_var, width=40).grid(row=1, column=3, padx=5)
        tk.Button(options_frame, text="Browse", command=self._select_output_folder).grid(row=1, column=4, padx=5)

        # Progress and Status
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=800, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.status_label = tk.Label(progress_frame, text="Status: Ready", font=("Arial", 12), fg="blue")
        self.status_label.pack()

        # Logs
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tk.Label(log_frame, text="Logs:", font=("Arial", 12)).pack()
        self.log_panel = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        self.log_panel.pack(fill=tk.BOTH, expand=True)

        # Image Preview
        preview_frame = tk.Frame(self.root)
        preview_frame.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

        tk.Label(preview_frame, text="Image Preview:", font=("Arial", 12)).pack(anchor=tk.W)
        self.image_label = tk.Label(preview_frame)
        self.image_label.pack(expand=True, fill=tk.BOTH)

        # Control Buttons
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(control_frame, text="Start Scraping", command=self._start_scraping).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Pause", command=self._pause_scraping).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Resume", command=self._resume_scraping).pack(side=tk.LEFT, padx=5)

    def _select_output_folder(self):
        """Open a folder selection dialog."""
        folder = filedialog.askdirectory()
        if folder:
            self.output_path_var.set(folder)

    def log_message(self, message):
        """Log a message to the GUI and log file."""
        self.log_queue.put(message)
        with open("scraper_log.txt", "a") as log_file:
            log_file.write(f"{datetime.now()}: {message}\n")

    def update_logs(self):
        """Update the log panel with messages."""
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.log_panel.config(state="normal")
            self.log_panel.insert(tk.END, message + "\n")
            self.log_panel.config(state="disabled")
            self.log_panel.see(tk.END)
        self.root.after(100, self.update_logs)

    def _start_scraping(self):
        """Start the scraping process."""
        urls = self.url_input.get("1.0", tk.END).strip().split("\n")
        urls = [self._clean_url(url.strip()) for url in urls if url.strip()]
        if not urls:
            messagebox.showerror("Error", "Please enter at least one URL.")
            return

        self.stop_event.clear()
        self.visited_links.clear()
        self.log_message("Starting scraping...")

        for url in urls:
            if self._validate_url(url):
                self.task_queue.put((url, int(self.depth_var.get())))
            else:
                self.log_message(f"Invalid URL: {url}")

        threading.Thread(target=self._worker).start()
        self.update_logs()

    def _pause_scraping(self):
        """Pause the scraping process."""
        self.stop_event.set()
        self.status_label.config(text="Paused", fg="orange")

    def _resume_scraping(self):
        """Resume the scraping process."""
        self.stop_event.clear()
        threading.Thread(target=self._worker).start()
        self.status_label.config(text="Resumed", fg="green")

    def _clean_url(self, url):
        """Normalize the URL."""
        parsed_url = urlparse(url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"

    def _validate_url(self, url):
        """Check if a URL is reachable."""
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _worker(self):
        """Worker function to process tasks in the queue."""
        max_threads = int(self.max_threads_var.get())
        threads = []

        for _ in range(max_threads):
            thread = threading.Thread(target=self._scrape_task)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        self.log_message("Scraping completed!")

    def _scrape_task(self):
        """Perform the scraping task."""
        while not self.task_queue.empty() and not self.stop_event.is_set():
            try:
                url, depth = self.task_queue.get_nowait()
                self._scrape_page(url, depth)
                self.task_queue.task_done()
            except Exception as e:
                self.log_message(f"Error: {e}")

    def _scrape_page(self, url, depth):
        """Scrape a single page."""
        if depth == 0 or url in self.visited_links:
            return

        self.visited_links.add(url)
        self.log_message(f"Scraping: {url}")

        html_content = self._fetch_html(url)
        if not html_content:
            return

        links = self._extract_links(url, html_content)
        images = self._fetch_images(url, html_content)

        for img_url in images:
            self._download_image(img_url)

        for link in links:
            self.task_queue.put((link, depth - 1))

    def _fetch_html(self, url):
        """Fetch the HTML content of a page."""
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": random.choice(self._get_user_agents())})
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            self.log_message(f"Failed to fetch: {url}")
            return None

    def _extract_links(self, url, html_content):
        """Extract links from a page."""
        soup = BeautifulSoup(html_content, "html.parser")
        links = set()
        for a_tag in soup.find_all("a", href=True):
            link = urljoin(url, a_tag["href"])
            if self._is_valid_link(link, url):
                links.add(link)
        return links

    def _is_valid_link(self, link, base_url):
        """Validate links based on inclusion and exclusion patterns."""
        exclude_patterns = self.exclude_patterns_var.get().split(",")
        include_patterns = self.include_patterns_var.get().split(",")

        if any(pattern in link for pattern in exclude_patterns):
            return False
        if include_patterns and not any(pattern in link for pattern in include_patterns):
            return False
        return True

    def _fetch_images(self, url, html_content):
        """Fetch image URLs from a page."""
        soup = BeautifulSoup(html_content, "html.parser")
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append(urljoin(url, src))
        return images

    def _download_image(self, url):
        """Download an image."""
        try:
            response = requests.get(url, stream=True, timeout=10, headers={"User-Agent": random.choice(self._get_user_agents())})
            response.raise_for_status()
            filename = os.path.basename(urlparse(url).path)
            filepath = os.path.join(self.output_path_var.get(), filename)

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

            self.log_message(f"Downloaded: {filepath}")
            self._update_image_preview(filepath)
        except requests.RequestException:
            self.log_message(f"Failed to download: {url}")

    def _update_image_preview(self, filepath):
        """Update the image preview in the GUI."""
        try:
            img = Image.open(filepath)
            img.thumbnail((200, 200))
            img_tk = ImageTk.PhotoImage(img)
            self.image_label.config(image=img_tk)
            self.image_label.image = img_tk
        except Exception as e:
            self.log_message(f"Error displaying image: {e}")

    def _get_user_agents(self):
        """Return a list of user agents."""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64)",
        ]


if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedImageScraper(root)
    root.mainloop()
