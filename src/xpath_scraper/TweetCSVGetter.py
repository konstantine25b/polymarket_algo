import json
import logging
import os
import random
import re
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TweetCSVGetter')

EXPECTED_HEADER = ("id", "text", "created_at")


USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0.0.0 Safari/537.36")      # headless Chromium's default UA contains "HeadlessChrome", which bot filters answer with 403


class ExportInvalid(RuntimeError):
    """The downloaded file is not a usable XTracker tweet export (error page, empty, wrong schema)."""


def validate_export(path: str, min_rows: int = 1):
    """Cheap sanity checks BEFORE the format/merge pipeline sees the file (B04): it must exist, be non-empty, not be
    an HTML/error page served with status 200 (the Heroku outage), and carry the expected CSV header + data rows."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise ExportInvalid(f"export missing or empty: {path}")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        head = f.read(4096)
    low = head.lstrip().lower()
    if low.startswith("<") or "<html" in low or "application error" in low:
        raise ExportInvalid("export is an HTML page, not a CSV (site error?)")
    first = [c.strip().strip('"').lower() for c in head.splitlines()[0].split(",")] if head.splitlines() else []
    if tuple(first[:3]) != EXPECTED_HEADER:
        raise ExportInvalid(f"unexpected CSV header: {first[:5]}")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        rows = sum(1 for line in f if re.match(r'\d{15,20},"', line))
    if rows < min_rows:
        raise ExportInvalid(f"export has {rows} tweet rows (need >= {min_rows})")
    return rows


class TweetCSVGetter:
    def __init__(self, tries: int = 3, max_seconds: float = 330.0):
        self.max_seconds = max_seconds            # total budget for all attempts, so the caller's subprocess timeout never hits first
        self.attempt_errors = []
        # Anchor on the repo root so the getter works from any working directory
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.download_dir = os.path.join(self.repo_root, "src", "xpath_scraper", "temp")
        self.tries = tries
        os.makedirs(self.download_dir, exist_ok=True)
        logger.info("Initialized TweetCSVGetter with download directory: %s", self.download_dir)

    def download(self) -> str:
        url = "https://www.xtracker.io/"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(accept_downloads=True, user_agent=USER_AGENT, locale="en-US")
                page = context.new_page()
                logger.info("Navigating to %s", url)
                resp = page.goto(url, timeout=60000, wait_until="domcontentloaded")
                if resp is not None and resp.status >= 400:
                    raise ExportInvalid(f"XTracker answered HTTP {resp.status} {resp.status_text} for {resp.url}")
                button = page.locator("xpath=//*[text()='Export Data']").first
                button.wait_for(state="visible", timeout=30000)          # DOM readiness / missing-button detection
                logger.info("Clicking 'Export Data' button")
                with page.expect_download(timeout=60000) as download_info:
                    button.click()
                download = download_info.value
                name = download.suggested_filename
                if not name.lower().endswith(".csv"):
                    raise ExportInvalid(f"unexpected download name: {name}")
                save_path = os.path.join(self.download_dir, "elonmusk.csv")      # the formatter's fixed input name
                download.save_as(save_path)
                logger.info("Downloaded %s -> %s", name, save_path)
                return save_path
            finally:
                browser.close()

    def getCSV(self) -> dict:
        """Download -> validate -> format -> merge, serialised against other writers. Returns the merge result."""
        sys.path.insert(0, self.repo_root)
        from src.simulation.paper_trader.procutil import file_lock       # stdlib-only helper
        logger.info("Starting CSV download process")
        with file_lock(os.path.join(self.repo_root, "src", "data", ".tweet_refresh.lock"), timeout=600):
            for stale in ("elonmusk.csv", "elonmusk_reformatted.csv"):            # never reuse a previous run's files
                path = os.path.join(self.download_dir, stale)
                if os.path.exists(path):
                    os.remove(path)
            ok, t0 = False, time.time()
            self.attempt_errors = []
            for attempt in range(1, self.tries + 1):
                try:
                    path = self.download()
                    n = validate_export(path)
                    logger.info("Export validated: %d tweet rows", n)
                    ok = True
                    break
                except Exception as ex:                                            # network, site, DOM, bad content
                    self.attempt_errors.append(f"attempt {attempt}: {ex!r:.400}")
                    logger.error("download attempt %d/%d failed: %r", attempt, self.tries, ex)
                    if attempt < self.tries:
                        pause = min(60.0, 5.0 * 2 ** attempt) * (0.5 + random.random())
                        if time.time() - t0 + pause + 120 > self.max_seconds:      # no room for another full attempt
                            logger.error("stopping retries: time budget of %.0fs would be exceeded", self.max_seconds)
                            break
                        time.sleep(pause)
            if not ok:
                raise RuntimeError(f"XTracker export failed after {len(self.attempt_errors)} attempt(s): " + " | ".join(self.attempt_errors))
            self.format()
            return self.merge()

    def _run_step(self, script) -> str:
        """Run a pipeline script with the current interpreter; raise if it fails. Returns its stdout."""
        p = subprocess.run([sys.executable, os.path.join(self.repo_root, script)], cwd=self.repo_root, capture_output=True, text=True)
        sys.stdout.write(p.stdout)
        sys.stderr.write(p.stderr)
        if p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, script, p.stdout, p.stderr)
        return p.stdout

    def format(self):
        logger.info("Reformatting CSV dates")
        try:
            self._run_step("src/formating_tweet_data/secondFixDates.py")
            out = os.path.join(self.download_dir, "elonmusk_reformatted.csv")
            if not os.path.exists(out) or os.path.getsize(out) == 0:
                raise RuntimeError("formatter exited 0 but produced no output file")
            logger.info("CSV reformatting completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to reformat CSV: %s", str(e))
            raise

    def merge(self) -> dict:
        logger.info("Merging CSV files")
        try:
            out = self._run_step("src/xpath_scraper/combiner.py")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to merge CSV files: %s", str(e))
            raise
        m = re.search(r"REFRESH_RESULT (\{.*\})", out)
        if not m:
            raise RuntimeError("merge exited 0 but reported no REFRESH_RESULT")
        logger.info("CSV merge completed successfully")
        return json.loads(m.group(1))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description="Download the XTracker export and merge it into the tweet CSV")
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--max-seconds", type=float, default=330.0, help="total time budget over all attempts")
    cli = ap.parse_args()
    getter = TweetCSVGetter(tries=cli.tries, max_seconds=cli.max_seconds)
    try:
        result = getter.getCSV()
    except Exception as ex:
        # machine-readable failure line for the caller (src.simulation.paper_trader.feeds), then a non-zero exit
        print("REFRESH_ERROR " + json.dumps({"error": f"{ex!r}"[:1500], "attempts": getter.attempt_errors}), flush=True)
        logger.error("tweet refresh failed: %r", ex)
        sys.exit(1)
    print("REFRESH_RESULT " + json.dumps(result), flush=True)
