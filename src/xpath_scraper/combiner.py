from datetime import datetime


def parse_line(line):
    parts = line.strip().split('","')
    if len(parts) != 3:
        return None  # malformed
    tweet_id = parts[0].strip('"')
    text = parts[1]
    timestamp_str = parts[2].strip('"')
    timestamp = datetime.strptime(timestamp_str, "%Y:%m:%d:%H:%M:%S")
    return (tweet_id, text, timestamp_str, timestamp)


def read_entries(filename):
    entries = []
    seen_ids = set()
    with open(filename, 'r', encoding='utf-8') as f:
        first = False
        for line in f:
            if first:
                parsed = parse_line(line)
                if parsed and parsed[0] not in seen_ids:
                    entries.append(parsed)
                    seen_ids.add(parsed[0])
            else:
                first = True

    return entries, seen_ids


def merge_files(source_file, target_file, output_file=None):
    target_entries, seen_ids = read_entries(target_file)
    source_entries, _ = read_entries(source_file)

    # Filter out duplicates
    new_entries = [entry for entry in source_entries if entry[0] not in seen_ids]

    # Combine and sort by timestamp
    combined = target_entries + new_entries
    combined.sort(key=lambda x: x[3])  # sort by datetime

    # Format back to string lines
    formatted_lines = [f'"{e[0]}","{e[1]}","{e[2]}"\n' for e in combined]

    output_path = output_file if output_file else target_file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(formatted_lines)


merge_files("src/xpath_scraper/temp/elonmusk_reformatted.csv", "src/data/elonmusk_reformatted.csv")
