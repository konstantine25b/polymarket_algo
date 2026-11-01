# Paper trader (exact paper trading of the tweet-count strategy)

Trades **fake money against the real Polymarket order books** with your exact rules, real taker fees,
real minimum sizes, persistent state, CSV logs and charts. It never stops by itself.

```bash
source venv/bin/activate

# LIVE - runs forever, resumes where it stopped if you restart it (Ctrl-C to stop)
python -m src.simulation.paper_trader --run-name paper1

# REPLAY a finished weekly market through the same engine in seconds (testing / validation)
python -m src.simulation.paper_trader --run-name replay1 --replay elon-musk-of-tweets-october-16-october-23-2026

# one live tick and exit (smoke test)
python -m src.simulation.paper_trader --run-name smoke --once --start-after-days 0

# tests
python -m pytest src/simulation/paper_trader/tests -q
```

## The strategy (defaults = the rules you specified)

| Rule | Default | Flag |
|---|---|---|
| Bankroll | $30 | `--bankroll` |
| Buy | one `$1` buy per hour (fee included, min $1) | `--stake`, `--buy-every` |
| Our probability at least | 8% | `--min-pred` |
| Market ask at least | 3% | `--min-mkt` |
| Our probability above the ask by more than | 1.0 point | `--min-edge` |
| Which bucket | **one at random**, probability proportional to its edge (pred - ask) | |
| Sell (whole position, at the bid) | our probability < 4% **or** market bid > our probability | `--sell-below`, `--no-bid-sell` |
| Sell check | every 10 minutes | `--sell-every` |
| No buying until | 2 days after a market opens | `--start-after-days` |

## Fees and order realism
* **Taker fee** `shares * rate * price * (1 - price)` in USDC, rounded to 5 decimals; `rate` and `exponent`
  are read from each market's own `feeSchedule` (Elon tweet markets: 0.05, exponent 1, taker-only).
  Charged on every buy and every sell (all orders are market orders = takers). No fee on redemption.
  A $1 buy of a 5% bucket pays ~4.75% of the stake in fees.
* Orders **walk the real book** (best price first, real depth). Buys spend `$stake` *including* the fee.
  A buy is rejected if the average fill is worse than the best ask by more than `--max-slippage` (1 point).
* Share sizes are floored to 2 decimals. Sells of any size are allowed (only a position under 0.01 shares, or an empty bid side, can't be sold). Buys are at least $1 (`--stake`).
* Mark-to-market equity = cash + positions sold at the **bid, net of the sell fee**.

## Predictions (`--pred-source`)
* `calibrated` (default - the version that was backtested): the ensemble's forecast total -> daily rate for the
  rest of the market, x `--b` (1.15), spread as a Gamma distribution (cv 0.30 with >=4 days left, else 0.45),
  recomputed every tick from the live tweet count. The ensemble is re-run **hourly in a separate process**.
* `ensemble`: the ensemble's own bucket probabilities (these lost money in the backtest).

## Data it fetches (and logs)
Every tick: all order books, Polymarket's own tweet count for the event (the resolution source), our own tweet
CSV count as a cross-check/fallback. Every hour: XTracker export -> merged into `src/data/elonmusk_reformatted.csv`
-> ensemble re-run. After a market ends it polls until it is resolved, pays out, and rolls to the next weekly market.

## Install / run / monitor
See **RUNBOOK.md** (install, exact run command, `status` health check, troubleshooting, paste-ready bot instructions).

## After the run
```bash
python -m src.simulation.paper_trader.report --run-name live40     # prints + writes report.txt
```

## Output (in `src/simulation/runs/<run-name>/`)  - nothing is ever rotated or deleted (do not use `--fresh` on a real run)
`state.json` (resume point) - `trades.csv` (every buy/sell/settle with prediction, ask/bid, fee, realised P&L, draw probability) -
`decisions.csv` (every hourly buy decision with all candidates) - `equity.csv` - `data_log.csv` (tweet counts, order books, errors) -
`forecasts.csv` - `snapshots.csv` (every bucket, every tick: our prob, bid/ask, depth, holdings) - `config_history.jsonl` (args at every start) - `console.log` (an exact copy of what was printed on screen) - `model_logs/` (the ensemble's full training output for every run) - `paper_trader.log` (append-only) - `summary.txt` - `report.txt` - `equity.png`, `market.png` (rewritten every tick) - `charts_archive/` (hourly copies).

## What is exact and what is not
Exact: fee formula/schedule, book depth, sizes, accounting (tested), restart safety, rule thresholds.
Approximate: fills assume the order reaches the book you just read (no latency); no maker orders/rebates; the
ensemble and tweet count refresh on their own schedules (hourly / every tick). Replay uses a synthetic book
(mid +/- half spread, unlimited depth), so replay results are optimistic - judge the strategy from the live run.
