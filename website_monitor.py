import hashlib
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
import requests # Still used for Telegram

# --- Selenium Imports ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- Constants ---
ARTIFACT_PATH = 'state/last_hash.txt'

class WebsiteMonitor:
    def __init__(self, url, bot_token, chat_id):
        self.url = url
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.last_hash = None
        self.hash_file_path = ARTIFACT_PATH

    # --- THIS FUNCTION IS COMPLETELY REPLACED ---
    def get_page_content(self):
        """Fetch website content using a real browser to render JavaScript."""
        print("Setting up headless Chrome browser...")
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run without a visible browser window
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = None # Initialize driver to None
        try:
            # Automatically downloads and manages the correct driver for Chrome
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            print(f"Navigating to {self.url}...")
            driver.get(self.url)
            
            # --- CRUCIAL STEP ---
            # Wait for JavaScript to load the dynamic content.
            # 10 seconds is a good starting point. Adjust if needed.
            print("Waiting 10 seconds for dynamic content to load...")
            time.sleep(10)
            
            print("Fetching page source after JavaScript rendering.")
            # driver.page_source contains the final HTML after JS has run
            return driver.page_source

        except Exception as e:
            print(f"An error occurred with Selenium: {e}")
            self.send_telegram_message(f"🚨 <b>MONITOR ERROR</b>\n\nCould not fetch {self.url} using Selenium.\nError: {e}")
            return None
        finally:
            # Ensure the browser is always closed to free up resources
            if driver:
                print("Closing browser.")
                driver.quit()

    # The rest of the script remains the same!
    def extract_relevant_content(self, html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.find('body')
        if body:
            return str(body)
        return html_content

    def calculate_hash(self, content):
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def load_last_hash(self):
        try:
            if os.path.exists(self.hash_file_path):
                with open(self.hash_file_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"Error loading hash: {e}")
        return None

    def save_hash(self, hash_value):
        try:
            os.makedirs(os.path.dirname(self.hash_file_path), exist_ok=True)
            with open(self.hash_file_path, 'w') as f:
                f.write(hash_value)
            print(f"Hash saved to {self.hash_file_path}")
        except Exception as e:
            print(f"Error saving hash: {e}")

    def send_telegram_message(self, message):
        try:
            telegram_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {'chat_id': self.chat_id, 'text': message, 'parse_mode': 'HTML'}
            response = requests.post(telegram_url, data=data, timeout=30)
            response.raise_for_status()
            print("Telegram notification sent successfully!")
            return True
        except requests.RequestException as e:
            print(f"Error sending Telegram message: {e}")
            return False

    def run_check(self):
        print(f"Checking website at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        content = self.get_page_content()
        if not content:
            print("Failed to fetch website content, stopping check.")
            return

        relevant_content = self.extract_relevant_content(content)
        current_hash = self.calculate_hash(relevant_content)
        
        self.last_hash = self.load_last_hash()

        if self.last_hash is None:
            self.save_hash(current_hash)
            print("First run - baseline hash saved.")
            message = f"🎭 <b>Website Monitor (Selenium) Started</b>\n\nNow monitoring: {self.url}\nYou will be notified ONLY when the site's body content changes."
            self.send_telegram_message(message)
        elif current_hash != self.last_hash:
            print("Website has changed!")
            message = f"🚨 <b>WEBSITE CHANGED!</b>\n\nThe ticket site has been updated:\n{self.url}\n\nCheck it now for new shows! 🎫"
            if self.send_telegram_message(message):
                self.save_hash(current_hash)
                print("Hash updated after successful notification.")
        else:
            print("No changes detected.")

def main():
    WEBSITE_URL = os.getenv("WEBSITE_URL")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHAT_ID = os.getenv("CHAT_ID")
    
    if not all([WEBSITE_URL, BOT_TOKEN, CHAT_ID]):
        print("ERROR: Missing one or more required environment variables (WEBSITE_URL, BOT_TOKEN, CHAT_ID).")
        return

    monitor = WebsiteMonitor(WEBSITE_URL, BOT_TOKEN, CHAT_ID)
    monitor.run_check()

if __name__ == "__main__":
    main()
