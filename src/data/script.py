# python3 script.py

import pandas as pd
import matplotlib.pyplot as plt
import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Log the current working directory
current_directory = os.getcwd()
logging.info(f"Current working directory: {current_directory}")

# Check if the file exists in the current directory
file_path = 'elonmusk.csv'
if not os.path.exists(file_path):
    logging.error(f"File not found: {file_path}. Please ensure the file is in the same directory as the script.")
    exit()

# Load the CSV data, specifying the header and correct column order
try:
    df = pd.read_csv(file_path, header=0, names=['ID', 'Text', 'Timestamp'], quotechar='"', usecols=[0, 1, 2])
    logging.info(f"Successfully loaded data from {file_path}")
except Exception as e:
    logging.error(f"Error reading CSV file: {e}")
    exit()

# Correct the year in the Timestamp column
correct_year = 2025

def correct_timestamp(timestamp_str):
    """Corrects the year in the timestamp string."""
    if isinstance(timestamp_str, str):
        try:
            dt_obj = datetime.datetime.strptime(timestamp_str, '%b %d, %I:%M:%S %p EDT')
            return dt_obj.replace(year=correct_year)
        except ValueError:
            return None  # Or handle the error as appropriate
    return None

df['Timestamp'] = df['Timestamp'].apply(correct_timestamp)

# Convert Timestamp to datetime objects with the correct format, handling errors
try:
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], utc=True, errors='coerce')
    logging.info("Successfully converted 'Timestamp' column to datetime objects (invalid dates set to NaT).")
except Exception as e:
    logging.error(f"Error converting 'Timestamp' column: {e}")
    exit()

# Drop rows with invalid timestamps (NaT)
df.dropna(subset=['Timestamp'], inplace=True)
logging.info(f"Dropped {df.isnull().sum()['Timestamp']} rows with invalid timestamps.")

# Daily Tweet Count
try:
    daily_counts = df.groupby(df['Timestamp'].dt.date).size().reset_index(name='Daily Count')
    daily_counts['Timestamp'] = pd.to_datetime(daily_counts['Timestamp'])
    logging.info("Successfully calculated daily tweet counts.")
except Exception as e:
    logging.error(f"Error calculating daily tweet counts: {e}")
    exit()

# Weekly Tweet Count
try:
    weekly_counts = df.groupby(df['Timestamp'].dt.isocalendar().week).size().reset_index(name='Weekly Count')
    weekly_counts['Week'] = weekly_counts.index
    logging.info("Successfully calculated weekly tweet counts.")
except Exception as e:
    logging.error(f"Error calculating weekly tweet counts: {e}")
    exit()

# Calculate Daily Posting Rate (Tweets per Day)
try:
    daily_counts['Day'] = daily_counts['Timestamp'].dt.date
    daily_counts['Posting Rate'] = daily_counts['Daily Count']
    logging.info("Successfully calculated daily posting rate.")
except Exception as e:
    logging.error(f"Error calculating daily posting rate: {e}")
    exit()

# Plot Daily Posting Rate
try:
    plt.figure(figsize=(12, 6))
    plt.plot(daily_counts['Timestamp'], daily_counts['Posting Rate'], marker='o', linestyle='-')
    plt.title('Daily Tweet Posting Rate')
    plt.xlabel('Date')
    plt.ylabel('Number of Tweets')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('daily_tweet_rate.png')  # Save the plot
    logging.info("Successfully created and saved daily tweet posting rate chart.")
    plt.show()
except Exception as e:
    logging.error(f"Error creating daily posting rate chart: {e}")

# Plot Weekly Tweet Count
try:
    plt.figure(figsize=(12, 6))
    plt.plot(weekly_counts['Week'], weekly_counts['Weekly Count'], marker='o', linestyle='-')
    plt.title('Weekly Tweet Count')
    plt.xlabel('Week')
    plt.ylabel('Number of Tweets')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('weekly_tweet_count.png')  # Save the plot
    logging.info("Successfully created and saved weekly tweet count chart.")
    plt.show()
except Exception as e:
    logging.error(f"Error creating weekly tweet count chart: {e}")

# Save the daily and weekly data to new CSV files
try:
    daily_counts.to_csv('daily_tweet_counts.csv', index=False)
    weekly_counts.to_csv('weekly_tweet_counts.csv', index=False)
    logging.info("Successfully saved daily and weekly tweet counts to CSV files.")
except Exception as e:
    logging.error(f"Error saving data to CSV files: {e}")

print("Daily and weekly tweet counts have been saved to 'daily_tweet_counts.csv' and 'weekly_tweet_counts.csv'. Charts of daily posting rate and weekly tweet counts are also displayed (and saved as .png files).")