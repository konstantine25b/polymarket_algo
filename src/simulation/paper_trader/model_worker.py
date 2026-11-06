"""
Runs the ensemble once, in its own process, and writes the forecast to a JSON file.

    python -m src.simulation.paper_trader.model_worker --start "2026-10-30 12:00:00" \
        --end "2026-11-06 12:00:00" --now "2026-11-01 07:30:00" --out forecast.json

Start/end/now are US/Eastern wall-clock times. The ensemble reads the market window from
constants and from several data-processor modules that imported it by value, so all of them are
patched here before the predictor is built. A crash in here cannot take the trading loop down.
"""
import argparse
import contextlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--now", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--slug", default=None, help="event slug this forecast is for (echoed into the output)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--data-path", default=None)
    ap.add_argument("--log-out", default=None, help="file that receives the ensemble's full (very chatty) output")
    args = ap.parse_args()

    import constants
    constants.POLYMARKET_START_TIME, constants.POLYMARKET_END_TIME = args.start, args.end
    import prediction_algos.facebook_prophet.data_processor as a
    import prediction_algos.neural_prophet.data_processor as b
    import prediction_algos.timesfm.data_processor as c
    import prediction_algos.ensemble.data_processor as d
    for m in (a, b, c, d):
        m.POLYMARKET_START_TIME, m.POLYMARKET_END_TIME = args.start, args.end
    from prediction_algos.ensemble import EnsembleTweetPredictor

    now = constants.ET_TIMEZONE.localize(datetime.strptime(args.now, "%Y-%m-%d %H:%M:%S"))
    chatter, dist_buf, top_buf = io.StringIO(), io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(chatter):          # the ensemble prints a lot (training progress etc.) - keep it in a file
        predictor = EnsembleTweetPredictor(data_path=args.data_path, save_plots=False, random_seed=args.seed)
        summary = predictor.generate_predictions(now)
    with contextlib.redirect_stdout(dist_buf):
        predictor.print_individual_algorithm_distributions(summary)
    with contextlib.redirect_stdout(top_buf):
        predictor.print_prediction_summary(summary)
    if args.log_out:
        os.makedirs(os.path.dirname(args.log_out), exist_ok=True)
        with open(args.log_out, "w") as f:
            f.write(chatter.getvalue() + "\n" + dist_buf.getvalue() + "\n" + top_buf.getvalue())
    contrib = summary["model_contributions"]
    lines = [f"ENSEMBLE FORECAST  (as of {args.now} ET, market ends {args.end} ET)", ""]
    names = {"neural_prophet": "Neural Prophet", "facebook_prophet": "Facebook Prophet", "timesfm": "TimesFM",
             "basic_prophet": "Basic Prophet", "moving_average": "Moving average", "linear_trend": "Linear trend"}
    for k, v in contrib.items():
        lines.append(f"  {names.get(k, k):18s} predicts {v['prediction']:7.1f} tweets total   (weight {v['weight'] * 100:4.1f}%)")
    lines += ["", f"  ENSEMBLE total      {summary['total_predicted']:7.1f}   | tweets so far {summary['current_tweets']} | "
                  f"time left {summary['time_remaining'].total_seconds() / 86400:.2f} days"]
    report = "\n".join(lines) + "\n\n" + dist_buf.getvalue().strip("\n")
    out = {
        "event_slug": args.slug,
        "generated_for": args.now,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_start": args.start, "window_end": args.end,
        "total_predicted": float(summary["total_predicted"]),
        "current_tweets": int(summary["current_tweets"]),
        "time_remaining_days": summary["time_remaining"].total_seconds() / 86400.0,
        "frames": {k: float(v["probability"]) for k, v in summary["predictions_by_frame"].items()},
        "model_contributions": {k: float(v["prediction"]) for k, v in contrib.items()},
        "report": report,
        "verbose_log": args.log_out,
    }
    tmp = args.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    os.replace(tmp, args.out)


if __name__ == "__main__":
    main()
