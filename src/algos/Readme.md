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



**Algo num 5: Hybrid SARIMA + Seasonality**

## What the SARIMA Algorithm Does

SARIMA is a powerful time series forecasting method that extends the ARIMA (Autoregressive Integrated Moving Average) model to handle seasonal patterns in the data. It works by understanding the past patterns of the time series data (like trends and cycles) to forecast future values.

Here's a breakdown of the components of SARIMA:

* **Autoregressive (AR):** Uses past values of the time series to predict future values.
* **Integrated (I):** Makes the time series stationary (removes trends) by differencing the data.
* **Moving Average (MA):** Uses past forecast errors to predict future values.
* **Seasonal (SAR, SI, SMA):** These components account for recurring patterns within a specific period (e.g., weekly, monthly).

In this script, the SARIMA model is used with a specific order `(1, 1, 1)` and a seasonal order `(1, 1, 1, 7)`. The `7` in the seasonal order indicates a weekly seasonality (as there are 7 days in a week).

Additionally, this script incorporates:

* **Weekly Seasonality:** It calculates factors based on the average tweet count for each day of the week relative to the overall average. This helps adjust the predictions based on typical weekday behavior.
* **Monthly Seasonality:** Similarly, it calculates factors based on the average tweet count for each month of the year.

The final prediction is a result of the SARIMA model's output adjusted by these weekly and monthly seasonality factors.

## Usage

While the specific command-line arguments for this script weren't provided, it likely takes the data file as input and runs the SARIMA model to predict future tweet counts. Based on the output, a simple execution might look like:

```bash
python3 sarima.py

```





**Algo num 4: Random Forest**

## What the Random Forest Algorithm Does

Random Forest is a powerful machine learning algorithm that belongs to the ensemble learning family. It works by constructing multiple decision trees during training and outputs the mode of the classes (for classification) or the mean prediction (for regression) of the individual trees.

In this script, a Random Forest Classifier is used to predict whether Elon Musk will tweet on a particular day. The model is trained on historical tweet data, likely using features derived from the date, such as:

* **weekday:** The day of the week.
* **month:** The month of the year.
* **streak:** Possibly a measure of consecutive days with or without tweets.
* **month_cos:** Cosine transformation of the month (for cyclical representation).
* **month_sin:** Sine transformation of the month (for cyclical representation).

After predicting whether a tweet will occur (with a certain probability), the script also provides an "Expected" number of tweets for that day. The method for calculating this expected number isn't explicitly shown in the output but is likely based on historical averages or patterns associated with the predicted features.

## Usage

```bash
python3 randomForest.py [--days COUNT] [--file FILEPATH]

```
Markdown

# Tweet Prediction using Random Forest

Predicts whether Elon Musk will tweet on a given day and estimates the expected number of tweets using a Random Forest Classifier.

**Algo num 6: Random Forest**

## What the Random Forest Algorithm Does

Random Forest is a powerful machine learning algorithm that belongs to the ensemble learning family. It works by constructing multiple decision trees during training and outputs the mode of the classes (for classification) or the mean prediction (for regression) of the individual trees.

In this script, a Random Forest Classifier is used to predict whether Elon Musk will tweet on a particular day. The model is trained on historical tweet data, likely using features derived from the date, such as:

* **weekday:** The day of the week.
* **month:** The month of the year.
* **streak:** Possibly a measure of consecutive days with or without tweets.
* **month_cos:** Cosine transformation of the month (for cyclical representation).
* **month_sin:** Sine transformation of the month (for cyclical representation).

After predicting whether a tweet will occur (with a certain probability), the script also provides an "Expected" number of tweets for that day. The method for calculating this expected number isn't explicitly shown in the output but is likely based on historical averages or patterns associated with the predicted features.

## Usage

```bash
python3 randomForest.py [--days COUNT] [--file FILEPATH]
```
Arguments:

--days COUNT: The number of future days for which to predict tweet activity (default: 1, though in the example it was 14).
--file FILEPATH: Path to the CSV file containing the tweet history data (default: data/elonmusk_reformatted.csv).
Examples
Predicting for the next 7 days using the default data file:

``` bash

python3 randomForest.py --days 7
```


**Algo num 7: Historical Patterns**

## How to Use the Fixed Version:

To get predictions based on historical averages (long-term patterns) without the influence of recent trends:

```bash
python3 historical_pattern.py --date YYYY-MM-DD --no-trend

```
Markdown

# Tweet Count Predictor (Historical Patterns)

Predicts daily and hourly tweet counts based on historical averages, with options for trend adjustment and precision evaluation.

**Algo num 7: Historical Patterns**

## How to Use the Fixed Version:

To get predictions based on historical averages (long-term patterns) without the influence of recent trends:

```bash
python3 historical_pattern.py --date YYYY-MM-DD --no-trend
```

Replace YYYY-MM-DD with the specific date you want to predict for. This will use the long-term historical averages for each weekday instead of scaling them down based on recent activity.

Description
This script analyzes historical tweet data to predict future tweet counts. It calculates average tweet rates by weekday and hour of day to make predictions. Key features include:

Historical Averages: Predicts based on long-term historical tweet patterns.
Trend Adjustment: Optionally scales predictions based on the recent 7-day average tweet activity. This can be disabled using the --no-trend flag to rely solely on historical averages.
Same-Day Prediction: Accurately predicts tweet counts for the current date by considering the remaining hours.
Hourly Analysis: Provides a detailed breakdown of average tweet rates for all 24 hours of the day, sorted by activity.
Precision Evaluation: Compares predictions against actual past data using Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).
Precision Visualization: Generates a plot comparing predicted versus actual tweet counts for a visual representation of accuracy.


Options:

--file FILEPATH: Path to the reformatted CSV file (default: data/elonmusk_reformatted.csv).
--date YYYY-MM-DD: Target date to predict tweet count for.
--days COUNT: Number of future days to predict (default: 7).
--plot: Generate activity plots (daily and hourly distributions).
--precision: Evaluate prediction precision against past data. Requires --days-back.
--days-back N: Number of days back to evaluate precision (default: 14). Used with --precision.
--all-hours: Display average tweet counts for all 24 hours, sorted by activity.
--no-trend: Disable the adjustment of predictions based on the recent 7-day trend.