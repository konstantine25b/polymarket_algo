import os
import subprocess

from playwright.sync_api import sync_playwright


class TweetCSVGetter:
    def __init__(self):
        self.download_dir = "temp"
        os.makedirs(self.download_dir, exist_ok=True)

    def getCSV(self):
        url = "https://www.xtracker.io/"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            page.goto(url)
            with page.expect_download() as download_info:
                page.locator("xpath=//*[text()='Export Data']").first.click()

            download = download_info.value

            save_path = os.path.join(self.download_dir, download.suggested_filename)
            download.save_as(save_path)

            print(f"Downloaded and saved to: {save_path}")
            self.fromat()
            self.merge()

            browser.close()

    def fromat(self):
        subprocess.run(["python3", "src/formating_tweet_data/secondFixDates.py"], check=True)

    def merge(self):
        subprocess.run(["python3", "src/xpath_scraper/combiner.py"], check=True)


if __name__ == '__main__':
    tcg = TweetCSVGetter()
    tcg.getCSV()
