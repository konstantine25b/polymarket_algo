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
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
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


class ForecastError(ValueError):
    """A forecast / probability computation that must not be traded on. Callers fail closed (no new entries)."""


def _finite(x) -> bool:
    try:
        return bool(np.isfinite(float(x)))
    except (TypeError, ValueError):
        return False


def validate_forecast(fc, event_slug: Optional[str] = None, now=None, max_future_s: float = 300.0, native: bool = False) -> None:
    """Reject anything that is not a coherent forecast for THIS event before it can make a model ready (B08)."""
    if not isinstance(fc, dict):
        raise ForecastError("forecast is not a dict")
    for k in ("total_predicted", "current_tweets", "time_remaining_days"):
        if k not in fc or not _finite(fc[k]):
            raise ForecastError(f"forecast field {k!r} missing or not finite: {fc.get(k)!r}")
    total, cur, days = float(fc["total_predicted"]), float(fc["current_tweets"]), float(fc["time_remaining_days"])
    if cur < 0 or total < 0:
        raise ForecastError(f"negative count (total {total}, current {cur})")
    if days <= 0:
        raise ForecastError(f"non-positive horizon: {days} days left")
    if total < cur - 0.5:
        raise ForecastError(f"predicted total {total:.1f} is below the tweets already counted ({cur:.0f})")
    slug = fc.get("event_slug")
    if event_slug is not None and slug is not None and slug != event_slug:
        raise ForecastError(f"forecast is for {slug!r}, not {event_slug!r}")
    gen = fc.get("generated_at_utc")
    if gen is not None and now is not None:
        try:
            g = pd.Timestamp(gen)
            g = g.tz_localize("UTC") if g.tzinfo is None else g.tz_convert("UTC")
            ahead = (g - pd.Timestamp(now)).total_seconds()
        except Exception:                                   # unparseable or out of range (e.g. year 2999)
            raise ForecastError(f"unusable generated_at_utc: {gen!r}")
        if ahead > max_future_s:
            raise ForecastError(f"forecast generated in the future ({gen})")
    if native:
        frames = fc.get("frames")
        if not isinstance(frames, dict) or not frames:
            raise ForecastError("native ensemble forecast has no frames")
        vals = list(frames.values())
        if not all(_finite(v) and 0.0 <= float(v) <= 1.0 + 1e-9 for v in vals) or sum(float(v) for v in vals) <= 0:
            raise ForecastError("native frame probabilities are invalid (non-finite, outside [0,1] or zero mass)")
        if abs(sum(float(v) for v in vals) - 1.0) > 0.05:
            raise ForecastError(f"native frame probabilities sum to {sum(float(v) for v in vals):.3f}, not 1")


def gamma_bucket_probs(ranges: Sequence[Range], so_far: float, rate_per_day: float, days_left: float,
                       b: float = 1.15) -> np.ndarray:
    for name, v in (("so_far", so_far), ("rate_per_day", rate_per_day), ("days_left", days_left), ("b", b)):
        if not _finite(v):
            raise ForecastError(f"{name} is not finite: {v!r}")
    if so_far < 0 or rate_per_day < 0 or days_left < 0 or b <= 0:
        raise ForecastError(f"invalid inputs: so_far={so_far} rate={rate_per_day} days_left={days_left} b={b}")
    if not len(ranges):
        raise ForecastError("no bucket ranges")
    lo_edge = np.array([r[0] for r in ranges], float)
    hi_edge = np.array([min(r[1], 10 ** 5) for r in ranges], float)
    mean_rem = b * rate_per_day * days_left
    if mean_rem < 1e-6:
        # Nothing more can happen (market over or zero rate): the count stays where it is. No invented extra activity.
        p = ((lo_edge <= so_far) & (so_far <= hi_edge)).astype(float)
    else:
        cv = 0.30 if days_left >= 4 else 0.45
        k = 1.0 / cv ** 2
        scale = mean_rem / k
        lo = lo_edge - 0.5 - so_far
        hi = hi_edge + 0.5 - so_far
        cdf = lambda x: special.gammainc(k, np.maximum(x, 0.0) / scale)
        p = cdf(hi) - cdf(lo)
    p = np.where(hi_edge < so_far, 0.0, p)          # outcomes already made impossible by the current count
    total = p.sum()
    if not np.isfinite(total) or total <= 1e-12:
        raise ForecastError("zero probability mass over the market's buckets (count outside every bucket?)")
    return p / total


def map_native_frames(frames: Dict[str, float], ranges: Sequence[Range], so_far: Optional[float] = None) -> np.ndarray:
    """Assign each of the ensemble's fixed frames to the market bucket containing its lower bound, zero the buckets
    the current count has already passed, and renormalise only known-good mass (never a uniform fallback)."""
    p = np.zeros(len(ranges))
    for name, prob in frames.items():
        if not _finite(prob) or prob < 0:
            raise ForecastError(f"invalid frame probability {name}: {prob!r}")
        lo, _ = parse_range(name)
        for i, (a, b) in enumerate(ranges):
            if a <= lo <= b:
                p[i] += prob
                break
    if so_far is not None:
        p = np.where(np.array([min(r[1], 10 ** 5) for r in ranges], float) < so_far, 0.0, p)
    total = p.sum()
    if total <= 1e-12:
        raise ForecastError("native ensemble frames put zero mass on the live buckets")
    return p / total


class CalibratedModel:
    name = "calibrated"

    def __init__(self, b: float = 1.15):
        self.b = b
        self.rate = None
        self.updated = None

    def update(self, forecast_total: float, so_far_at_forecast: float, days_left_at_forecast: float, ts=None):
        validate_forecast({"total_predicted": forecast_total, "current_tweets": so_far_at_forecast,
                           "time_remaining_days": days_left_at_forecast})
        self.rate = max((forecast_total - so_far_at_forecast) / days_left_at_forecast, 0.0)
        self.updated = ts

    @property
    def ready(self):
        return self.rate is not None

    def probs(self, ranges, so_far, days_left, **_):
        return gamma_bucket_probs(ranges, so_far, self.rate, days_left, self.b)

    def to_dict(self):
        return {"kind": "calibrated", "b": self.b, "rate": self.rate}


class NativeEnsembleModel:
    name = "ensemble"

    def __init__(self):
        self.frames = None
        self.updated = None

    def update_frames(self, frames: Dict[str, float], ts=None):
        validate_forecast({"total_predicted": 0, "current_tweets": 0, "time_remaining_days": 1, "frames": frames}, native=True)
        self.frames = frames
        self.updated = ts

    @property
    def ready(self):
        return self.frames is not None

    def probs(self, ranges, so_far=None, days_left=None, **_):
        return map_native_frames(self.frames, ranges, so_far)

    def to_dict(self):
        return {"kind": "ensemble", "frames": self.frames}
