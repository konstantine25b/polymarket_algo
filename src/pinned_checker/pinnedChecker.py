from playwright.sync_api import sync_playwright


class PinnedChecker:
    def __init__(self):
        self.username = "elonmusk"
        self.filepath = "src/pinned_checker/loggedPinned.txt"

    def checkForNewPinnedTweet(self) -> bool:
        currentResult = self.get_pinned_tweet()
        if currentResult == "ERROR":
            return False
        if self.alreadyLogged(currentResult):
            return True
        else:
            self.logResult(currentResult)
            return True
        return False

    def get_pinned_tweet(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Go to profile page
            url = f"https://x.com/{self.username}"
            page.goto(url, timeout=60000)

            # Wait for tweets to load
            page.wait_for_selector("article")

            # Find all tweet articles
            tweets = page.query_selector_all("article")
            for tweet in tweets:
                inner_text = tweet.inner_text()
                if "Pinned" in inner_text:
                    browser.close()
                    return inner_text
            else:
                browser.close()
                return "ERROR"

    def alreadyLogged(self, currentResult):
        try:
            with open(self.filepath, "r") as f:
                splitOnName = currentResult.split("@elonmusk")
                # print(splitOnName)
                # print(splitOnName[1].split("\n"))
                content = splitOnName[1].split("\n")[3]
                return f.read() == content
        except FileNotFoundError:
            return False

    def logResult(self, currentResult):
        with open(self.filepath, "w") as f:
            splitOnName = currentResult.split("@elonmusk")
            # print(splitOnName)
            # print(splitOnName[1].split("\n"))
            content = splitOnName[1].split("\n")[3]
            f.write(content)


rei = PinnedChecker()
print(rei.checkForNewPinnedTweet())
