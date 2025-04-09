# Tweet Count Predictor

Predicts daily tweet counts using a moving average algorithm.

**Algo num 1: Moving Average Daily**

## Usage

```bash
python3 MA_daily.py [--window DAYS] [--file FILEPATH]
 ```
Markdown

# Tweet Count Predictor

Predicts daily tweet counts using a moving average algorithm.

**Algo num 1: Moving Average Daily**

## Usage

```bash
python3 MA_daily.py [--window DAYS] [--file FILEPATH]
```
Arguments:
--window DAYS: Number of days to use for the moving average (default: 7)
--file FILEPATH: Path to CSV file (default: data/elonmusk_daily_counts.csv)
Examples
Default 7-day average:

```bash
python3 MA_daily.py
```

14-day average:
```bash
python3 MA_daily.py --window 14
```

Optimal Window Size
7-14 days typically works best for tweet prediction.

Shorter windows (3-7 days) respond faster to recent trends.
Longer windows (14-30 days) provide smoother predictions.
The default 7 days offers a good balance between responsiveness and stability.


**Algo num 2: EWMA + Rate + Weekly Seasonality**

## Usage

```bash
python3 EWMA_daily.py [--ewma DAYS] [--rate DAYS] [--file FILEPATH]

```
Arguments:

--ewma DAYS: EWMA span for baseline trend (default: 7)
--rate DAYS: Window for recent rate of change calculation (default: 3)
--file FILEPATH: Path to CSV file (default: data/elonmusk_daily_counts.csv)

Examples
Default parameters:
```bash

python3 EWMA_daily.py
```

EWMA span of 14 days and rate window of 5 days:

```bash

python3 EWMA_daily.py --ewma 14 --rate 5
```

**Algo num 3: Moving Average Daily**

## Usage

```bash
python3 moving_average.py [--window DAYS] [--file FILEPATH] [--days COUNT]
 ```
Arguments:

--window DAYS: Number of days to use for moving average (default: 7)
--file FILEPATH: Path to CSV file (default: data/elonmusk_daily_counts.csv)
--days COUNT: Number of future days to predict (default: 1)

Example :
``` bash
python3 moving_average.py --window 10 --days 3
```

**Algo num 4: EWMA + Rate + Weekly Seasonality**

## Usage

```bash
python3 EWMA_daily.py [--ewma DAYS] [--rate DAYS] [--file FILEPATH] [--days COUNT]

```
Arguments:

--ewma DAYS: EWMA span for baseline trend (default: 7)
--rate DAYS: Window for recent rate of change calculation (default: 3)
--file FILEPATH: Path to CSV file (default: data/elonmusk_daily_counts.csv)
--days COUNT: Number of future days to predict (default: 1)

example:

``` bash

python3 EWMA_daily.py --ewma 14 --rate 5 --days 3

```

