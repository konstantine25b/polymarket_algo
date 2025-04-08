import csv
import os
from datetime import datetime, timedelta

# --- Configuration ---

# Determine the absolute path of the script and the project's src directory
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir) # Go up one level from src/formating to src

# Define input and output file paths relative to the src directory
input_filename = os.path.join(src_dir, 'data', 'elonmusk.csv')
# Output file will be saved in the same data directory with a new name
output_filename = os.path.join(src_dir, 'data', 'elonmusk_reformatted.csv')

# Define the starting date for the sequence
start_date = datetime(2024, 9, 1) # Year 2024, Month 9 (September), Day 1

# --- Processing Logic ---

current_date = start_date
output_data = []
processed_rows = 0
skipped_rows = 0

print(f"Starting script...")
print(f"Input file: {input_filename}")
print(f"Output file: {output_filename}")
print(f"Starting sequence date: {start_date.strftime('%Y-%m-%d')}")

try:
    with open(input_filename, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        try:
            header = next(reader) # Read the header
            if header != ['id', 'text', 'created_at']:
                print(f"Warning: CSV header mismatch. Expected ['id', 'text', 'created_at'], got {header}. Proceeding anyway.")
            output_data.append(header) # Add header to output
        except StopIteration:
            print("Error: Input CSV file is empty.")
            exit() # Exit if the file is empty

        for i, row in enumerate(reader, start=1):
            if len(row) < 3: # Check if row has at least 3 columns
                print(f"Skipping malformed row #{i}: Not enough columns. Row data: {row}")
                skipped_rows += 1
                continue

            original_created_at_str = row[2] # Get the original date string

            try:
                # --- Extract the TIME part from the original string ---
                # Example: "Apr 18, 6:41:57 PM EDT"
                # We need to extract "6:41:57 PM"
                # Split by comma, take the second part, strip whitespace
                time_section = original_created_at_str.split(',')[1].strip()
                # Split the time section by space, take the first two parts ("H:M:S", "AM/PM")
                time_str_parts = time_section.split()[:2]
                time_str = " ".join(time_str_parts) # e.g., "6:41:57 PM"

                # Parse the extracted time string to get a time object
                original_time_obj = datetime.strptime(time_str, '%I:%M:%S %p').time()

                # --- Combine the sequential DATE with the extracted TIME ---
                new_dt = datetime.combine(current_date.date(), original_time_obj)

                # --- Format the new datetime object as YYYY:MM:DD:HH:MM:SS ---
                formatted_date = new_dt.strftime('%Y:%m:%d:%H:%M:%S') # Using : as requested

                # --- Update the row with the new formatted date ---
                row[2] = formatted_date
                output_data.append(row)

                # --- Increment the date for the *next* row ---
                current_date += timedelta(days=1)
                processed_rows += 1

            except (ValueError, IndexError, AttributeError) as e:
                print(f"Skipping row #{i} due to error processing 'created_at': '{original_created_at_str}'. Error: {e}. Row data: {row}")
                skipped_rows += 1
            except Exception as e: # Catch any other unexpected errors
                 print(f"Skipping row #{i} due to unexpected error: {e}. Row data: {row}")
                 skipped_rows += 1


    # --- Writing the modified data to the new CSV file ---
    print(f"\nWriting output to {output_filename}...")
    with open(output_filename, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(output_data)

    print("-" * 30)
    print("Processing complete.")
    print(f"Successfully processed: {processed_rows} rows.")
    print(f"Skipped:             {skipped_rows} rows.")
    print(f"Output saved to:     {output_filename}")
    print("-" * 30)


except FileNotFoundError:
    print(f"Error: Input file not found at '{input_filename}'. Please ensure the file exists and the path is correct.")
except Exception as e:
    print(f"An unexpected error occurred during file reading or writing: {e}")