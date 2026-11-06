"""
Light-weight tweet-count model (replaces the Prophet / NeuralProphet / TimesFM ensemble for trading).

Pure numpy/scipy, a few milliseconds per forecast, ~50 MB of RAM, no subprocess, no GPU, no model downloads.

How it works
  1. Intensity profile from the tweet history (only tweets strictly BEFORE the as-of time - causal):
       intensity(hour) = daily_level * day_of_week_weight * hour_of_day_share      (all in US/Eastern wall-clock)
     daily_level = mean tweets/day over the last `level_days` days; day-of-week weights from the last `dow_weeks`
     weeks; hour-of-day shares from the last `hod_days` days.
  2. Gamma-Poisson update of a weekly "level multiplier" lambda: prior Gamma(a, a) (mean 1, so the recent level is
     the prior guess), data = tweets counted so far in this market vs what the profile expected for the same hours.
     Counts are clumpy, so observed/expected counts are divided by `phi` (variance inflation) before the update.
  3. Tweets still to come ~ negative binomial with the posterior mean and variance (level uncertainty + Poisson noise
     inflated by phi). Bucket probabilities = NB mass of (final count - so_far) inside each bucket.

All parameters were chosen by walk-forward backtest (see src/simulation/backtest/).
"""
from dataclasses import dataclass, asdict
from typing import Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from .model import ForecastError


STALE_GAP_H = 18.0


@dataclass
class LightParams:
    level_days: int = 21
    hod_days: int = 28
    dow_weeks: int = 8
    prior_a: float = 16.0       # strength of the "level = recent level" prior (relative sd of the weekly level = 1/sqrt(a))
    phi: float = 12.0           # variance inflation of tweet counts relative to Poisson
    level_floor: float = 5.0    # tweets/day floor so a quiet stretch can never give a zero rate

    def as_dict(self):
        return asdict(self)


def load_times(csv_path: str) -> np.ndarray:
    """Sorted tweet timestamps (naive US/Eastern wall-clock) as datetime64[ns]."""
    t = pd.to_datetime(pd.read_csv(csv_path, usecols=["created_at"]).created_at, format="%Y:%m:%d:%H:%M:%S", errors="coerce").dropna()
    return np.sort(t.values)


