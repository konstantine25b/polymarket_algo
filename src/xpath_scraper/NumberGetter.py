from playwright.sync_api import sync_playwright

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.constants import POLYMARKET_ELON_TWEETS_URL

class TweetCountGetter:
    def __init__(self):
        self.url = POLYMARKET_ELON_TWEETS_URL
        self.xpath = "xpath=//*[text()='TWEET COUNT']/../../*[2]"

    def getTweetCount(self):
        url = self.url
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            try:
                content = page.locator(self.xpath).text_content()
                content = int(content)
                browser.close()
                return content
            except:
                browser.close()
        return -1


if __name__ == '__main__':
    tcg = TweetCountGetter()
    count = tcg.getTweetCount()
    print(f"Tweet count:", count)
