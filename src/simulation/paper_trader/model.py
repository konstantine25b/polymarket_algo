"""
Turns forecasts into per-bucket probabilities.

CalibratedModel  (default, the version that was backtested)
    The ensemble predicts a final tweet total. From it we take a daily rate for the rest of the
    market, scale it by `b` (the ensemble under-predicts), and model the tweets still to come as a
    Gamma distribution whose relative spread (cv) is 0.30 with >=4 days left and 0.45 below that.
    final count = tweets so far + Gamma(mean = b * rate * days_left, cv).
    Probabilities are recomputed on every tick from the live tweet count, so they move with the clock.

NativeEnsembleModel
    The ensemble's own bucket probabilities, held fixed between model refreshes.
"""
import re
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy import special

Range = Tuple[int, int]


def parse_range(title: str) -> Range:
    t = title.strip()
    if t.startswith("<"):
        return 0, int(t[1:]) - 1
    if t.endswith("+"):
        return int(t[:-1]), 10 ** 5
    a, b = re.split(r"[-–]", t)
    return int(a), int(b)


def gamma_bucket_probs(ranges: Sequence[Range], so_far: float, rate_per_day: float, days_left: float,
                       b: float = 1.15) -> np.ndarray:
    cv = 0.30 if days_left >= 4 else 0.45
    mean_rem = max(b * rate_per_day * max(days_left, 0.0), 1.0)
    k = 1.0 / cv ** 2
    scale = mean_rem / k
    lo = np.array([r[0] for r in ranges], float) - 0.5 - so_far
    hi = np.array([min(r[1], 10 ** 5) for r in ranges], float) + 0.5 - so_far
    cdf = lambda x: special.gammainc(k, np.maximum(x, 0.0) / scale)
    p = cdf(hi) - cdf(lo)
    total = p.sum()
    return p / total if total > 0 else np.full(len(p), 1.0 / len(p))


def map_native_frames(frames: Dict[str, float], ranges: Sequence[Range]) -> np.ndarray:
    """Assign each of the ensemble's fixed frames to the market bucket containing its lower bound."""
    p = np.zeros(len(ranges))
    for name, prob in frames.items():
        lo, _ = parse_range(name)
        for i, (a, b) in enumerate(ranges):
            if a <= lo <= b:
                p[i] += prob
                break
    total = p.sum()
    return p / total if total > 0 else np.full(len(p), 1.0 / len(p))


class CalibratedModel:
    name = "calibrated"

    def __init__(self, b: float = 1.15):
        self.b = b
        self.rate = None
        self.updated = None

    def update(self, forecast_total: float, so_far_at_forecast: float, days_left_at_forecast: float, ts=None):
        self.rate = max((forecast_total - so_far_at_forecast) / max(days_left_at_forecast, 1e-6), 1.0)
        self.updated = ts

    @property
    def ready(self):
        return self.rate is not None

    def probs(self, ranges, so_far, days_left, **_):
        return gamma_bucket_probs(ranges, so_far, self.rate, days_left, self.b)


class NativeEnsembleModel:
    name = "ensemble"

    def __init__(self):
        self.frames = None
        self.updated = None

    def update_frames(self, frames: Dict[str, float], ts=None):
        self.frames = frames
        self.updated = ts

    @property
    def ready(self):
        return self.frames is not None

    def probs(self, ranges, so_far=None, days_left=None, **_):
        return map_native_frames(self.frames, ranges)
