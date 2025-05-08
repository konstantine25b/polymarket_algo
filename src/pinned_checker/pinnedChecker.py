from playwright.sync_api import sync_playwright
from datetime import datetime
import hashlib
import os


class PinnedChecker:
    def __init__(self):
        self.username = "elonmusk"
        self.filepath = "src/pinned_checker/loggedPinned.txt"

    def checkForNewPinnedTweets(self):
        current_results = self.get_pinned_tweets()
        if not current_results:
            return

        for result in current_results:
            if not self.already_logged(result):
                self.log_result(result)

    def get_pinned_tweets(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            url = f"https://x.com/{self.username}"
            page.goto(url, timeout=60000)
            page.wait_for_selector("article")

            tweets = page.query_selector_all("article")
            pinned = []
            for tweet in tweets:
                inner_text = tweet.inner_text()
                if "Pinned" in inner_text:
                    pinned.append(inner_text)

            browser.close()
            return pinned

    def extract_content(self, tweet_text):
        try:
            split_on_name = tweet_text.split(f"@{self.username}")
            return split_on_name[1].split("\n")[3].strip()
        except Exception:
            return tweet_text.strip().split("\n")[0]  # fallback

    def generate_tweet_id(self, content):
        return hashlib.sha256(content.encode()).hexdigest()[:18]

    def already_logged(self, tweet_text):
        content = self.extract_content(tweet_text)
        tweet_id = self.generate_tweet_id(content)

        if not os.path.exists(self.filepath):
            return False

        with open(self.filepath, "r") as f:
            for line in f:
                if line.startswith(f'"{tweet_id}"'):
                    return True
        return False

    def log_result(self, tweet_text):
        content = self.extract_content(tweet_text)
        tweet_id = self.generate_tweet_id(content)
        timestamp = datetime.utcnow().strftime("%Y:%m:%d:%H:%M:%S")
        formatted = f'"{tweet_id}","{content}","{timestamp}"\n'

        with open(self.filepath, "a") as f:
            f.write(formatted)

        print("Logged new pinned tweet:", formatted.strip())

    def get_all_pinned(self):
        if not os.path.exists(self.filepath):
            return []

        results = []
        with open(self.filepath, "r") as f:
            for line in f:
                parts = line.strip().split('","')
                if len(parts) == 3:
                    tweet_id = parts[0].strip('"')
                    content = parts[1]
                    timestamp = parts[2].strip('"')
                    results.append([tweet_id, content, timestamp])
        return results


if __name__ == "__main__":
    checker = PinnedChecker()
    checker.checkForNewPinnedTweets()
