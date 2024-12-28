import subprocess
import sys
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BrowserManager:
    def __init__(self):
        self.driver = None

    def check_dependencies(self):
        required_packages = [
            'selenium', 'pandas', 'Pillow', 'requests', 'openpyxl',
            'undetected-chromedriver'
        ]

        logging.info("Checking dependencies...")
        missing_packages = []

        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            logging.info(f"Installing missing packages: {', '.join(missing_packages)}")
            for package in missing_packages:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                    logging.info(f"Successfully installed {package}")
                except subprocess.CalledProcessError as e:
                    logging.error(f"Failed to install {package}: {str(e)}")
                    return False

        logging.info("All dependencies are installed.")
        return True

    def setup_browser(self):
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        try:
            self.driver = uc.Chrome(options=options)
            logging.info("Browser setup successful")
            return True
        except Exception as e:
            logging.error(f"Failed to setup browser: {str(e)}")
            return False

    def quit_browser(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def get_driver(self):
        return self.driver
