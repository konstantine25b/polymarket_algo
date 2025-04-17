import csv
import os
from datetime import datetime
import pytz
import re

# --- Configuration ---
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)  # Go up one level from src/formating to src

input_filename = os.path.join(src_dir, 'data', 'elonmusk.csv')
output_filename = os.path.join(src_dir, 'data', 'elonmusk_reformatted.csv')
error_log_filename = os.path.join(src_dir, 'data', 'elonmusk_parsing_errors.log')

print("Starting script...")
print(f"Input file: {input_filename}")
print(f"Output file: {output_filename}")
print(f"Error log: {error_log_filename}")

output_data = []
processed_rows = 0
skipped_rows = 0
error_rows = []
current_year = 2024
max_month_seen = 0

# Function to determine if we should update the year
def determine_year(date_str):
    # Extract month from the date string
    global current_year, max_month_seen
    
    # Parse the date string to get the month
    pattern = r'([A-Za-z]{3})\s+\d{1,2}'
    match = re.search(pattern, date_str)
    
    if not match:
        return current_year  # Default to current year if pattern doesn't match
    
    month_str = match.group(1)
    month_num = datetime.strptime(month_str, '%b').month
    
    # Update max month seen
    max_month_seen = max(max_month_seen, month_num)
    
    # Check if we need to update the year
    if month_num == 1 and max_month_seen == 12:
        # We've seen December and now we're seeing January, so it's a new year
        current_year = 2025
    
    return current_year

# Function to clean tweet text to make it pandas-compatible
def clean_tweet_text(text):
    if not text:
        return ""
    # Replace all newlines with a space
    cleaned = text.replace('\n', ' ').replace('\r', ' ')
    # Replace double quotes with single quotes to avoid CSV issues
    cleaned = cleaned.replace('"', "'")
    return cleaned

