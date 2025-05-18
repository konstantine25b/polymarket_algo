from datetime import datetime
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TweetCSVCombiner')

def parse_line(line):
    parts = line.strip().split('","')
    if len(parts) != 3:
        return None  # malformed
    tweet_id = parts[0].strip('"')
    text = parts[1]
    timestamp_str = parts[2].strip('"')
    try:
        timestamp = datetime.strptime(timestamp_str, "%Y:%m:%d:%H:%M:%S")
        return (tweet_id, text, timestamp_str, timestamp)
    except ValueError:
        # This could be the header or malformed date
        logger.warning(f"Could not parse timestamp from line: {line[:50]}...")
        return None


def read_entries(filename):
    entries = []
    seen_ids = set()
    header = None
    
    logger.info(f"Reading entries from {filename}")
    if not os.path.exists(filename):
        logger.error(f"File not found: {filename}")
        return entries, seen_ids, header
        
    with open(filename, 'r', encoding='utf-8') as f:
        line_count = 0
        for line in f:
            line_count += 1
            if line_count == 1:
                # Save header
                header = line
                logger.info(f"Header found: {header.strip()}")
                continue
                
            parsed = parse_line(line)
            if parsed and parsed[0] not in seen_ids:
                entries.append(parsed)
                seen_ids.add(parsed[0])

    logger.info(f"Read {len(entries)} unique entries from {filename}")
    return entries, seen_ids, header


def merge_files(source_file, target_file, output_file=None):
    logger.info(f"Merging {source_file} into {target_file}")
    
    target_entries, seen_ids, target_header = read_entries(target_file)
    source_entries, _, source_header = read_entries(source_file)
    
    # Use header from target file, or source if target doesn't have one
    header = target_header or source_header or '"id","text","timestamp"\n'

    # Filter out duplicates
    new_entries = [entry for entry in source_entries if entry[0] not in seen_ids]
    logger.info(f"Found {len(new_entries)} new entries to add")

    # Combine and sort by timestamp
    combined = target_entries + new_entries
    combined.sort(key=lambda x: x[3])  # sort by datetime
    logger.info(f"Combined data contains {len(combined)} entries")

    # Format back to string lines
    formatted_lines = [f'"{e[0]}","{e[1]}","{e[2]}"\n' for e in combined]

    output_path = output_file if output_file else target_file
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header first
        f.write(header)
        # Then write data
        f.writelines(formatted_lines)
    
    logger.info(f"Merged data written to {output_path}")


if __name__ == "__main__":
    source_file = "src/xpath_scraper/temp/elonmusk_reformatted.csv"
    target_file = "src/data/elonmusk_reformatted.csv"
    
    logger.info(f"Starting CSV merge process")
    merge_files(source_file, target_file)
    logger.info(f"CSV merge complete")
