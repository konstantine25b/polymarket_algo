import csv
import os
from datetime import datetime

# --- Configuration ---
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)  # Go up one level from src/formating to src

input_filename = os.path.join(src_dir, 'data', 'elonmusk.csv')
output_filename = os.path.join(src_dir, 'data', 'elonmusk_reformatted.csv')

print(f"Starting script...")
print(f"Input file: {input_filename}")
print(f"Output file: {output_filename}")

output_data = []
processed_rows = 0
skipped_rows = 0

try:
    with open(input_filename, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        try:
            header = next(reader)  # Read header
            if header != ['id', 'text', 'created_at']:
                print(f"Warning: CSV header mismatch. Expected ['id', 'text', 'created_at'], got {header}. Proceeding anyway.")
            output_data.append(header)
        except StopIteration:
            print("Error: Input CSV file is empty.")
            exit()

        for i, row in enumerate(reader, start=1):
            if len(row) < 3:
                print(f"Skipping malformed row #{i}: Not enough columns. Row data: {row}")
                skipped_rows += 1
                continue

            original_created_at_str = row[2]  # e.g., "Apr 8, 10:06:20 AM EDT"

            try:
                # Parse the original date (e.g., "Apr 8, 10:06:20 AM EDT")
                month_day = original_created_at_str.split(',')[0].strip()  # "Apr 8"
                time_part = original_created_at_str.split(',')[1].strip().split(' ')[0]  # "10:06:20"
                ampm_part = original_created_at_str.split(',')[1].strip().split(' ')[1]  # "AM" or "PM"

                # Construct new date in 2024 (e.g., "Apr 8 2024")
                new_date_str = f"{month_day} 2024"  # "Apr 8 2024"
                new_time_str = f"{time_part} {ampm_part}"  # "10:06:20 AM"

                # Parse into datetime
                new_date = datetime.strptime(new_date_str, '%b %d %Y').date()  # "Apr 8 2024" → 2024-04-08
                new_time = datetime.strptime(new_time_str, '%I:%M:%S %p').time()  # "10:06:20 AM" → 10:06:20

                # Combine and format
                new_datetime = datetime.combine(new_date, new_time)
                formatted_date = new_datetime.strftime('%Y:%m:%d:%H:%M:%S')  # "2024:04:08:10:06:20"

                row[2] = formatted_date
                output_data.append(row)
                processed_rows += 1

            except Exception as e:
                print(f"Skipping row #{i} due to error: {e}. Row data: {row}")
                skipped_rows += 1

    # Find the index of the first row with date starting from 2024:09:01
    start_index = -1
    for index, row in enumerate(output_data):
        if index > 0 and len(row) > 2 and row[2].startswith('2024:09:01'):
            start_index = index
            break

    # Create a new output data list starting from the found index
    final_output_data = []
    if start_index != -1:
        final_output_data.append(output_data[0])  # Add the header
        final_output_data.extend(output_data[start_index:])
    else:
        # If 2024:09:01 is not found, keep the header and all processed rows
        final_output_data = output_data

    # Write output
    with open(output_filename, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(final_output_data)

    print("-" * 30)
    print("Processing complete.")
    print(f"Successfully processed: {processed_rows} rows.")
    print(f"Skipped:             {skipped_rows} rows.")
    if start_index != -1:
        print(f"Data before 2024-09-01 removed.")
    else:
        print(f"No data found starting from 2024-09-01. All processed data retained.")
    print(f"Output saved to:     {output_filename}")
    print("-" * 30)

except FileNotFoundError:
    print(f"Error: Input file not found at '{input_filename}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")