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
pip install -r requirements.txt          # ~10-15 min (torch, jax, prophet ...)
playwright install chromium              # headless browser used to read Polymarket's tweet count

python -m pytest src/simulation/paper_trader/tests -q      # expect: 15 passed
```
The first forecast downloads the TimesFM weights (~800 MB, one time), so the very first start can take a few minutes.
No `.env` / wallet / API keys are needed for paper trading.

## 2. Run

```bash
cd polymarket_algo && source venv/bin/activate
caffeinate -i python -m src.simulation.paper_trader --run-name live40 --bankroll 40 --start-after-days 0
```
* `caffeinate -i` stops macOS from sleeping (the loop pauses while the Mac sleeps).
* `--run-name` is the folder `src/simulation/runs/<name>/`. Same name = **resume** (cash, positions, logs are kept; `--bankroll` is then ignored). New name = fresh start.
* **Never use `--fresh` on a real run**: it deletes that run's logs and state.
* Stop with Ctrl-C. Run the same command again to resume.
* To run unattended: `tmux new -s paper` then the command, detach with Ctrl-b d (re-attach: `tmux attach -t paper`).

## 3. What is happening

The loop wakes every **10 minutes** (:00, :10, :20 ...). On each wake-up it:
1. fetches all order books and Polymarket's tweet count, and compares the count with our own tweet database;
2. turns the latest forecast into a probability per bucket (recomputed from the live count and days left);
3. **sell check** on every open position - sells the whole position at the bid if our probability < 4% **or** the market bid > our probability;
4. **buy decision, once per hour**: candidates are buckets with our probability >= 8%, market ask >= 3% and our probability > ask + 1.0 point;
   one is drawn at random (weight = edge) and $1 (fee included) is bought from the real book. No candidate = no buy (this is common);
5. writes logs/charts and saves state.

About once an hour, in a separate process, it downloads the XTracker tweet export, merges it into `src/data/elonmusk_reformatted.csv`
and re-runs the ensemble (Neural Prophet, Facebook Prophet, TimesFM, Basic Prophet, moving average, linear trend). The ensemble's total becomes a
daily rate; a calibrated Gamma shape (x1.15 bias correction) gives the bucket probabilities.
Every buy and sell pays Polymarket's taker fee `shares x 0.05 x price x (1 - price)` (read from the market's own `feeSchedule`).
When the market ends it waits for the resolution, pays winners $1 per share, books the losses and rolls to the next weekly market.

## 4. Monitor - is everything alright?

**One command** (exit code 0 healthy, 1 warnings, 2 critical):
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
| `config_history.jsonl`, `state.json` | arguments at every start; resume point |
| `charts_archive/` | hourly copies of both charts |

## 5. Troubleshooting

| Symptom (from `status`) | Meaning / fix |
|---|---|
| `no run.lock` / `process dead` | Stopped or crashed. Start the same command again - it resumes. |
| `last tick ... older than 25 min` while running | Stuck network/browser call. Look at `paper_trader.log`; Ctrl-C and restart. |
| `tweet count source: local_csv` | Polymarket page could not be read. `playwright install chromium`; check internet. Trading continues on our own data. |
| `order books 0/25` | Network down, or the market ended (it rolls to the next weekly market by itself). |
| `last ensemble forecast ... min ago` too old | Model worker failing: grep `model worker` in `paper_trader.log`; see `model_logs/`. The bot keeps using the last forecast. |
| "another paper trader is already running" | Another process uses that run folder. Use `status`; stop it or pick another `--run-name`. |
| Mac asleep overnight | Use `caffeinate -i`; a sleeping Mac pauses the loop (nothing breaks, ticks are simply missed). |

## 6. After the run

```bash
python -m src.simulation.paper_trader.report --run-name live40     # prints and saves report.txt
```
Result, drawdown, trades by bucket and sell reason, how often a buy candidate existed, data quality, uptime gaps, our probability vs the market.
Keep in mind: backtests of these rules averaged roughly +$8/week per $30 *with* fees but the median week lost, and about 1 week in 4 lost nearly everything.
One live week is a single sample.

## 7. Paste-ready instruction for a bot / assistant

> Install and run the paper trader from branch `fix/scraper-year-ensemble-dryrun` of github.com/konstantine25b/polymarket_algo, following `src/simulation/paper_trader/RUNBOOK.md` sections 1-2 (Python 3.11 venv, `pip install -r requirements.txt`, `playwright install chromium`, run the 15 tests).
> Start it in tmux with: `caffeinate -i python -m src.simulation.paper_trader --run-name live40 --bankroll 40 --start-after-days 0` and keep it running.
> Every 15 minutes run `python -m src.simulation.paper_trader.status --run-name live40`. Exit 0: reply "healthy" with the account line. Exit 1: report the WARN lines. Exit 2: restart with the exact same command (never `--fresh`, never change the run name) and report what `paper_trader.log` shows.
> Never edit files, never delete the run folder, never send real orders (the bot cannot). When asked for results run `python -m src.simulation.paper_trader.report --run-name live40` and summarise it.
