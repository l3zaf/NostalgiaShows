# MODIFIED SCRIPT FOR GITHUB ACTIONS

import requests
import hashlib
import os
from datetime import datetime

# --- Constants for GitHub Actions ---
# The path where the hash file will be stored as an artifact
ARTIFACT_PATH = 'state/last_hash.txt'

class WebsiteMonitor:
    def __init__(self, url, bot_token, chat_id):
        self.url = url
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.last_hash = None
        self.hash_file_path = ARTIFACT_PATH # Use the artifact path

    def get_page_content(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching page: {e}")
            self.send_telegram_message(f"🚨 <b>MONITOR ERROR</b>\n\nCould not fetch {self.url}.\nError: {e}")
            return None

    def calculate_hash(self, content):
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    # MODIFIED: Load hash from the artifact file
    def load_last_hash(self):
        try:
            # Check if the artifact was downloaded and the file exists
            if os.path.exists(self.hash_file_path):
                with open(self.hash_file_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"Error loading hash: {e}")
        return None

    # MODIFIED: Save hash to the artifact file
    def save_hash(self, hash_value):
        try:
            # GitHub Actions needs the directory to exist before writing a file
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

    # RENAMED from check_for_changes to run_check
    def run_check(self):
        print(f"Checking website at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        content = self.get_page_content()
        if not content:
            print("Failed to fetch website content, stopping check.")
            return

        current_hash = self.calculate_hash(content)
        self.last_hash = self.load_last_hash()

        if self.last_hash is None:
            self.save_hash(current_hash)
            print("First run - baseline hash saved.")
            message = f"🎭 <b>Website Monitor Started</b>\n\nNow monitoring: {self.url}\nYou'll be notified when the site changes!"
            self.send_telegram_message(message)
        elif current_hash != self.last_hash:
            print("Website has changed!")
            message = f"🚨 <b>WEBSITE CHANGED!</b>\n\nThe ticket site has been updated:\n{self.url}\n\nCheck it now for new shows! 🎫"
            if self.send_telegram_message(message):
                self.save_hash(current_hash)
                print("Hash updated after successful notification.")
        else:
            print("No changes detected.")

# MODIFIED: The main execution block. No more loops or sleep.
def main():
    # --- Configuration from Environment Variables ---
    # We will set these in GitHub Secrets, which is much more secure.
    WEBSITE_URL = os.getenv("WEBSITE_URL")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHAT_ID = os.getenv("CHAT_ID")
    
    if not all([WEBSITE_URL, BOT_TOKEN, CHAT_ID]):
        print("ERROR: Missing one or more required environment variables (WEBSITE_URL, BOT_TOKEN, CHAT_ID).")
        return

    monitor = WebsiteMonitor(WEBSITE_URL, BOT_TOKEN, CHAT_ID)
    monitor.run_check() # Run the check just once.

if __name__ == "__main__":
    main()