# Paper trader - runbook (install, run, monitor)

**Branch:** `fix/scraper-year-ensemble-dryrun` of `https://github.com/konstantine25b/polymarket_algo`
**What it is:** a paper-trading bot. It reads the *real* Polymarket order books for the weekly "Elon Musk # tweets"
market and trades fake money with fixed rules and real taker fees. It never sends an order and needs no wallet.

## 1. Install (once)

```bash
git clone https://github.com/konstantine25b/polymarket_algo.git
cd polymarket_algo
git checkout fix/scraper-year-ensemble-dryrun

python3.11 -m venv venv                  # Python 3.11 is required (3.9 cannot install the pinned dependencies)
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-light.txt    # ~1-2 min: enough for the default 'light'/'fresh' strategies
# pip install -r requirements.txt        # ~10-15 min (torch, jax, prophet ...): ONLY for --strategy legacy
playwright install chromium              # headless browser used to read Polymarket's tweet count

python -m pytest src/simulation/paper_trader/tests -q      # must finish with 0 failures (CI runs it on every push)
```
The first forecast downloads the TimesFM weights (~800 MB, one time), so the very first start can take a few minutes.
No `.env` / wallet / API keys are needed for paper trading.

## 2. Run

**macOS** (laptop):
```bash
cd polymarket_algo && source venv/bin/activate
caffeinate -i python -m src.simulation.paper_trader --run-name live40 --bankroll 40 --start-after-days 0 --backup-dir ~/paper_backup
```
**Linux** (no `caffeinate`; run under a supervisor, see `deploy/paper-trader.service` - systemd user unit with restart backoff and a crash-loop limit):
```bash
python -m src.simulation.paper_trader --run-name live40 --bankroll 40 --start-after-days 0 --backup-dir /mnt/other-disk/paper_backup
```
* `caffeinate -i` (macOS only) stops the Mac from sleeping (the loop pauses while it sleeps; the timer is monotonic-safe after resume).
* `--backup-dir` receives a checksummed checkpoint (state, forecast, full ledger) every tick and the tweet dataset after each refresh. Point it OUTSIDE the checkout. If a run folder is lost, starting again with the same `--run-name` and `--backup-dir` restores from the newest valid checkpoint; if state is lost and nothing can be restored the bot **refuses** to start a same-name account (use `--allow-new-state` to start over on purpose).
* Do not `tee` the output into `console.log` - the app writes that file itself (tee-ing doubles every line). Send stdout/stderr to the supervisor's journal instead.
* `--run-name` is the folder `src/simulation/runs/<name>/`. Same name = **resume** (cash, positions, logs are kept; `--bankroll` is then ignored). New name = fresh start.
* **Never use `--fresh` on a real run**: it deletes that run's logs and state.
* Stop with Ctrl-C. Run the same command again to resume.
* To run unattended: `tmux new -s paper` then the command, detach with Ctrl-b d (re-attach: `tmux attach -t paper`).

## 2b. Strategies (`--strategy`, default `light`)

| | `light` (default, backtested) | `legacy` (original) |
|---|---|---|
| Model | `light_model.py`: hour-of-day x day-of-week profile + Gamma-Poisson weekly level, negative-binomial remainder. ~25 ms, ~160 MB, no subprocess, no model downloads | Prophet/NeuralProphet/TimesFM ensemble in a worker process (GBs, minutes) |
| Buys | only the model's **top-2 buckets**, prob >= 10%, ask >= 2c, edge >= 2pt **after the buy fee**, best net edge first, **never add to a held bucket**, only from day 4 of the market | edge > 1pt over the ask, random pick, unlimited adds, from day 2 |
| Exits | none - hold to settlement (selling early did not help in the backtest) | sell when prob < 4% or bid > prob |
| Caps | 25% of equity per bucket, 80% per event | same |

Every preset value can be overridden with its flag (`--top-k`, `--max-adds`, `--min-pred`, `--start-after-days`, `--sell-below`, ...).
`--stake` is $1 by default; results scale linearly with the stake (the caps are fractions of equity).
Backtest evidence, assumptions and caveats: `src/simulation/backtest/RESULTS.md` (re-create with `python -m src.simulation.backtest.data`,
`...table`, `...report`). **The measured edge depends on knowing the tweet count in near real time**: it shrinks from +$2.4 to ~+$0.8 per
$40-week when the count is 1+ hours behind, and it is small and uncertain either way. `data_log.csv` shows Polymarket's count vs our database each
tick - use it to measure the real lag, and pass `--count-lag-h N` if the count runs N hours behind.

## 3. What is happening

