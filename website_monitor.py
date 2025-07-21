import requests
import hashlib
import os
from datetime import datetime
from bs4 import BeautifulSoup

# --- Constants for GitHub Actions ---
ARTIFACT_PATH = 'state/last_hash.txt'

class WebsiteMonitor:
    def __init__(self, url, bot_token, chat_id):
        self.url = url
        self.bot_token = bot_token
        self.chat_id = chat_id
        # We no longer need self.last_hash here, it will be a local variable in run_check
        self.hash_file_path = ARTIFACT_PATH

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

    # --- THIS IS THE FULLY CORRECTED LOGIC ---
    def run_check(self):
        print(f"Checking website at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        content = self.get_page_content()
        if not content:
            print("Failed to fetch website content, stopping check.")
            return

        relevant_content = self.extract_relevant_content(content)
        current_hash = self.calculate_hash(relevant_content)
        
        last_hash = self.load_last_hash()

        # Case 1: This is a first run or a reset. Be SILENT.
        if last_hash is None:
            print("No previous hash found. Saving new hash as baseline. No notification will be sent.")
            self.save_hash(current_hash)
            return # IMPORTANT: Exit the function here.

        # Case 2: A previous hash was found. Compare it.
        if current_hash != last_hash:
            print("Website has changed!")
            message = f"🚨 <b>WEBSITE CHANGED!</b>\n\nThe ticket site has been updated:\n{self.url}\n\nCheck it now for new shows! 🎫"
            if self.send_telegram_message(message):
                self.save_hash(current_hash) # Update the hash only on successful send
                print("Hash updated after successful notification.")
        else:
            # Case 3: No changes.
            print("No changes detected.")

def main():
    WEBSITE_URL = os.getenv("WEBSITE_URL")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHAT_ID = os.getenv("CHAT_ID")
    
    if not all([WEBSITE_URL, BOT_TOKEN, CHAT_ID]):
        print("ERROR: Missing one or more required environment variables.")
        return

    monitor = WebsiteMonitor(WEBSITE_URL, BOT_TOKEN, CHAT_ID)
    monitor.run_check()

if __name__ == "__main__":
    main()
