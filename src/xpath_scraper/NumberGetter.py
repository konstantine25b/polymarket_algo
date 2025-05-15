from datetime import datetime
from playwright.sync_api import sync_playwright


class TweetCountGetter:
    def __init__(self):
        date_str = datetime.now().strftime("%B %-d")
        print(date_str)
        month, day = date_str.split(' ')
        self.month = str(month).lower()
        self.day = int(day)
        self.xpath = "xpath=//*[text()='TWEET COUNT']/../../*[2]"

    def getTweetCount(self):
        month = self.month
        day = self.day
        for i in range(7):
            url = f"https://polymarket.com/event/elon-musk-of-tweets-{month}-{day - 7}-{day}"
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url)
                try:
                    content = page.locator(self.xpath).text_content()
                    content = int(content)
                    print(f"{month}-{day - 7}-{day} was correct, Tweet count:", content)
                    browser.close()
                    break
                except:
                    browser.close()
                    print(f"{month}-{day - 7}-{day} was wrong")
            day += 1


if __name__ == '__main__':
    tcg = TweetCountGetter()
    tcg.getTweetCount()
