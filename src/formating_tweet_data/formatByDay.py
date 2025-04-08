import csv
import os
from datetime import datetime

# --- Configuration ---
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)  # Go up one level from src/formating to src

input_filename = os.path.join(src_dir, 'data', 'elonmusk_reformatted.csv')
output_filename = os.path.join(src_dir, 'data', 'elonmusk_tweet_counts.csv')

print(f"Starting script...")
print(f"Input file: {input_filename}")
print(f"Output file: {output_filename}")

tweet_counts = {}
processed_rows = 0
skipped_rows = 0

try:
    with open(input_filename, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        try:
            header = next(reader)  # Read header
            if header != ['id', 'text', 'created_at']:
                print(f"Warning: CSV header mismatch. Expected ['id', 'text', 'created_at'], got {header}. Proceeding anyway.")
        except StopIteration:
            print("Error: Input CSV file is empty.")
            exit()

        for i, row in enumerate(reader, start=1):
            if len(row) > 2:
                created_at_str = row[2]
                try:
                    # Extract the date part (YYYY:MM:DD)
                    date_part = created_at_str[:10]
                    if date_part in tweet_counts:
                        tweet_counts[date_part] += 1
                    else:
                        tweet_counts[date_part] = 1
                    processed_rows += 1
                except Exception as e:
                    print(f"Error processing date in row {i}: {e}. Row data: {row}")
                    skipped_rows += 1
            else:
                print(f"Skipping row {i}: Not enough columns. Row data: {row}")
                skipped_rows += 1

    # Write the tweet counts to the output CSV file
    with open(output_filename, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["Date", "Tweet Count"])  # Write header

        for date, count in tweet_counts.items():
            writer.writerow([date, count])

    print("-" * 30)
    print("Tweet count analysis complete.")
    print(f"Processed {processed_rows} rows.")
    print(f"Skipped {skipped_rows} rows.")
    print(f"Output saved to: {output_filename}")
    print("-" * 30)

except FileNotFoundError:
    print(f"Error: Input file not found at '{input_filename}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")