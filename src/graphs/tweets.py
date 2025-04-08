import matplotlib.pyplot as plt
import pandas as pd
import os

# --- Configuration ---
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)  # Go up one level from src/formating to src
data_dir = os.path.join(src_dir, 'data')
output_dir = os.path.join(script_dir, 'graphs')  # Directory to save graphs
input_filename = os.path.join(data_dir, 'elonmusk_tweet_counts.csv')

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

print(f"Starting script to generate graphs from: {input_filename}")
print(f"Graphs will be saved to: {output_dir}")

try:
    # Read the CSV file into a Pandas DataFrame
    df = pd.read_csv(input_filename)
    df['Date'] = pd.to_datetime(df['Date'], format='%Y:%m:%d')

    # 1. Time Series Plot of Tweet Count
    plt.figure(figsize=(12, 6))
    plt.plot(df['Date'], df['Tweet Count'], marker='o', linestyle='-')
    plt.title('Daily Tweet Count Over Time')
    plt.xlabel('Date')
    plt.ylabel('Tweet Count')
    plt.grid(True)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    filename_timeseries = os.path.join(output_dir, 'tweet_count_time_series.png')
    plt.savefig(filename_timeseries)
    plt.close()  # Close the figure to free up memory

    # 2. Bar Chart of Tweet Count
    plt.figure(figsize=(12, 6))
    plt.bar(df['Date'], df['Tweet Count'])
    plt.title('Daily Tweet Count')
    plt.xlabel('Date')
    plt.ylabel('Tweet Count')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    filename_barplot = os.path.join(output_dir, 'tweet_count_bar_plot.png')
    plt.savefig(filename_barplot)
    plt.close()

    # 3. Rate of Change of Tweet Count
    df['Rate of Change'] = df['Tweet Count'].diff()

    plt.figure(figsize=(12, 6))
    plt.plot(df['Date'][1:], df['Rate of Change'][1:], marker='o', linestyle='-')
    plt.title('Daily Rate of Change in Tweet Count')
    plt.xlabel('Date')
    plt.ylabel('Change in Tweet Count')
    plt.grid(True)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    filename_rate_of_change = os.path.join(output_dir, 'tweet_count_rate_of_change.png')
    plt.savefig(filename_rate_of_change)
    plt.close()

    # 4. Rolling Average of Tweet Count (to visualize trend)
    df['Rolling Average'] = df['Tweet Count'].rolling(window=7).mean()

    plt.figure(figsize=(12, 6))
    plt.plot(df['Date'], df['Tweet Count'], label='Daily Count', alpha=0.7)
    plt.plot(df['Date'], df['Rolling Average'], label='7-Day Rolling Average', color='red')
    plt.title('Daily Tweet Count with 7-Day Rolling Average')
    plt.xlabel('Date')
    plt.ylabel('Tweet Count')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    filename_rolling_average = os.path.join(output_dir, 'tweet_count_rolling_average.png')
    plt.savefig(filename_rolling_average)
    plt.close()

    print(f"Graphs have been generated and saved to: {output_dir}")

except FileNotFoundError:
    print(f"Error: Input file not found at '{input_filename}'. Please ensure the file exists.")
except Exception as e:
    print(f"An error occurred: {e}")