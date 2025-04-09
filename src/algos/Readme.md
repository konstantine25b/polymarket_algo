# Tweet Count Predictor

Predicts daily tweet counts using a moving average algorithm.

**Algo num 1: Moving Average Daily**

## Usage

```bash
python3 moving_average_daily.py [--window DAYS] [--file FILEPATH]

Markdown

# Tweet Count Predictor

Predicts daily tweet counts using a moving average algorithm.

**Algo num 1: Moving Average Daily**

## Usage

```bash
python3 moving_average_daily.py [--window DAYS] [--file FILEPATH]
```
Arguments:
--window DAYS: Number of days to use for the moving average (default: 7)
--file FILEPATH: Path to CSV file (default: data/elonmusk_daily_counts.csv)
Examples
Default 7-day average:

```bash
python3 moving_average_daily.py
```

14-day average:
```bash
python3 moving_average_daily.py --window 14
```

Optimal Window Size
7-14 days typically works best for tweet prediction.

Shorter windows (3-7 days) respond faster to recent trends.
Longer windows (14-30 days) provide smoother predictions.
The default 7 days offers a good balance between responsiveness and stability.