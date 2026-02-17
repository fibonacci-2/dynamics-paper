import json
import csv
import argparse
import re
import os

def preprocess_text(text):
    # Lowercasing Text
    text = text.lower()
    
    # Removing Hyperlinks
    text = re.sub(r'https?://\S+', '', text)
    
    # Removing HTML Tags
    text = re.sub(r'<.*?>', '', text)
    
    # Removing User Mentions
    text = re.sub(r'@\w+', '', text)
    
    # Removing HTML Entities
    text = re.sub(r'&\w+;', ' ', text)
    
    # Processing Hashtags
    text = re.sub(r'#(\w+)', r'\1', text)
    
    # Preserving Certain Characters and Whitespace
    text = re.sub(r'[^a-zA-Z0-9\s\.\'\!\?\,\;\-]', ' ', text)
    
    # Normalizing Spaces and Punctuation
    text = re.sub(r'(?<=[.,!?])(?=[^\s])', r' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(\.|\!|\?|\,|\;)\1+', r'\1', text)  # Deduplicate sentence-ending symbols
    text = re.sub(r'\.{3,}', '.', text)  # Replace consecutive ellipsis with a single full stop
    text = text.strip()
    text = re.sub(r'(?<=\w)([.,;])(?=\S)', r'\1 ', text)
    
    # Ensure post ends with a full stop if it doesn't end with a sentence-ending symbol
    if not re.search(r'[.!?]$', text):
        text += '.'
    
    return text

def load_json_files_from_folder(folder_path):
    json_files = [f for f in os.listdir(folder_path) if f.startswith("matched_control_batch") and f.endswith(".json")]
    data = []
    for file in json_files:
        with open(os.path.join(folder_path, file), 'r', encoding='utf-8') as f:
            data.extend(json.load(f))
    return data, len(json_files)

def format_to_csv(data, output_file):
    total_posts = 0
    invalid_posts = 0
    duplicate_posts = 0
    seen_post_ids = set()

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['TID', 'text']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for entry in data:
            diagnosed_user = entry['diagnosed_user']
            controls = entry['controls']
            for control in controls:
                control_user = control['username']
                posts = control['posts']
                for post in posts:
                    tid = f"0_{post['subreddit']}_{diagnosed_user}_{control_user}_{post['id']}"
                    text = post['selftext']
                    if text.strip():
                        if tid in seen_post_ids:
                            duplicate_posts += 1
                        else:
                            cleaned_text = preprocess_text(text)
                            writer.writerow({'TID': tid, 'text': cleaned_text})
                            seen_post_ids.add(tid)
                            total_posts += 1
                    else:
                        invalid_posts += 1
    return total_posts, invalid_posts, duplicate_posts

def main():
    parser = argparse.ArgumentParser(description='Format JSON data to CSV and perform text cleaning.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing JSON files')
    parser.add_argument('output_file', type=str, help='Path to the output CSV file')

    args = parser.parse_args()

    data, file_count = load_json_files_from_folder(args.input_folder)
    total_posts, invalid_posts, duplicate_posts = format_to_csv(data, args.output_file)

    print(f"------------summary-----------")
    print(f"Number of files read: {file_count}")
    print(f"Total number of posts processed: {total_posts}")
    print(f"Number of invalid posts ignored: {invalid_posts}")
    print(f"Number of duplicate posts ignored: {duplicate_posts}")

if __name__ == '__main__':
    main()
