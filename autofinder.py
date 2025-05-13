def load_tweet_ids(filename):
    ids = set()
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',', 2)
            if len(parts) >= 1:
                tweet_id = parts[0].strip('"')
                ids.add(tweet_id)
    return ids

def load_tweet_map(filename):
    tweet_map = {}
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',', 2)
            if len(parts) == 3:
                tweet_id = parts[0].strip('"')
                tweet_map[tweet_id] = line.strip()
    return tweet_map

def find_missing(file1, file2):
    ids1 = load_tweet_ids(file1)
    ids2 = load_tweet_ids(file2)

    only_in_file1 = ids1 - ids2
    only_in_file2 = ids2 - ids1

    tweets1 = load_tweet_map(file1)
    tweets2 = load_tweet_map(file2)

    print(f"Entries in {file1} but not in {file2}: {len(only_in_file1)}")
    for tweet_id in only_in_file1:
        print(tweets1[tweet_id])

    print(f"\nEntries in {file2} but not in {file1}: {len(only_in_file2)}")
    for tweet_id in only_in_file2:
        print(tweets2[tweet_id])

# Replace these with your actual filenames
find_missing("src/data/website_elonmusk_reformatted.csv", "src/data/elonmusk_reformatted.csv")
