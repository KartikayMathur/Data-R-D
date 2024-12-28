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
import tensorflow as tf
from tensorflow.keras.preprocessing.image import img_to_array, load_img
import os
import re
import subprocess
import sys

def install_packages_from_file(file_path):
    """
    Parse a Python file for imported packages and install them using pip.

    Args:
        file_path (str): Path to the Python file.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    try:
        with open(file_path, "r") as file:
            content = file.read()

        # Find all import statements
        imports = re.findall(r"^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)", content, re.MULTILINE)

        # Extract unique top-level packages (e.g., "requests" from "from requests import get")
        packages = {module.split('.')[0] for module in imports}

        if not packages:
            print("No packages found in the file.")
            return

        print(f"Found packages: {', '.join(packages)}")

        # Install each package
        for package in packages:
            print(f"Installing: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("All packages installed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")

# Specify the path to the current file or another file
current_file = __file__  # This script's file
# Or replace __file__ with a specific file path:
# current_file = "path/to/your_file.py"

install_packages_from_file(current_file)

class AdvancedImageScraper:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Image Scraper")
        self.root.geometry("1100x850")

        # Variables and queues
        self.task_queue = Queue()
        self.log_queue = Queue()
        self.stop_event = threading.Event()
        self.visited_links = set()
        self.retries = 3

        # User input widgets
        self._create_input_widgets()
        self._create_progress_widgets()
        self._create_log_widgets()
        self._create_preview_widget()

        # Ensure required directories and files exist
        self._create_required_files_and_directories()

    def _create_required_files_and_directories(self):
        """Create required files and directories if they don't exist."""
        os.makedirs("Downloaded_Images", exist_ok=True)
        if not os.path.exists("scraper_log.txt"):
            with open("scraper_log.txt", "w") as log_file:
                log_file.write("Scraper Logs\n")

    def _create_input_widgets(self):
        """Create widgets for user inputs."""
        tk.Label(self.root, text="Enter URLs (one per line):", font=("Arial", 12)).pack()
        self.url_input = tk.Text(self.root, height=6, width=120)
        self.url_input.pack(pady=5)

        tk.Label(self.root, text="Crawl Depth:", font=("Arial", 12)).pack()
        self.depth_var = tk.StringVar(value="2")
        tk.Entry(self.root, textvariable=self.depth_var, width=10).pack()

        tk.Label(self.root, text="Skip images smaller than (in KB):", font=("Arial", 12)).pack()
        self.min_size_var = tk.StringVar(value="10")
        tk.Entry(self.root, textvariable=self.min_size_var, width=10).pack()

        tk.Label(self.root, text="Exclude URLs containing (comma-separated):", font=("Arial", 12)).pack()
        self.exclude_patterns_var = tk.StringVar(value="")
        tk.Entry(self.root, textvariable=self.exclude_patterns_var, width=100).pack()

        tk.Label(self.root, text="Include URLs containing (comma-separated):", font=("Arial", 12)).pack()
        self.include_patterns_var = tk.StringVar(value="")
        tk.Entry(self.root, textvariable=self.include_patterns_var, width=100).pack()

        tk.Label(self.root, text="Maximum Threads:", font=("Arial", 12)).pack()
        self.max_threads_var = tk.StringVar(value="10")
        tk.Entry(self.root, textvariable=self.max_threads_var, width=10).pack()

        tk.Label(self.root, text="Request Delay (seconds):", font=("Arial", 12)).pack()
        self.request_delay_var = tk.StringVar(value="1")
        tk.Entry(self.root, textvariable=self.request_delay_var, width=10).pack()

        tk.Label(self.root, text="Output Folder:", font=("Arial", 12)).pack()
        self.output_path_var = tk.StringVar(value="Downloaded_Images")
        tk.Entry(self.root, textvariable=self.output_path_var, width=80).pack()
        tk.Button(self.root, text="Browse", command=self._select_output_folder).pack()

    def _create_progress_widgets(self):
        """Create progress bar and status display widgets."""
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=800, mode="determinate")
        self.progress_bar.pack(pady=10)

        self.status_label = tk.Label(self.root, text="Status: Ready", font=("Arial", 12), fg="blue")
        self.status_label.pack()

    def _create_log_widgets(self):
        """Create widgets for log display."""
        tk.Label(self.root, text="Logs:", font=("Arial", 12)).pack()
        self.log_panel = tk.Text(self.root, height=10, width=140, state="disabled")
        self.log_panel.pack()

    def _create_preview_widget(self):
        """Create widgets for image preview."""
        tk.Label(self.root, text="Image Preview:", font=("Arial", 12)).pack()
        self.image_label = tk.Label(self.root)
        self.image_label.pack()

        # Control buttons
        self.start_button = ttk.Button(self.root, text="Start Scraping", command=self._start_scraping)
        self.start_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.pause_button = ttk.Button(self.root, text="Pause", command=self._pause_scraping)
        self.pause_button.pack(side=tk.LEFT, padx=10)

        self.resume_button = ttk.Button(self.root, text="Resume", command=self._resume_scraping)
        self.resume_button.pack(side=tk.LEFT, padx=10)

    def _select_output_folder(self):
        """Open a folder selection dialog."""
        folder = filedialog.askdirectory()
        if folder:
            self.output_path_var.set(folder)

    def log_message(self, message):
        """Log a message to the GUI and log file."""
        self.log_queue.put(message)
        with open("scraper_log.txt", "a") as log_file:
            log_file.write(message + "\n")

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
