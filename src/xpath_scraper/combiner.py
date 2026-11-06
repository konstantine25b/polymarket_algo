from datetime import datetime
import hashlib
import json
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


def read_entries(filename, stats=None):
    """Parse a '"id","text","timestamp"' file. Lines that cannot be parsed are counted in stats['malformed'] (never
    silently forgotten): the caller decides whether that is acceptable (B05)."""
    entries = []
    seen_ids = set()
    header = None
    malformed = []

    logger.info(f"Reading entries from {filename}")
    if not os.path.exists(filename):
        logger.error(f"File not found: {filename}")
        if stats is not None:
            stats.update(missing=True, malformed=0, lines=0)
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
            if not line.strip():
                continue
            parsed = parse_line(line)
            if parsed is None:
                malformed.append(line_count)
                continue
            if parsed[0] not in seen_ids:
                entries.append(parsed)
                seen_ids.add(parsed[0])

    logger.info(f"Read {len(entries)} unique entries from {filename}")
    if stats is not None:
        stats.update(missing=False, malformed=len(malformed), malformed_lines=malformed[:20], lines=line_count - 1)
    return entries, seen_ids, header


def merge_files(source_file, target_file, output_file=None):
    """Merge new tweets from source into target. Returns a result dict; raises (leaving the target untouched) if the
    merge could lose or garble anything: missing/empty source, unparseable lines on either side, or any tweet ID that
    was in the target but is not in the output."""
    logger.info(f"Merging {source_file} into {target_file}")

    tstats, sstats = {}, {}
    target_entries, seen_ids, target_header = read_entries(target_file, tstats)
    source_entries, _, source_header = read_entries(source_file, sstats)

    if sstats.get("missing"):
        raise RuntimeError(f"source file not found: {source_file}")
    if not source_entries:
        raise RuntimeError(f"source file {source_file} has no parseable tweets - refusing to merge")
    if sstats["malformed"]:
        raise RuntimeError(f"{sstats['malformed']} unparseable line(s) in source {source_file} (first at {sstats['malformed_lines'][:5]})")
    if tstats["malformed"]:
        raise RuntimeError(f"{tstats['malformed']} unparseable line(s) in target {target_file} would be dropped by a rewrite "
                           f"(first at {tstats['malformed_lines'][:5]}) - fix them by hand first")

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
    # ID-level preservation (a bare row-count check cannot see symmetric drops)
    out_ids = {e[0] for e in combined}
    lost = seen_ids - out_ids
    if lost or len(combined) < len(target_entries):
        raise RuntimeError(f"merge would drop {len(lost)} existing tweet id(s); refusing to write")

    # Write to a temp file and swap it in, so an interrupted write cannot truncate the data file
    tmp_path = output_path + f".{os.getpid()}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(header)
        f.writelines(formatted_lines)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, output_path)

    sha = hashlib.sha256(open(output_path, 'rb').read()).hexdigest()
    result = {"new_rows": len(new_entries), "total_rows": len(combined), "source_rows": len(source_entries),
              "newest": combined[-1][2] if combined else None,
              "source_newest": max(e[3] for e in source_entries).strftime("%Y:%m:%d:%H:%M:%S"), "sha256": sha}
    logger.info(f"Merged data written to {output_path}")
    return result


if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    source_file = os.path.join(repo_root, "src/xpath_scraper/temp/elonmusk_reformatted.csv")
    target_file = os.path.join(repo_root, "src/data/elonmusk_reformatted.csv")
    
    logger.info(f"Starting CSV merge process")
    result = merge_files(source_file, target_file)
    logger.info(f"Found {result['new_rows']} new entries")
    print("REFRESH_RESULT " + json.dumps(result), flush=True)
    logger.info(f"CSV merge complete")
