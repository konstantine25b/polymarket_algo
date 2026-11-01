import os
import sys
import subprocess
import logging
from playwright.sync_api import sync_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TweetCSVGetter')

class TweetCSVGetter:
    def __init__(self):
        # Anchor on the repo root so the getter works from any working directory
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.download_dir = os.path.join(self.repo_root, "src", "xpath_scraper", "temp")
        os.makedirs(self.download_dir, exist_ok=True)
        logger.info("Initialized TweetCSVGetter with download directory: %s", self.download_dir)

    def getCSV(self):
        logger.info("Starting CSV download process")
        url = "https://www.xtracker.io/"
        with sync_playwright() as p:
            logger.info("Launching browser")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            logger.info("Navigating to %s", url)
            page.goto(url, timeout=60000)
            logger.info("Clicking 'Export Data' button")
            with page.expect_download(timeout=60000) as download_info:
                page.locator("xpath=//*[text()='Export Data']").first.click()

            download = download_info.value
            logger.info("Download started: %s", download.suggested_filename)

            save_path = os.path.join(self.download_dir, download.suggested_filename)
            download.save_as(save_path)

            logger.info("Downloaded and saved to: %s", save_path)
            self.format()
            self.merge()

            browser.close()

    def _run_step(self, script):
        """Run a pipeline script with the current interpreter; raise if it fails."""
        subprocess.run([sys.executable, os.path.join(self.repo_root, script)], check=True, cwd=self.repo_root)

    def format(self):
        logger.info("Reformatting CSV dates")
        try:
            self._run_step("src/formating_tweet_data/secondFixDates.py")
            logger.info("CSV reformatting completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to reformat CSV: %s", str(e))
            raise

    def merge(self):
        logger.info("Merging CSV files")
        try:
            self._run_step("src/xpath_scraper/combiner.py")
            logger.info("CSV merge completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to merge CSV files: %s", str(e))
            raise


if __name__ == '__main__':
    tcg = TweetCSVGetter()
    tcg.getCSV()
