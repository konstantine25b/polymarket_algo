#!/usr/bin/env python3

import argparse
import csv
import os
import sys
import logging
import glob
from datetime import datetime
from pathlib import Path


def setup_logging(log_level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def parse_date(date_str):
    """Parse a date string in the format YYYY-MM-DD"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD")


def resolve_path(file_path):
    """
    Resolve file path that might contain special characters or wildcards
    by finding the actual file that matches the pattern.
    """
    # If the file exists directly, return it
    if os.path.isfile(file_path):
        return file_path
    
    # Try to find files matching a pattern
    matches = glob.glob(file_path)
    if matches and os.path.isfile(matches[0]):
        return matches[0]
    
    # Try with glob escaping for characters like parentheses
    base_dir = os.path.dirname(file_path) or '.'
    file_name = os.path.basename(file_path)
    
    if '(' in file_name or ')' in file_name:
        # List all files in the directory
        all_files = os.listdir(base_dir)
        # Find the file that matches the name
        for f in all_files:
            if f == file_name:
                return os.path.join(base_dir, f)
    
    # Return original path if we couldn't resolve it
    return file_path


def read_csv(file_path):
    """Read a CSV file and return a set of its records and list of all rows"""
    records = set()
    all_rows = []
    id_to_row = {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        
        for row in reader:
            if not row:  # Skip empty rows
                continue
            
            # Store as tuple so it's hashable
            row_tuple = tuple(row)
            records.add(row_tuple)
            all_rows.append(row_tuple)
            
            # Map row ID to the row if the row has an ID column
            if len(row) > 0:
                id_to_row[row[0]] = row_tuple
            
    return records, all_rows, header, id_to_row


def filter_by_date(rows, date_column_index, start_date=None, end_date=None):
    """Filter rows by date range if dates are provided"""
    if start_date is None and end_date is None:
        return rows
    
    filtered_rows = []
    
    for row in rows:
        if len(row) <= date_column_index:
            continue
            
        try:
            # Assuming date format from the sample: YYYY:MM:DD:HH:MM:SS
            date_str = row[date_column_index].split(':')
            if len(date_str) >= 3:
                row_date = datetime(int(date_str[0]), int(date_str[1]), int(date_str[2]))
                
                if (start_date is None or row_date >= start_date) and \
                   (end_date is None or row_date <= end_date):
                    filtered_rows.append(row)
        except (ValueError, IndexError):
            # Skip rows with invalid date format
            continue
            
    return filtered_rows


def compare_csv_files(file1, file2, date_col=2, start_date=None, end_date=None, output=None, 
                       compare_by_id=False, log_diff=False, auto_output_dir=None):
    """
    Compare two CSV files and identify rows that exist in one file but not in the other.
    Optionally filter by date range.
    
    Args:
        file1: Path to the first CSV file
        file2: Path to the second CSV file
        date_col: Index of the date column (0-based)
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        output: Optional output file path
        compare_by_id: Compare rows by their ID instead of the entire row
        log_diff: Log up to 50 differences to console
        auto_output_dir: Directory to save output file if no specific output path is provided
    
    Returns:
        A tuple containing:
        - Number of rows unique to file 1
        - Number of rows unique to file 2
        - Total rows in file 1
        - Total rows in file 2
    """
    logger = setup_logging()
    
    # Read CSV files
    records1, all_rows1, header1, id_to_row1 = read_csv(file1)
    records2, all_rows2, header2, id_to_row2 = read_csv(file2)
    
    # Filter by date if specified
    if start_date or end_date:
        filtered_rows1 = filter_by_date(all_rows1, date_col, start_date, end_date)
        filtered_rows2 = filter_by_date(all_rows2, date_col, start_date, end_date)
        
        # Convert to sets for comparison
        records1 = set(filtered_rows1)
        records2 = set(filtered_rows2)
        
        # Rebuild ID mappings if comparing by ID
        if compare_by_id:
            id_to_row1 = {row[0]: row for row in filtered_rows1 if len(row) > 0}
            id_to_row2 = {row[0]: row for row in filtered_rows2 if len(row) > 0}
    
    # Find differences
    if compare_by_id:
        # Compare by IDs
        ids1 = set(id_to_row1.keys())
        ids2 = set(id_to_row2.keys())
        
        ids_in_file1_not_in_file2 = ids1 - ids2
        ids_in_file2_not_in_file1 = ids2 - ids1
        
        in_file1_not_in_file2 = {id_to_row1[id_] for id_ in ids_in_file1_not_in_file2}
        in_file2_not_in_file1 = {id_to_row2[id_] for id_ in ids_in_file2_not_in_file1}
    else:
        # Compare entire rows
        in_file1_not_in_file2 = records1 - records2
        in_file2_not_in_file1 = records2 - records1
    
    # Log differences if requested
    if log_diff:
        logger.info("Sample of rows in file 1 not in file 2 (max 50):")
        for i, row in enumerate(sorted(in_file1_not_in_file2)[:50]):
            logger.info(f"{i+1}. {row}")
            
        logger.info("\nSample of rows in file 2 not in file 1 (max 50):")
        for i, row in enumerate(sorted(in_file2_not_in_file1)[:50]):
            logger.info(f"{i+1}. {row}")
    
    # Generate output filename in the comparisons directory if not specified
    if output is None and auto_output_dir:
        os.makedirs(auto_output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        file1_name = os.path.basename(file1).replace('.csv', '')
        file2_name = os.path.basename(file2).replace('.csv', '')
        output = os.path.join(auto_output_dir, f"diff_{file1_name}_vs_{file2_name}_{timestamp}.csv")
        logger.info(f"Auto-generating output filename: {output}")
    
    # Write output if specified
    if output:
        output_dir = os.path.dirname(output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        with open(output, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            if header1:
                writer.writerow(header1)
            
            # Write rows unique to file 1
            writer.writerow(["Rows in file 1 not in file 2:"])
            for row in in_file1_not_in_file2:
                writer.writerow(row)
            
            # Add a separator
            writer.writerow([])
            writer.writerow(["Rows in file 2 not in file 1:"])
            
            # Write rows unique to file 2
            for row in in_file2_not_in_file1:
                writer.writerow(row)
    
    return len(in_file1_not_in_file2), len(in_file2_not_in_file1), len(records1), len(records2)


def main():
    parser = argparse.ArgumentParser(description='Compare two CSV files and find missing rows')
    parser.add_argument('file1', help='Path to the first CSV file')
    parser.add_argument('file2', help='Path to the second CSV file')
    parser.add_argument('--date-col', type=int, default=2, 
                        help='Index of the date column (0-based, default: 2)')
    parser.add_argument('--start-date', help='Start date for filtering (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for filtering (YYYY-MM-DD)')
    parser.add_argument('--output', help='Path to save the output CSV file with missing rows')
    parser.add_argument('--compare-by-id', action='store_true', 
                        help='Compare rows by ID (first column) instead of the entire row')
    parser.add_argument('--log-diff', action='store_true',
                        help='Log up to 50 different rows to console')
    parser.add_argument('--auto-save', action='store_true',
                        help='Automatically save comparison results to the comparisons folder')
    
    args = parser.parse_args()
    
    # Resolve file paths that might contain special characters
    file1_path = resolve_path(args.file1)
    file2_path = resolve_path(args.file2)
    
    # Validate input files
    for file_path, arg_path in [(file1_path, args.file1), (file2_path, args.file2)]:
        if not os.path.isfile(file_path):
            print(f"Error: File not found: {arg_path}")
            sys.exit(1)
    
    # Parse dates if provided
    start_date = parse_date(args.start_date) if args.start_date else None
    end_date = parse_date(args.end_date) if args.end_date else None
    
    # Set auto output directory
    auto_output_dir = 'src/debug/csv_data/comparisons' if args.auto_save else None
    
    # Compare files
    unique_to_file1, unique_to_file2, total_file1, total_file2 = compare_csv_files(
        file1_path, file2_path, args.date_col, start_date, end_date, args.output,
        args.compare_by_id, args.log_diff, auto_output_dir
    )
    
    # Print results
    compare_method = "ID" if args.compare_by_id else "entire row content"
    print(f"\nCSV Comparison Results (comparing by {compare_method}):")
    print(f"Total rows in file 1 (after filtering): {total_file1}")
    print(f"Total rows in file 2 (after filtering): {total_file2}")
    print(f"Rows unique to file 1: {unique_to_file1}")
    print(f"Rows unique to file 2: {unique_to_file2}")
    
    if args.output:
        print(f"\nDetailed results saved to: {args.output}")
    elif auto_output_dir:
        print(f"\nDetailed results saved to the comparisons folder")


if __name__ == "__main__":
    main() 