"""The light model's 48-hour momentum term: on by default, causal, off when history is stale, always fresh from the CSV."""
import os
import numpy as np
import pandas as pd
import pytest

from src.simulation.paper_trader.light_model import LightModel, LightParams, LightPredictor

START, NOW, END = pd.Timestamp("2026-11-10 12:00"), pd.Timestamp("2026-11-14 12:00"), pd.Timestamp("2026-11-17 12:00")


def history(hot_last_48h=1.0, until=NOW, days=60, per_hour=2):
    """per_hour tweets every hour for `days` days, the last 48 hours scaled by hot_last_48h; naive ET timestamps."""
    hours = pd.date_range(until - pd.Timedelta(days=days), until, freq="h", inclusive="left")
    out = []
    for h in hours:
        n = per_hour * (hot_last_48h if h >= until - pd.Timedelta(hours=48) else 1)
        out += [h + pd.Timedelta(minutes=int(60 * (k + .5) / n)) for k in range(int(round(n)))]
    return np.array(sorted(out), dtype="datetime64[ns]")


def total(times, momentum, so=190):
    m = LightModel(times, LightParams(momentum=momentum)).fit(NOW)
    mu, _ = m.remaining(START, NOW, END, so)
    return so + mu, m


def test_default_is_on():
    assert LightParams().momentum == 0.35


def test_off_means_no_pace():
    _, m = total(history(), 0.0)
    assert m.last_pace is None


def test_hot_last_48h_raises_forecast_and_cold_lowers_it():
    base, _ = total(history(1.0), 0.0)
    hot_off, _ = total(history(2.0), 0.0)
    hot_on, m = total(history(2.0), 0.35)
    cold_on, mc = total(history(0.5), 0.35)
    cold_off, _ = total(history(0.5), 0.0)
    assert m.last_pace > 1.3 and mc.last_pace < 0.8
    assert hot_on > hot_off + 5            # momentum pushes up when the last two days were hot
    assert cold_on < cold_off - 5          # ... and down when they were cold


def test_pace_is_clipped():
    _, m = total(history(8.0, per_hour=1), 0.35)
    assert m.last_pace == pytest.approx(2.0)


def test_stale_history_disables_momentum():
    t = history(1.0, until=NOW - pd.Timedelta(hours=30))      # newest tweet 30 h before "now": CSV behind, not a quiet stretch
    m = LightModel(t, LightParams(momentum=0.35)).fit(NOW)
    m.remaining(START, NOW, END, 190)
    assert m.last_pace is None


def test_future_tweets_do_not_leak_in():
    a = history(1.0)
    extra = history(1.0, until=NOW + pd.Timedelta(days=2), days=2, per_hour=6)       # tweets AFTER now (backtest data)
    b = np.sort(np.concatenate([a, extra]))
    pa = LightModel(a, LightParams()).fit(NOW).recent_pace(NOW)
    pb = LightModel(b, LightParams()).fit(NOW).recent_pace(NOW)
    assert pa == pytest.approx(pb)


def test_predictor_rereads_csv_and_reports_pace(tmp_path):
    from src.simulation.paper_trader.feeds import Event
    csv = tmp_path / "t.csv"

    def write(times):
        pd.DataFrame({"created_at": pd.DatetimeIndex(times).strftime("%Y:%m:%d:%H:%M:%S")}).to_csv(csv, index=False)

    write(history(1.0)); pred = LightPredictor(str(csv))
    class Ev: start = pd.Timestamp(START, tz="US/Eastern").tz_convert("UTC"); end = pd.Timestamp(END, tz="US/Eastern").tz_convert("UTC")
    now_utc = pd.Timestamp(NOW, tz="US/Eastern").tz_convert("UTC")
    ranges = [(i, i + 19) for i in range(0, 600, 20)]
    pred.probs(ranges, 190, event=Ev, now=now_utc); first = pred.last_mean_total
    write(history(2.0)); os.utime(csv, (os.path.getmtime(csv) + 5,) * 2)
    pred.reload(); pred.probs(ranges, 190, event=Ev, now=now_utc)
    assert pred.last_mean_total > first + 5 and pred.last_pace > 1.3          # new CSV content is used, not a cached copy
