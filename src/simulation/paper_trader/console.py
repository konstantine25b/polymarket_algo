"""
Human-readable console output (banners, tables, decision blocks) that is also appended to
<run dir>/console.log, so what you saw on screen can be re-read after the run. Logger lines
(timestamped) are mirrored into the same file by runner.configure_logging(mirror_console=True).
"""
import os
from datetime import datetime

WIDTH = 100


class Console:
    def __init__(self, run_dir: str, enabled: bool = True):
        self.enabled = enabled
        self.path = os.path.join(run_dir, "console.log")

    def say(self, text: str = ""):
        if not self.enabled:
            return
        print(text, flush=True)
        with open(self.path, "a") as f:
            f.write(text + "\n")

    def banner(self, title: str, ch: str = "="):
        self.say("")
        self.say(ch * WIDTH)
        self.say(title)
        self.say(ch * WIDTH)

    def section(self, title: str):
        self.say("")
        self.say(f"--- {title} " + "-" * max(0, WIDTH - len(title) - 5))


def pct(x, nd=1):
    return "   -  " if x is None else f"{x * 100:{5 + nd}.{nd}f}%"[-(6 + nd):]
