# CSV Comparison Tool

A simple utility to compare two CSV files and identify differences between them. This tool is particularly useful for comparing different versions of the same dataset to find missing or added records.

## Features

- Compare any two CSV files to find missing or additional rows
- Compare by ID (first column) instead of entire row content
- Filter comparison by date range
- Generate a report of differences
- Log up to 50 differences to console
- Auto-save comparison results to a dedicated folder
- Count total mismatches between files
- Works with the ElonMusk tweet datasets in `src/data`

## Installation

No installation required. Just make sure you have Python 3.x installed.

## Usage

Run the comparison tool directly with Python:

```bash
# Basic usage
python3 src/debug/csv_data/compare_csv.py <file1> "<file2>"

# With additional options
python3 src/debug/csv_data/compare_csv.py <file1> <file2> [OPTIONS]
```

### Arguments

- `file1`: Path to the first CSV file
- `file2`: Path to the second CSV file
- `--date-col`: Index of the date column (0-based, default is 2)
- `--start-date`: Optional start date for filtering (format: YYYY-MM-DD)
- `--end-date`: Optional end date for filtering (format: YYYY-MM-DD)
- `--output`: Optional path to save the differences to a CSV file
- `--compare-by-id`: Compare rows by ID (first column) instead of the entire row content
- `--log-diff`: Log up to 50 different rows to console for quick review
- `--auto-save`: Automatically save comparison results to the `src/debug/csv_data/comparisons` folder

## Examples

### Compare two ElonMusk dataset files

I use this::::::
```bash
python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv src/data/elonmusk_reformatted(26).csv --compare-by-id --log-diff --auto-save 
```
```bash
python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv src/data/elonmusk_reformatted2.csv
```

### Compare files by ID column

```bash
python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv src/data/elonmusk_reformatted2.csv --compare-by-id
```

### Compare files with date filtering

```bash
python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv src/data/elonmusk_reformatted2.csv --start-date 2023-01-01 --end-date 2023-12-31
```

### Save differences to a file

```bash
python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv src/data/elonmusk_reformatted2.csv --output differences.csv
```

### Auto-save differences to the comparisons folder

```bash
python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv src/data/elonmusk_reformatted2.csv --auto-save
```

### See sample of differences in the console

```bash
python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv src/data/elonmusk_reformatted2.csv --log-diff
```

### Combine multiple options

```bash
python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv src/data/elonmusk_reformatted2.csv --compare-by-id --log-diff --auto-save
```

### IMPORTANT: Handling filenames with special characters

When a filename contains special characters like parentheses `()`, you MUST use double quotes around the entire filename:

```bash
# CORRECT: Using double quotes
python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv "src/data/elonmusk_reformatted(26).csv"
```

Without quotes, the command will fail with an error like:

```
zsh: no matches found: src/data/elonmusk_reformatted(26).csv
```

This is because parentheses are special characters in the shell that are used for command grouping.

## Workaround for filenames with special characters

If you don't want to use quotes, you can temporarily rename the files to remove special characters. Here's how to compare files with special characters:

1. Use quotes around filenames with parentheses (recommended)

   ```bash
   python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv "src/data/elonmusk_reformatted(26).csv"
   ```

2. Or escape each special character with a backslash
   ```bash
   python3 src/debug/csv_data/compare_csv.py src/data/elonmusk_reformatted.csv src/data/elonmusk_reformatted\(26\).csv
   ```

Either approach will work in all shells.

## Notes

- The date filtering assumes the date column follows the format `YYYY:MM:DD:HH:MM:SS` as seen in the ElonMusk datasets
- For date filtering, the command line takes dates in the format `YYYY-MM-DD` for simplicity
- The tool will automatically skip rows with invalid date formats when filtering
- When using `--compare-by-id`, the tool compares only the first column (ID) of each row, which is useful when you're only concerned with missing or additional records regardless of their content
- The `--log-diff` option shows up to 50 different rows from each file in the console output
- The `--auto-save` option creates a file in the `src/debug/csv_data/comparisons` folder with a timestamp in the filename
- You can combine `--auto-save` with `--output` to save to both locations

## Available Sample Data

The following files in `src/data` can be used for comparison (remember to use quotes for files with special characters):

- `elonmusk_reformatted.csv`
- `elonmusk_reformatted2.csv`
- `elonmusk_reformatted3.csv`
- `elonmusk_reformatted (10).csv` (use quotes for files with spaces or parentheses)
- `elonmusk_reformatted (12).csv` (use quotes for files with spaces or parentheses)
- `elonmusk_reformatted (14).csv` (use quotes for files with spaces or parentheses)
- `elonmusk_reformatted (18).csv` (use quotes for files with spaces or parentheses)
- `elonmusk_reformatted (19).csv` (use quotes for files with spaces or parentheses)
- `elonmusk_reformatted(24).csv` (use quotes for files with parentheses)
- `elonmusk_reformatted(26).csv` (use quotes for files with parentheses)
