import requests
import hashlib
import os
from datetime import datetime
from bs4 import BeautifulSoup # Import BeautifulSoup

# --- Constants for GitHub Actions ---
ARTIFACT_PATH = 'state/last_hash.txt'

class WebsiteMonitor:
    def __init__(self, url, bot_token, chat_id):
        self.url = url
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.last_hash = None
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

    # NEW FUNCTION: Extracts only the relevant part of the HTML
    def extract_relevant_content(self, html_content):
        """Parse HTML and return the content of the body tag."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        # We find the <body> tag. This is much more stable than the full HTML.
        body = soup.find('body')
        if body:
            return str(body)
        return html_content # Fallback to full content if body isn't found

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

        # THE KEY CHANGE IS HERE: We now process the content before hashing
        relevant_content = self.extract_relevant_content(content)
        current_hash = self.calculate_hash(relevant_content)
        
        self.last_hash = self.load_last_hash()

        # The rest of the logic is now reliable
        if self.last_hash is None:
            self.save_hash(current_hash)
            print("First run - baseline hash saved.")
            message = f"🎭 <b>Website Monitor Started</b>\n\nNow monitoring: {self.url}\nYou will be notified ONLY when the site's body content changes."
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