The loop wakes every **10 minutes** (:00, :10, :20 ...). On each wake-up it:
1. fetches all order books and Polymarket's tweet count, and compares the count with our own tweet database;
2. turns the latest forecast into a probability per bucket (recomputed from the live count and days left);
3. **sell check** on every open position - sells the whole position at the bid if our probability < 4% **or** the market bid > our probability;
4. **buy decision, once per hour**: candidates are buckets with our probability >= 8%, market ask >= 3% and our probability > ask + 1.0 point;
   one is drawn at random (weight = edge) and $1 (fee included) is bought from the real book. No candidate = no buy (this is common);
5. writes logs/charts and saves state.

(`legacy` strategy) About once an hour, in a separate process, it downloads the XTracker tweet export, merges it into `src/data/elonmusk_reformatted.csv`
and re-runs the ensemble (Neural Prophet, Facebook Prophet, TimesFM, Basic Prophet, moving average, linear trend). The ensemble's total becomes a
daily rate; a calibrated Gamma shape (x1.15 bias correction) gives the bucket probabilities.
Every buy and sell pays Polymarket's taker fee `shares x 0.05 x price x (1 - price)` (read from the market's own `feeSchedule`).
When the market ends it waits for the resolution, pays winners $1 per share, books the losses and rolls to the next weekly market.

## 4. Monitor - is everything alright?

**One command** (exit code 0 healthy, 1 warnings, 2 critical; liveness comes from a kernel lock plus `heartbeat.json`, not from a PID):
```bash
python -m src.simulation.paper_trader.status --run-name live40
```
Healthy looks like: process running, last tick < 25 min ago, order books 25/25, tweet count source `polymarket`, last ensemble forecast < 150 min ago,
0 errors in the last 60 min, cash never negative.

Live view (macOS has no `watch`):
```bash
while true; do clear; python -m src.simulation.paper_trader.status --run-name live40; sleep 60; done
tail -f src/simulation/runs/live40/console.log          # exactly what the bot prints
tail -f src/simulation/runs/live40/paper_trader.log     # timestamped log incl. warnings/errors
open  src/simulation/runs/live40/equity.png  src/simulation/runs/live40/market.png     # rewritten every tick
```

Files in `src/simulation/runs/live40/` (nothing is ever rotated or deleted):

| File | Content |
|---|---|
| `console.log`, `paper_trader.log` | screen output / timestamped log |
| `trades.csv` | every buy, sell, settlement: price, fee, our probability, ask/bid, draw probability, realised P&L |
| `decisions.csv` | every hourly buy decision with all candidates |
| `snapshots.csv` | every bucket every tick: our probability, bid/ask, depth, holdings |
| `equity.csv`, `data_log.csv`, `forecasts.csv` | equity curve; tweet counts and data health; every ensemble run |
| `model_logs/` | the ensemble's full training output per run |
| `config_history.jsonl`, `state.json`, `forecast_state.json` | arguments at every start; resume points (account / last applied forecast) |
| `checkpoints/`, `heartbeat.json`, `exit_status.json` | checksummed snapshots; loop liveness; why the process last exited (signal, uncaught exception + traceback) |
| `charts_archive/` | hourly copies of both charts |

## 5. Troubleshooting

| Symptom (from `status`) | Meaning / fix |
|---|---|
| `no run.lock` / `process dead` | Stopped or crashed. Start the same command again - it resumes. |
| `last tick ... older than 25 min` while running | Stuck network/browser call. Look at `paper_trader.log`; Ctrl-C and restart. |
| `tweet count source: local_csv` | Polymarket page could not be read. `playwright install chromium`; check internet. Trading continues on our own data. |
| `order books 0/25` | Network down, or the market ended (it rolls to the next weekly market by itself). |
| `last ensemble forecast ... min ago` too old | Refresh or model worker failing (retries back off 5 -> 60 min): grep `forecast attempt failed` in `paper_trader.log`; full worker stderr per attempt is in `model_logs/attempt_*.stderr`. Past `--model-stale-min` (150) **new buys are blocked**; exits keep working on the last valid forecast. |
| `blocked: tweet data is stale` in decisions.csv | Our tweet database is >30 tweets behind Polymarket (XTracker refresh failing). Buys resume after a successful refresh. |
| "another paper trader is already running" | Another process uses that run folder. Use `status`; stop it or pick another `--run-name`. |
| Mac asleep overnight | Use `caffeinate -i` (macOS); a sleeping Mac pauses the loop (nothing breaks, ticks are simply missed). |

## 6. After the run