try:
    # Read the original file line by line to ensure correct parsing
    input_data = []
    
    # First, manually parse the CSV file to ensure proper handling of multiline tweets
    with open(input_filename, 'r', newline='', encoding='utf-8') as infile:
        # Get header first
        header = next(csv.reader(infile))
        input_data.append(header)
        output_data.append(header.copy())
        
        # Now read file as a single string to manually parse
        infile.seek(0)  # Go back to start of file
        content = infile.read()
        
        # Skip the header line
        content = content[content.find('\n')+1:]
        
        # Regular expression to match CSV pattern with proper handling of quoted fields
        # This regex: 
        # 1. Matches the ID (digits)
        # 2. Followed by comma
        # 3. Followed by quoted text field that can contain escaped quotes
        # 4. Followed by comma
        # 5. Followed by a quoted date field
        csv_pattern = r'(\d+),(".*?(?<!\\)"),(.*?)(?=\n\d+,|$)'
        
        matches = re.finditer(csv_pattern, content, re.DOTALL)
        for match in matches:
            tweet_id = match.group(1)
            
            # Parse tweet text: remove surrounding quotes and unescape internal quotes
            tweet_text = match.group(2)
            if tweet_text.startswith('"') and tweet_text.endswith('"'):
                tweet_text = tweet_text[1:-1]  # Remove surrounding quotes
            tweet_text = tweet_text.replace('\\"', '"')  # Unescape internal quotes
            tweet_text = clean_tweet_text(tweet_text)
            
            # Get date string
            date_str = match.group(3).strip()
            if date_str.startswith('"') and date_str.endswith('"'):
                date_str = date_str[1:-1]  # Remove surrounding quotes
            
            # Add to input data
            input_data.append([tweet_id, tweet_text, date_str])

    print(f"Read {len(input_data)-1} rows from input file.")
    
    # Process all rows while guaranteeing no data loss
    for i, row in enumerate(input_data[1:], start=1):  # Skip header
        if len(row) < 3:
            print(f"Row {i} has incomplete data (less than 3 columns). Keeping original data.")
            output_data.append(row.copy())  # Make a copy to be safe
            skipped_rows += 1
            continue

        tweet_id = row[0] if len(row) > 0 else "unknown"
        tweet_text = row[1] if len(row) > 1 else ""
        original_created_at_str = row[2] if len(row) > 2 else ""  # e.g., "Apr 8, 10:06:20 AM EDT"

        try:
            # Determine the year based on the month pattern
            year = determine_year(original_created_at_str)
            
            # Parse the date components
            parts = original_created_at_str.split(', ')
            if len(parts) < 2:
                # Handle alternative format without comma
                parts = original_created_at_str.split(' ', 1)
                if len(parts) < 2:
                    raise ValueError(f"Cannot parse date format: {original_created_at_str}")
            
            date_part = parts[0]  # e.g., "Apr 8"
            time_part = parts[1] if len(parts) > 1 else ""  # e.g., "10:06:20 AM EDT"
            
            # Extract month and day
            date_match = re.search(r'([A-Za-z]{3})\s+(\d{1,2})', date_part)
            if not date_match:
                raise ValueError(f"Cannot extract month and day from: {date_part}")
            
            month = date_match.group(1)  # e.g., "Apr"
            day = date_match.group(2)    # e.g., "8"
            
            # Format as YYYY:MM:DD:HH:MM:SS
            # First, convert month name to number
            month_num = datetime.strptime(month, '%b').month
            
            # Extract time components: HH:MM:SS
            time_match = re.search(r'(\d{1,2}):(\d{2}):(\d{2})\s+(AM|PM)', time_part)
            if not time_match:
                raise ValueError(f"Cannot extract time from: {time_part}")
            
            hour = int(time_match.group(1))
            minute = time_match.group(2)
            second = time_match.group(3)
            am_pm = time_match.group(4)
            
            # Convert 12-hour format to 24-hour format
            if am_pm.upper() == 'PM' and hour < 12:
                hour += 12
            elif am_pm.upper() == 'AM' and hour == 12:
                hour = 0
            
            # Create the formatted date string
            formatted_date = f"{year}:{month_num:02d}:{int(day):02d}:{hour:02d}:{minute}:{second}"
            
            # Make a new row with the formatted date
            new_row = [tweet_id, tweet_text, formatted_date]
            output_data.append(new_row)
            processed_rows += 1
            
            if i % 1000 == 0:
                print(f"Processed {i} rows so far...")
                
        except Exception as e:
            error_msg = f"Row {i}, ID {tweet_id}: Error parsing '{original_created_at_str}' - {e}"
            error_rows.append(error_msg)
            print(f"Warning: {error_msg}")
            # Keep the original row to avoid data loss
            clean_row = [tweet_id, tweet_text, original_created_at_str]
            output_data.append(clean_row)
            skipped_rows += 1

    # Check for missing IDs from the original data
    input_ids = set(row[0] for row in input_data[1:] if len(row) > 0)
    output_ids = set(row[0] for row in output_data[1:] if len(row) > 0)
    
    missing_ids = input_ids - output_ids
    if missing_ids:
        print(f"WARNING: Found {len(missing_ids)} missing IDs in output. Adding them back.")
        for row in input_data[1:]:
            if len(row) > 0 and row[0] in missing_ids:
                if len(row) >= 3:
                    # Create a clean version of the row
                    clean_row = [row[0], row[1], row[2]]
                    output_data.append(clean_row)
                    print(f"Re-added missing ID: {row[0]}")
                else:
                    # Handle incomplete rows
                    while len(row) < 3:
                        row.append("")
                    clean_row = [row[0], row[1], row[2]]
                    output_data.append(clean_row)
                    print(f"Re-added missing ID with incomplete data: {row[0]}")

    # Double-check specific tweet ID that was mentioned
    target_id = "1911319452089536904"
    target_found = False
    for row in output_data:
        if len(row) > 0 and row[0] == target_id:
            target_found = True
            print(f"Specific tweet check - Found ID {target_id} with date: {row[2] if len(row) > 2 else 'MISSING'}")
            break
            
    if not target_found:
        print(f"WARNING: Could not find tweet ID {target_id} in output data!")

    # Write output file with proper CSV handling
    with open(output_filename, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)  # Quote all fields
        writer.writerows(output_data)
    
    print(f"All data written to output file: {output_filename}")
    
    # Write error log if there are errors
    if error_rows:
        with open(error_log_filename, 'w', encoding='utf-8') as errfile:
            errfile.write("TWEET PARSING ERROR LOG\n")
            errfile.write("======================\n\n")
            errfile.write(f"Total errors: {len(error_rows)}\n\n")
            for err in error_rows:
                errfile.write(f"{err}\n")

    # Verify final output
    input_count = len(input_data) - 1  # Subtract header
    output_count = len(output_data) - 1  # Subtract header
    
    print("-" * 30)
    print("Processing complete.")
    print(f"Input rows:              {input_count}")
    print(f"Output rows:             {output_count}")
    print(f"Successfully processed:  {processed_rows} rows")
    print(f"Skipped/preserved:       {skipped_rows} rows")
    
    if input_count != output_count:
        print(f"WARNING: Input and output row counts differ by {abs(input_count - output_count)} rows!")
    else:
        print("SUCCESS: All data preserved. Input and output row counts match.")
    
    if skipped_rows > 0 or error_rows:
        print(f"Error details written to: {error_log_filename}")
    print(f"Output saved to:         {output_filename}")
    print(f"Note: Dates have been reformatted to YYYY:MM:DD:HH:MM:SS format")
    print("-" * 30)

except FileNotFoundError:
    print(f"Error: Input file not found at '{input_filename}'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    import traceback
    traceback.print_exc()
    if error_rows:
        print(f"Writing error log to {error_log_filename}")
        with open(error_log_filename, 'w', encoding='utf-8') as errfile:
            errfile.write("TWEET PARSING ERROR LOG\n")
            errfile.write("======================\n\n")
            errfile.write(f"Global error: {e}\n\n")
            for err in error_rows:
                errfile.write(f"{err}\n")