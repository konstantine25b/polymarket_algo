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

class TweetCountGetter:
    def __init__(self):
        self.url = POLYMARKET_ELON_TWEETS_URL
        self.xpath = "xpath=//*[text()='TWEET COUNT']/../../*[2]"
        logger.info("Initialized TweetCountGetter with URL: %s", self.url)

    def getTweetCount(self):
        logger.info("Starting tweet count retrieval process")
        url = self.url
        with sync_playwright() as p:
            logger.info("Launching browser")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            logger.info("Navigating to %s", url)
            page.goto(url)
            try:
                logger.info("Locating tweet count element")
                content = page.locator(self.xpath).text_content()
                content = int(content)
                logger.info("Successfully retrieved tweet count: %d", content)
                browser.close()
                return content
            except Exception as e:
                logger.error("Failed to retrieve tweet count: %s", str(e))
                browser.close()
        logger.warning("Returning failure value -1")
        return -1


if __name__ == '__main__':
    tcg = TweetCountGetter()
    count = tcg.getTweetCount()
    print(f"Tweet count: {count}")