class LightModel:
    def __init__(self, times: np.ndarray, params: Optional[LightParams] = None):
        self.p = params or LightParams()
        self.times = times
        self._hourly = None

    # ---- profile -------------------------------------------------------------------------------------------
    def _hour_counts(self) -> pd.Series:
        if self._hourly is None:
            s = pd.Series(1, index=pd.DatetimeIndex(self.times).floor("h")).groupby(level=0).sum()
            full = pd.date_range(s.index.min(), s.index.max(), freq="h")
            self._hourly = s.reindex(full, fill_value=0).astype(float)
        return self._hourly

    def fit(self, asof) -> "LightModel":
        """Estimate level / day-of-week / hour-of-day from complete hours before `asof` (naive ET Timestamp)."""
        p, h = self.p, self._hour_counts()
        asof = pd.Timestamp(asof)
        end = asof.floor("h")
        newest = pd.Timestamp(self.times[-1])
        if asof - newest > pd.Timedelta(hours=STALE_GAP_H):      # longer than any plausible lull (99.99% of gaps < 25 h, 99.9% < 15 h)
            end = newest.floor("h")                              # => the CSV is behind: do not read the missing hours as a quiet stretch
        h = h[h.index < end]
        if len(h) < 24 * 14:
            raise ForecastError("not enough tweet history before the as-of time")
        last = h[h.index >= end - pd.Timedelta(days=p.level_days)]
        self.level = max(last.sum() / (len(last) / 24.0), p.level_floor)
        hod = h[h.index >= end - pd.Timedelta(days=p.hod_days)]
        hs = hod.groupby(hod.index.hour).sum().reindex(range(24), fill_value=0.0) + 1.0   # +1: no zero-share hours
        self.hod = (hs / hs.sum()).values
        dw = h[h.index >= end - pd.Timedelta(weeks=p.dow_weeks)]
        d = dw.groupby(dw.index.dayofweek).sum().reindex(range(7), fill_value=0.0) + 1.0
        self.dow = (d / d.mean()).values
        self.asof = asof
        self.data_end = end
        return self

    def exposure(self, start, end) -> float:
        """Expected tweets between two naive-ET timestamps under the profile (partial hours pro-rated)."""
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        if end <= start:
            return 0.0
        hours = pd.date_range(start.floor("h"), end.floor("h"), freq="h")
        lo = np.maximum(hours.values, np.datetime64(start))
        hi = np.minimum(hours.values + np.timedelta64(1, "h"), np.datetime64(end))
        frac = np.clip((hi - lo) / np.timedelta64(1, "h"), 0.0, 1.0)
        rate = self.level / 24.0 * self.dow[hours.dayofweek.values] * self.hod[hours.hour.values] * 24.0
        return float((rate * frac).sum())

    # ---- forecast ------------------------------------------------------------------------------------------
    def remaining(self, start, now, end, n_so_far: float) -> Tuple[float, float]:
        """(mean, variance) of tweets still to come between `now` and `end` given `n_so_far` counted since `start`."""
        p = self.p
        e_sofar, e_rem = self.exposure(start, now), self.exposure(now, end)
        if e_rem <= 0:
            return 0.0, 0.0
        a = p.prior_a
        n_p, e_p = max(n_so_far, 0.0) / p.phi, e_sofar / p.phi          # variance-inflated pseudo counts
        post_shape, post_rate = a + n_p, a + e_p
        lam, var_lam = post_shape / post_rate, post_shape / post_rate ** 2
        mu = lam * e_rem
        var = var_lam * e_rem ** 2 + p.phi * mu
        return float(mu), float(var)

    def bucket_probs(self, ranges: Sequence[Tuple[int, int]], start, now, end, n_so_far: int) -> np.ndarray:
        if not np.isfinite(n_so_far) or n_so_far < 0:
            raise ForecastError(f"bad tweet count {n_so_far!r}")
        mu, var = self.remaining(start, now, end, n_so_far)
        lo = np.array([r[0] for r in ranges], float) - n_so_far
        hi = np.array([min(r[1], 10 ** 5) for r in ranges], float) - n_so_far
        if mu < 1e-9:
            pr = ((lo <= 0) & (hi >= 0)).astype(float)
        else:
            if var <= mu * 1.0001:
                dist = stats.poisson(mu)
            else:
                r = mu * mu / (var - mu)
                dist = stats.nbinom(r, r / (r + mu))
            pr = dist.cdf(np.floor(hi)) - dist.cdf(np.ceil(lo) - 1.0)
            pr = np.where(hi < 0, 0.0, np.clip(pr, 0.0, 1.0))
        tot = pr.sum()
        if not np.isfinite(tot) or tot <= 1e-12:
            raise ForecastError("light model: zero probability mass over the buckets")
        return pr / tot


class LightPredictor:
    """Adapter used by the paper trader: owns the tweet history, reloads it when the CSV changes, answers `probs`."""
    name = "light"

    def __init__(self, csv_path: str, params: Optional[LightParams] = None, count_lag_h: float = 0.0):
        self.csv_path, self.params, self.count_lag_h = csv_path, params or LightParams(), count_lag_h
        self._mtime = None
        self.model: Optional[LightModel] = None
        self.updated = None
        self.last_mean_total: Optional[float] = None
        self.reload()

    def reload(self):
        import os
        m = os.path.getmtime(self.csv_path)
        if m != self._mtime:
            self.model = LightModel(load_times(self.csv_path), self.params)
            self._mtime = m

    @property
    def ready(self) -> bool:
        return self.model is not None and len(self.model.times) > 24 * 14

    def newest_tweet(self):
        return pd.Timestamp(self.model.times[-1])            # naive US/Eastern

    def probs(self, ranges, so_far, days_left=None, event=None, now=None, **_):
        """`event` gives start/end (UTC Timestamps), `now` the UTC Timestamp of the tick."""
        et = lambda t: pd.Timestamp(t).tz_convert("US/Eastern").tz_localize(None)
        start, end, now_et = et(event.start), et(event.end), et(now)
        self.model.fit(now_et)
        so = so_far
        if self.count_lag_h:                                  # the count we see is this many hours behind: add the expected unseen tweets
            so = so_far + self.model.exposure(now_et - pd.Timedelta(hours=self.count_lag_h), now_et)
        p = self.model.bucket_probs(ranges, start, now_et, end, int(round(so)))
        mu, _v = self.model.remaining(start, now_et, end, so)
        self.last_mean_total = float(so + mu)
        return p
