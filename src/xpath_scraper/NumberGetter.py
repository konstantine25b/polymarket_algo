from playwright.sync_api import sync_playwright
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.constants import POLYMARKET_ELON_TWEETS_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TweetCountGetter')

EXIT_BROWSER = 3          # Chromium missing / cannot launch: an installation problem, not a page problem
NAV_TIMEOUT_MS = 45_000   # explicit bounds: a hung page must not be able to stall the caller
ELEMENT_TIMEOUT_MS = 30_000


class BrowserUnavailable(RuntimeError):
    pass


class TweetCountGetter:
    def __init__(self, url=None):
        self.url = url or POLYMARKET_ELON_TWEETS_URL
        self.xpath = "xpath=//*[text()='TWEET COUNT']/../../*[2]"
        logger.info("Initialized TweetCountGetter with URL: %s", self.url)

    @staticmethod
    def _launch(p):
        exe = p.chromium.executable_path
        if not exe or not os.path.exists(exe):
            raise BrowserUnavailable(f"Chromium is not installed (expected {exe}). Run: python -m playwright install chromium")
        try:
            return p.chromium.launch(headless=True)
        except Exception as e:
            raise BrowserUnavailable(f"Chromium failed to launch: {e!s:.300}") from e

    def getTweetCount(self):
        """The page's tweet count, or -1 if the page could not be read. Raises BrowserUnavailable if there is no usable browser."""
        logger.info("Starting tweet count retrieval process")
        with sync_playwright() as p:
            logger.info("Launching browser")
            browser = self._launch(p)
            try:
                page = browser.new_page()
                logger.info("Navigating to %s", self.url)
                page.goto(self.url, timeout=NAV_TIMEOUT_MS)
                logger.info("Locating tweet count element")
                content = page.locator(self.xpath).text_content(timeout=ELEMENT_TIMEOUT_MS)
                count = int(content.strip().replace(",", ""))
                logger.info("Successfully retrieved tweet count: %d", count)
                return count
            except Exception as e:
                logger.error("Failed to retrieve tweet count: %s", str(e)[:400])
            finally:
                browser.close()
        logger.warning("Returning failure value -1")
        return -1


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Read the current tweet count from a Polymarket event page')
    ap.add_argument('--url', default=None, help='Event URL (default: POLYMARKET_ELON_TWEETS_URL from constants)')
    try:
        count = TweetCountGetter(ap.parse_args().url).getTweetCount()
    except BrowserUnavailable as ex:
        print(f"BROWSER_ERROR: {ex}", flush=True)
        sys.exit(EXIT_BROWSER)
    print(f"Tweet count: {count}")