```bash
python -m src.simulation.paper_trader.report --run-name live40     # prints and saves report.txt
```
Result, drawdown, trades by bucket and sell reason, how often a buy candidate existed, data quality, uptime gaps, our probability vs the market.
Keep in mind: backtests of these rules averaged roughly +$8/week per $30 *with* fees but the median week lost, and about 1 week in 4 lost nearly everything.
One live week is a single sample.

## 7. Paste-ready instruction for a bot / assistant (Grok etc.)

````text
TASK: install, run and monitor a PAPER-trading bot (fake money, no wallet, no real orders). Do exactly this, nothing else.

1) INSTALL (Linux or macOS, Python 3.11 required)
   git clone https://github.com/konstantine25b/polymarket_algo.git
   cd polymarket_algo
   git checkout feat/light-model-backtest
   python3.11 -m venv venv && source venv/bin/activate
   pip install --upgrade pip && pip install -r requirements-light.txt      # ~1-2 min, do NOT use requirements.txt
   python -m playwright install --with-deps chromium                        # Linux needs sudo/apt for the --with-deps part; macOS: drop --with-deps
   python -m pytest src/simulation/paper_trader/tests -q                    # must show 0 failed (a few skipped is normal)
   Quick check (10 s, safe, places nothing):
   python -m src.simulation.paper_trader --run-name check_now --bankroll 40 --strategy fresh --once
   It must print "polymarket count N | our csv count N ... 26/26 order books" and "cash $40.00". If it errors, report the full error and stop.

2) RUN (keep it running 24/7; it is a loop that ticks every 10 minutes)
   tmux new -s paper            # (Linux alternative: the systemd unit in src/simulation/paper_trader/deploy/paper-trader.service)
   source venv/bin/activate
   python -m src.simulation.paper_trader --run-name week_nov3 --bankroll 40 --strategy fresh --backup-dir ~/paper_backup
   (macOS only: put `caffeinate -i` in front.)  Detach: Ctrl-b d.  Re-attach: tmux attach -t paper.
   It trades the Elon Musk weekly tweet-count market, rolls to the next one by itself, and resumes from saved state if restarted.
   Rules of the road: NEVER use --fresh, NEVER change --run-name, NEVER delete src/simulation/runs/, NEVER edit any file, never touch a run called live40.

3) MONITOR - every 15 minutes run:
   python -m src.simulation.paper_trader.status --run-name week_nov3
   Exit code 0 = healthy: reply "healthy" plus the ACCOUNT line (cash, equity, open positions).
   Exit code 1 = warnings: report the WARN lines word for word.
   Exit code 2 = critical. First look at the first status line:
                 - "process running" but "last tick ... min ago" > 25: the process is alive. First check whether the computer/VM was
                   suspended (the monitor itself missing checks is a sign). Wait 10 minutes and run status again - after a pause it
                   resumes by itself. If it is STILL stale: find the pid (cat src/simulation/runs/week_nov3/run.lock), kill that pid
                   (kill <pid>; only kill -9 if it ignores a normal kill after 30 s), then start it again with the exact command from step 2.
                   (Starting a second copy while the first is alive just prints "another paper trader owns ..." and exits - that is correct.)
                 - "no run.lock" / "no process holds it": the process is dead. Restart with the EXACT same command from step 2 (it resumes).
                 Either way wait 2 minutes, run status again, and report what tail -50 src/simulation/runs/week_nov3/paper_trader.log says.
   Healthy looks like: "process running", last tick < 25 min ago, order books 25/25 (or all of them), tweet count source polymarket,
   0 errors in the last 60 min, heartbeat < 15 min.

   Also check once a day and report:
   - tail -5 src/simulation/runs/week_nov3/data_log.csv : the "diff" column (Polymarket count minus our tweet database). It should stay small
     (|diff| <= 10). If |diff| > 10 for 6 ticks in a row, report it - the strategy assumes a real-time tweet count.
   - tail -5 src/simulation/runs/week_nov3/decisions.csv : the "result" column says why it bought or did not buy ("no candidate" is normal;
     "blocked: ..." means data is stale - report it).
   - src/simulation/runs/week_nov3/trades.csv : list every BUY/SELL since last report (bucket, shares, price, reason).
   - cat src/simulation/runs/week_nov3/exit_status.json (only if it was restarted) : why it stopped.
   NOTE: for the first days of each market it will correctly make NO trades - buying only starts on day 4 of a market.

4) WHEN ASKED FOR RESULTS: python -m src.simulation.paper_trader.report --run-name week_nov3  and summarise it (equity vs $40, realised P&L, fees, trades).
````
