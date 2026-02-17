import json
import csv
import argparse
import re
import os
from collections import defaultdict
from datetime import datetime

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
    json_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.startswith("matched_control_batch") and file.endswith(".json"):
                json_files.append(os.path.join(root, file))
    
    data = []
    for file in json_files:
        with open(file, 'r', encoding='utf-8') as f:
            data.extend(json.load(f))
    return data, len(json_files)

def format_to_csv(data, output_file, diagnosed_summary_file, control_threshold=None):
    total_posts = 0
    duplicate_posts = 0
    seen_post_ids = set()
    diagnosed_counts = defaultdict(int)
<<<<<<< HEAD
    unique_controls = set()
=======
    users_meeting_threshold = 0
>>>>>>> 43c36f1044aa90245b4af1539ffd0fecd7470015

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['TID', 'text']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for entry in data:
            diagnosed_user = entry['diagnosed_user']
            controls = entry['controls']
            diagnosed_counts[diagnosed_user] += len(controls)
            if control_threshold is not None and diagnosed_counts[diagnosed_user] < control_threshold:
                continue
            users_meeting_threshold += 1
            for control in controls:
                control_user = control['username']
                unique_controls.add(control_user)
                posts = control['posts']
                for post in posts:
                    tid = f"0_{post['subreddit']}_{diagnosed_user}_{control_user}_{post['id']}"
                    text = post['selftext'].strip()
                    if tid in seen_post_ids:
                        duplicate_posts += 1
                    else:
                        cleaned_text = preprocess_text(text)
                        writer.writerow({'TID': tid, 'text': cleaned_text})
                        seen_post_ids.add(tid)
                        total_posts += 1
                   

    # Write diagnosed user summary to a separate file
    with open(diagnosed_summary_file, 'w', newline='', encoding='utf-8') as summary_file:
        fieldnames = ['diagnosed_user', 'control_count']
        writer = csv.DictWriter(summary_file, fieldnames=fieldnames)

        writer.writeheader()
        for diagnosed_user, control_count in diagnosed_counts.items():
            if control_count >= control_threshold:
                writer.writerow({'diagnosed_user': diagnosed_user, 'control_count': control_count})

<<<<<<< HEAD
    # Count the number of diagnosed users with more than 9 matched controls
    diagnosed_with_more_than_9_controls = sum(1 for count in diagnosed_counts.values() if count > 9)

    return total_posts, duplicate_posts, len(diagnosed_counts), diagnosed_with_more_than_9_controls, len(unique_controls)
=======
    return total_posts, invalid_posts, duplicate_posts, len(diagnosed_counts), users_meeting_threshold
>>>>>>> 43c36f1044aa90245b4af1539ffd0fecd7470015

def main():
    parser = argparse.ArgumentParser(description='Format JSON data to CSV and perform text cleaning.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing JSON files')
<<<<<<< HEAD
=======
    parser.add_argument('output_file', type=str, help='Path to the output CSV file')
    parser.add_argument('diagnosed_summary_file', type=str, help='Path to the output CSV file for diagnosed summary')
    parser.add_argument('--control_threshold', type=int, default=9, help='Minimum number of controls required to include a diagnosed user')
>>>>>>> 43c36f1044aa90245b4af1539ffd0fecd7470015

    args = parser.parse_args()
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = os.path.join(args.input_folder, f"{today}-output.csv")
    diagnosed_summary_file = os.path.join(args.input_folder, f"{today}-summary.csv")
    log_file = os.path.join(args.input_folder, f"{today}-log.txt")

    data, file_count = load_json_files_from_folder(args.input_folder)
<<<<<<< HEAD
    total_posts,  duplicate_posts, unique_diagnosed_count, diagnosed_with_more_than_9_controls, unique_controls_count = format_to_csv(data, output_file, diagnosed_summary_file)

    with open(log_file, 'w', encoding='utf-8') as log:
        log.write(f"------------summary-----------\n")
        log.write(f"Number of files read: {file_count}\n")
        log.write(f"Total number of posts processed: {total_posts}\n")
        log.write(f"Number of duplicate posts ignored: {duplicate_posts}\n")
        log.write(f"Number of unique diagnosed users: {unique_diagnosed_count}\n")
        log.write(f"Number of diagnosed users with more than 9 matched controls: {diagnosed_with_more_than_9_controls}\n")
        log.write(f"Total number of unique controls found: {unique_controls_count}\n")
=======
    total_posts, invalid_posts, duplicate_posts, unique_diagnosed_count, users_meeting_threshold = format_to_csv(data, args.output_file, args.diagnosed_summary_file, args.control_threshold)

    print(f"------------summary-----------")
    print(f"Number of files read: {file_count}")
    print(f"Total number of posts processed: {total_posts}")
    print(f"Number of invalid posts ignored: {invalid_posts}")
    print(f"Number of duplicate posts ignored: {duplicate_posts}")
    print(f"Number of unique diagnosed users: {unique_diagnosed_count}")
    print(f"Number of diagnosed users meeting the control threshold: {users_meeting_threshold}")
>>>>>>> 43c36f1044aa90245b4af1539ffd0fecd7470015

if __name__ == '__main__':
    main()
